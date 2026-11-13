import streamlit as st
import json
import math
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import requests
from pathlib import Path
from pyproj import Transformer
import pandas as pd
import numpy as np
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import zipfile

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Visor GEODE Auto", layout="wide")

# --- CONSTANTES ---
IGME_URL = "https://mapas.igme.es/gis/rest/services/Cartografia_Geologica/IGME_Geode_50/MapServer"
PNOA_WMS_URL = "https://www.ign.es/wms-inspire/pnoa-ma"
IGN_RASTER_URL = "https://www.ign.es/wms-inspire/mapa-raster"
WMS_GEODE_URL = "https://mapas.igme.es/gis/services/Cartografia_Geologica/IGME_Geode_50/MapServer/WMSServer"
CAPA_RECINTOS = 8              # id de "Recintos geología" en REST (leyenda)
WMS_CAPA_RECINTOS = "1"        # la misma capa en el WMS (numeración invertida)
# GetFeatureInfo devuelve todo lo que cae en un cuadrado de ~9 px alrededor del
# punto (medido contra el servidor: entre 8 y 10 px). Se usa 8 para garantizar
# que las teselas se solapan y no queda hueco sin consultar.
GFI_HUELLA_PX = 8
GFI_TESELAS_LADO_MAYOR = 5
GFI_MAX = 500
UMBRAL_ALFA = 32               # alfa mínimo para considerar "pintado" un píxel
MIN_PX_VISIBLE = 4             # una unidad con menos píxeles no se ve en la imagen
ESCALA_MAX_RECINTOS = 300000   # minScale de la capa 8: por encima no se dibuja
ESCALA_MAX_ROTULOS = 50000     # minScale de la capa 0 (rótulos de unidades)
DPI = 96

# ----------------------------------------------------------------------
# 1. FUNCIONES DE CACHÉ (VELOCIDAD)
#    Norma: las funciones cacheadas LANZAN excepción si falla la red.
#    Así st.cache_data no memoriza un fallo puntual (antes un timeout
#    dejaba el mapa/leyenda en blanco hasta reiniciar la app).
# ----------------------------------------------------------------------

def deducir_epsg_desde_zona(zona_utm):
    return {28: 4083, 29: 25829, 30: 25830, 31: 25831}.get(int(zona_utm or 30), 25830)


@st.cache_data(show_spinner=False)
def descargar_fondo_base(bbox, width, height, tipo="PNOA"):
    url, layers = PNOA_WMS_URL, "OI.OrthoimageCoverage"
    if tipo == "TOPO":
        url, layers = IGN_RASTER_URL, "mtn_rasterizado"

    params = {
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
        "LAYERS": layers, "STYLES": "", "SRS": "EPSG:4326",
        "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "WIDTH": int(width), "HEIGHT": int(height), "FORMAT": "image/png",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    # Un WMS puede devolver 200 con un XML de error en vez de imagen
    if "image" not in r.headers.get("Content-Type", "image"):
        raise RuntimeError(f"El WMS no devolvió una imagen: {r.text[:200]}")
    return Image.open(BytesIO(r.content)).convert("RGBA")


def _export_geode(bbox_str, width, height, capas=None, where=None):
    """
    PNG (bytes) del export de GEODE.
      capas="8"  -> solo esa capa (layers=show:8)
      where=...  -> además, solo los recintos que cumplen la condición (layerDefs)
    """
    params = {
        "f": "image", "bbox": bbox_str, "bboxSR": 4326, "imageSR": 4326,
        "format": "png32", "transparent": "true",
        "size": f"{int(width)},{int(height)}", "dpi": DPI,
    }
    if capas:
        params["layers"] = f"show:{capas}"
    if where:
        params["layerDefs"] = json.dumps({str(CAPA_RECINTOS): where})
    url = f"{IGME_URL}/export"
    if where and len(where) > 1200:      # listas largas de recintos: por POST
        r = requests.post(url, data=params, timeout=60)
    else:
        r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    if "image" not in r.headers.get("Content-Type", "image"):
        raise RuntimeError(f"GEODE no devolvió una imagen: {r.text[:200]}")
    return r.content


@st.cache_data(show_spinner=False)
def descargar_geode_transparente(bbox_str, width, height, capas=None):
    return Image.open(BytesIO(_export_geode(bbox_str, width, height, capas))).convert("RGBA")


@st.cache_data(show_spinner=False)
def render_unidades(bbox_str, width, height, wheres):
    """Un export por unidad (solo sus recintos), en paralelo. {where: png_bytes}."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        datos = list(pool.map(
            lambda q: _export_geode(bbox_str, width, height, str(CAPA_RECINTOS), q), wheres))
    return dict(zip(wheres, datos))


def _clave(texto):
    """'Código de Unidad Geológica' / 'CódigodeUnidadGeológica' -> 'codigodeunidadgeologica'."""
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if c.isalnum() and not unicodedata.combining(c)).lower()


CAMPOS_GFI = {
    "objectid": "OBJECTID",
    "codigodeunidadgeologica": "CODE_UNIO",
    "descripcionunidadgeologica": "DESC_UNIT",
    "codigodesimbolizacion": "CODE_COTR",
    "edadsuperior": "EDAD_SUP",
    "edadinferior": "EDAD_INF",
    "codigozonageode": "ZONA",
}


def _gfi_tesela(cx, cy, ancho_g, alto_g):
    """
    Un GetFeatureInfo WMS cuya "huella" (GFI_HUELLA_PX píxeles virtuales)
    cubre una tesela de ancho_g x alto_g grados centrada en (cx, cy).
    Devuelve la lista de recintos (dict) que tocan esa huella.
    """
    px, py = ancho_g / GFI_HUELLA_PX, alto_g / GFI_HUELLA_PX
    params = {
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo",
        "LAYERS": WMS_CAPA_RECINTOS, "QUERY_LAYERS": WMS_CAPA_RECINTOS, "STYLES": "",
        "SRS": "EPSG:4326",
        "BBOX": f"{cx - 4.5 * px},{cy - 4.5 * py},{cx + 4.5 * px},{cy + 4.5 * py}",
        "WIDTH": 9, "HEIGHT": 9, "X": 4, "Y": 4,          # píxel central de una imagen 9x9
        "INFO_FORMAT": "application/geo+json", "FEATURE_COUNT": GFI_MAX,
    }
    r = requests.get(WMS_GEODE_URL, params=params, timeout=30)
    r.raise_for_status()
    texto = r.text
    if "ServiceException" in texto:
        raise RuntimeError(f"El WMS de GEODE rechazó la consulta: {texto[:300]}")

    try:                                                   # respuesta GeoJSON
        crudos = [f.get("properties") or {} for f in json.loads(texto).get("features", [])]
    except ValueError:                                     # respuesta XML (<FIELDS .../>)
        crudos = [dict(el.attrib) for el in ET.fromstring(r.content).iter() if el.tag.endswith("FIELDS")]

    recintos = []
    for props in crudos:
        fila = {CAMPOS_GFI[_clave(k)]: (str(v).strip() if v is not None else None)
                for k, v in props.items() if _clave(k) in CAMPOS_GFI}
        if fila.get("CODE_UNIO"):
            recintos.append(fila)
    return recintos


@st.cache_data(show_spinner=False)
def obtener_recintos(bbox):
    """
    Recintos CANDIDATOS del encuadre (y su borde), vía WMS GetFeatureInfo.

    El IGME ha desactivado query/identify/find en el servicio REST de GEODE
    ("No está permitida la capacidad solicitada"), así que ya no se pueden
    pedir los recintos como vectores. El WMS sí devuelve los ATRIBUTOS (sin
    geometría) de todo lo que cae alrededor de un punto: se barre el encuadre
    con una malla de teselas solapadas y se unen los resultados por OBJECTID.

    Devuelve (df_recintos, truncado) o None si no hay nada. Es una lista de
    candidatos: analizar_encuadre() comprueba después cuáles se ven en la imagen.
    Lanza excepción si falla la red (así no se cachea el fallo).
    """
    minx, miny, maxx, maxy = bbox
    w, h = maxx - minx, maxy - miny
    lado = max(w, h) / GFI_TESELAS_LADO_MAYOR
    nx, ny = max(1, math.ceil(w / lado - 1e-9)), max(1, math.ceil(h / lado - 1e-9))
    tw, th = w / nx, h / ny
    centros = [(minx + (i + 0.5) * tw, miny + (j + 0.5) * th) for i in range(nx) for j in range(ny)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(lambda c: _gfi_tesela(c[0], c[1], tw, th), centros))

    truncado = any(len(res) >= GFI_MAX for res in resultados)
    por_id = {}
    for res in resultados:
        for fila in res:
            por_id[fila.get("OBJECTID") or len(por_id)] = fila
    if not por_id:
        return None

    df = pd.DataFrame(por_id.values())
    for col in ("DESC_UNIT", "CODE_COTR", "EDAD_SUP", "EDAD_INF", "ZONA"):
        if col not in df:
            df[col] = None
    df["ZONA"] = df["ZONA"].fillna("")
    return df, truncado


def _ventana_llena(mask, k):
    """Esquina (x, y) de la ventana k x k más céntrica totalmente dentro de mask, o None."""
    H, W = mask.shape
    if H < k or W < k:
        return None
    ii = np.pad(mask.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    llenas = (ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]) == k * k
    ys, xs = np.nonzero(llenas)
    if not len(ys):
        return None
    i = np.argmin((ys - np.median(ys)) ** 2 + (xs - np.median(xs)) ** 2)
    return int(xs[i]), int(ys[i])


def _icono_de(img_unidad, mask, lado=20, margen=2):
    """Símbolo de la unidad recortado de su propio dibujo (o su color dominante)."""
    plano = Image.alpha_composite(Image.new("RGBA", img_unidad.size, "white"), img_unidad).convert("RGB")
    esquina = _ventana_llena(mask, lado + 2 * margen)
    if esquina:
        x0, y0 = esquina[0] + margen, esquina[1] + margen
        return plano.crop((x0, y0, x0 + lado, y0 + lado))
    colores, n = np.unique(np.asarray(plano)[mask], axis=0, return_counts=True)
    return Image.new("RGB", (lado, lado), tuple(int(c) for c in colores[n.argmax()]))


def _agrupar(rec):
    """{(ZONA, CODE_UNIO): (fila de atributos, tupla de OBJECTID)}. El código de unidad
    solo es único dentro de cada zona GEODE."""
    grupos = {}
    for clave, g in rec.groupby(["ZONA", "CODE_UNIO"], sort=False):
        ids = sorted({str(i) for i in g["OBJECTID"].dropna() if str(i).isdigit()}, key=int)
        grupos[clave] = (g.iloc[0], tuple(ids))
    return grupos


def analizar_encuadre(bbox, bbox_str, w, h):
    """
    Unidades que REALMENTE aparecen en la imagen, con su símbolo.

    1. Candidatos: recintos del encuadre y su borde (obtener_recintos).
    2. Por cada unidad candidata se pide a GEODE la misma imagen pero dibujando
       solo sus recintos. Si no pinta ningún píxel, la unidad no está en la
       imagen y se descarta; si pinta, de ahí sale su símbolo y su % de área.
    3. Control de cobertura: la suma de todas las unidades debe tapar todo lo
       pintado en la capa de recintos. Si queda un hueco, se pregunta al WMS qué
       hay en ese punto y se añade la unidad que faltaba.

    Devuelve None si no hay recintos, o un dict con:
      df, iconos, verificado, cobertura, descartadas, truncado, aviso
    """
    res = obtener_recintos(bbox)
    if res is None:
        return None
    rec, truncado = res
    unidades = _agrupar(rec)
    cols = ["CODE_UNIO", "DESC_UNIT", "CODE_COTR", "EDAD_SUP", "EDAD_INF", "ZONA"]

    def tabla(claves, extra=None):
        filas = []
        for k in claves:
            fila = {c: unidades[k][0].get(c) for c in cols}
            fila.update((extra or {}).get(k, {}))
            filas.append(fila)
        df = pd.DataFrame(filas)
        df["_num"] = pd.to_numeric(df["CODE_UNIO"], errors="coerce")
        return df.sort_values(by=["_num", "CODE_UNIO", "ZONA"], kind="mergesort").drop(columns="_num").reset_index(drop=True)

    try:
        minx, miny, maxx, maxy = bbox
        px, py = (maxx - minx) / w, (maxy - miny) / h
        img_rec = descargar_geode_transparente(bbox_str, w, h, capas=str(CAPA_RECINTOS))
        dibujado = np.asarray(img_rec.getchannel("A")) > UMBRAL_ALFA
        rgb_rec = np.asarray(img_rec)[..., :3].astype(np.int16)
        # clave -> (imagen, máscara pintada, máscara "coincide con el mapa") ; clave -> ids usados
        capas_u, hechas = {}, {}

        def procesar():
            pendientes = [k for k, (_, ids) in unidades.items() if ids and hechas.get(k) != ids]
            wheres = tuple("OBJECTID IN (" + ",".join(unidades[k][1]) + ")" for k in pendientes)
            pngs = render_unidades(bbox_str, w, h, wheres) if wheres else {}
            for k, q in zip(pendientes, wheres):
                im = Image.open(BytesIO(pngs[q])).convert("RGBA")
                if im.size != (w, h):
                    raise RuntimeError("tamaño de imagen inesperado")
                m = np.asarray(im.getchannel("A")) > UMBRAL_ALFA
                # Un píxel queda "explicado" por la unidad solo si además tiene el mismo color
                # que en el mapa de recintos (no basta con que la unidad pinte ahí).
                igual = m & dibujado & (np.abs(np.asarray(im)[..., :3].astype(np.int16) - rgb_rec).max(axis=2) <= 24)
                capas_u[k] = (im, m, igual)
                hechas[k] = unidades[k][1]
            return bool(pendientes)

        procesar()
        total = int(dibujado.sum())
        if len(capas_u) >= 2 and total and all(c[1].sum() > 0.98 * total for c in capas_u.values()):
            raise RuntimeError("el servidor no aplica el filtro por recintos (layerDefs)")

        hueco = dibujado
        for _ in range(8):                           # control de cobertura + rescate
            explicado = np.zeros_like(dibujado)
            for c in capas_u.values():
                explicado |= c[2]
            hueco = dibujado & ~explicado
            esquina = _ventana_llena(hueco, 5)
            if esquina is None:
                break
            lon = minx + (esquina[0] + 2.5) * px
            lat = maxy - (esquina[1] + 2.5) * py
            nuevos = pd.DataFrame(_gfi_tesela(lon, lat, 2 * px, 2 * py))
            if nuevos.empty:
                break
            for col in cols:
                if col not in nuevos:
                    nuevos[col] = None
            nuevos["ZONA"] = nuevos["ZONA"].fillna("")
            rec = pd.concat([rec, nuevos], ignore_index=True).drop_duplicates(subset=["OBJECTID"])
            unidades = _agrupar(rec)
            if not procesar():
                break
        # Los bordes entre recintos (suavizado) no cuentan: solo huecos de 3x3 px o más
        H_, W_ = hueco.shape
        ii = np.pad(hueco.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        n_hueco = int(((ii[3:, 3:] - ii[:-3, 3:] - ii[3:, :-3] + ii[:-3, :-3]) == 9).sum()) if min(H_, W_) >= 3 else 0
        cobertura = 1.0 - (n_hueco / total if total else 0.0)

        visibles, descartadas, iconos, extra = [], [], {}, {}
        for k in unidades:
            im, m, _igual = capas_u.get(k, (None, None, None))
            n_px = int(m.sum()) if m is not None else 0
            if n_px >= MIN_PX_VISIBLE:
                visibles.append(k)
                iconos[k] = _icono_de(im, m)
                extra[k] = {"PCT_IMAGEN": round(100.0 * n_px / (w * h), 2)}
            else:
                descartadas.append(str(k[1]))
        if not visibles:
            return None
        return {"df": tabla(visibles, extra), "iconos": iconos, "verificado": True,
                "cobertura": cobertura, "descartadas": sorted(set(descartadas), key=lambda c: (len(c), c)),
                "truncado": truncado, "aviso": None}

    except Exception as e:
        # Plan B: sin verificación (todas las candidatas, símbolos de /legend)
        iconos = {}
        try:
            simbolos = obtener_simbolos_leyenda()
        except Exception:
            simbolos = {}
        for k, (fila, _) in unidades.items():
            b64 = simbolos.get(normalizar_cotr(fila.get("CODE_COTR")))
            if b64:
                try:
                    iconos[k] = Image.open(BytesIO(base64.b64decode(b64))).convert("RGBA")
                except Exception:
                    pass
        return {"df": tabla(list(unidades)), "iconos": iconos, "verificado": False, "cobertura": None,
                "descartadas": [], "truncado": truncado, "aviso": str(e)}

@st.cache_data(show_spinner=False, ttl=24 * 3600)
def obtener_simbolos_leyenda(layer_id=CAPA_RECINTOS):
    """
    Diccionario {CODE_COTR (8 dígitos): icono en base64} de la capa de recintos.
    La respuesta del IGME pesa ~1,6 MB: se cachea (antes se descargaba entera
    en CADA rerun, con timeout de 10 s).
    """
    copia = Path(__file__).parent / f"simbolos_geode_capa{layer_id}.json"
    try:
        r = requests.get(f"{IGME_URL}/legend", params={"f": "json"}, timeout=90)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Error del servicio GEODE: {data['error']}")
    except Exception:
        if copia.exists():          # última leyenda buena guardada en disco
            return json.loads(copia.read_text(encoding="utf-8"))
        raise
    capa = next((l for l in data.get("layers", []) if l.get("layerId") == layer_id), None)
    if capa is None:
        raise RuntimeError(f"La leyenda del servicio no contiene la capa {layer_id}")

    simbolos = {}
    for item in capa.get("legend", []):
        img = item.get("imageData")
        if not img:
            continue
        # 'values' no existe en ítems tipo "<all other values>" ni en servidores
        # antiguos: antes un solo ítem sin 'values' anulaba TODA la leyenda.
        for clave in (item.get("values") or [item.get("label")]):
            if clave is not None:
                simbolos[str(clave).strip()] = img
    try:
        copia.write_text(json.dumps(simbolos), encoding="utf-8")
    except OSError:
        pass
    return simbolos


# ----------------------------------------------------------------------
# 2. LÓGICA DE COMPOSICIÓN Y LEYENDA
# ----------------------------------------------------------------------

def componer_imagen(img_base, img_geode, opacidad, usar_fondo_blanco):
    top_layer = img_geode.copy()
    if opacidad < 1.0:
        r, g, b, a = top_layer.split()
        a = a.point(lambda p: int(p * opacidad))
        top_layer = Image.merge("RGBA", (r, g, b, a))

    if usar_fondo_blanco:
        base = Image.new("RGBA", top_layer.size, (255, 255, 255, 255))
        return Image.alpha_composite(base, top_layer)
    if img_base:
        if img_base.size != top_layer.size:
            img_base = img_base.resize(top_layer.size)
        return Image.alpha_composite(img_base, top_layer)
    return top_layer


def cargar_fuente(size, negrita=False):
    """
    Busca una fuente TrueType con tildes. 'arial.ttf' solo existe en Windows;
    en Linux / Streamlit Cloud se caía a la fuente por defecto de Pillow, que
    es más pequeña y pinta 'Ó', 'Í', 'ñ'... como recuadros.
    Para blindarlo: copiar DejaVuSans.ttf junto a este script, o añadir
    'fonts-dejavu-core' a packages.txt en Streamlit Cloud.
    """
    aqui = Path(__file__).parent
    nombres = (["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if negrita
               else ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    candidatos = [str(aqui / n) for n in nombres] + nombres
    try:
        import matplotlib
        candidatos.append(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / nombres[1]))
    except Exception:
        pass
    for c in candidatos:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def normalizar_cotr(valor):
    """CODE_COTR -> texto de 8 dígitos, venga como int, float ('2014.0') o str."""
    if valor is None or pd.isna(valor):
        return None
    s = str(valor).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(8) if s.isdigit() else s


def envolver_texto(texto, font, ancho_max):
    """Parte el texto midiendo píxeles reales (no nº de caracteres)."""
    lineas, actual = [], ""
    for palabra in str(texto).split():
        prueba = f"{actual} {palabra}".strip()
        if not actual or font.getlength(prueba) <= ancho_max:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas or [""]


def generar_leyenda(df_csv, iconos, w_total=450):
    """
    Devuelve (imagen, lista_de_unidades_sin_símbolo).
    iconos: {(ZONA, CODE_UNIO): imagen PIL}. Una línea por unidad de df_csv;
    las que no tengan icono se dibujan con un recuadro vacío.
    """
    if df_csv is None or df_csv.empty:
        return None, []

    font = cargar_fuente(14)
    font_titulo = cargar_fuente(15, negrita=True)
    ICONO, MARGEN, SEP = 20, 10, 10
    x_text = MARGEN + ICONO + 10
    ancho_texto = w_total - x_text - MARGEN
    asc, desc = font.getmetrics()
    h_linea = asc + desc + 2

    entries, sin_simbolo = [], []
    unique = df_csv[["ZONA", "CODE_UNIO", "DESC_UNIT"]].drop_duplicates()
    for _, row in unique.iterrows():
        desc_unit = row["DESC_UNIT"]
        desc_unit = "(sin descripción)" if pd.isna(desc_unit) or not str(desc_unit).strip() else str(desc_unit).strip()
        txt = f"{row['CODE_UNIO']} - {desc_unit}"

        icono = iconos.get((row["ZONA"], row["CODE_UNIO"]))
        if icono is not None:
            icono = icono.convert("RGBA")
            if icono.size != (ICONO, ICONO):
                icono = icono.resize((ICONO, ICONO))
        if icono is None:
            sin_simbolo.append(str(row["CODE_UNIO"]))
        entries.append({"icono": icono, "lineas": envolver_texto(txt, font, ancho_texto)})

    y0 = 45
    h_total = y0 + sum(max(ICONO, len(e["lineas"]) * h_linea) + SEP for e in entries) + MARGEN

    img = Image.new("RGB", (w_total, h_total), "white")
    draw = ImageDraw.Draw(img)
    draw.text((MARGEN, 12), "LEYENDA GEOLÓGICA", fill="black", font=font_titulo)

    y = y0
    for e in entries:
        if e["icono"] is not None:
            # Con máscara alfa: sin ella las tramas (rayados) dejaban la leyenda
            # con zonas transparentes, negras al pasar a JPG/Word.
            img.paste(e["icono"], (MARGEN, y), e["icono"])
        draw.rectangle((MARGEN, y, MARGEN + ICONO, y + ICONO), outline=(110, 110, 110))
        for i, linea in enumerate(e["lineas"]):
            draw.text((x_text, y + i * h_linea), linea, fill="black", font=font)
        y += max(ICONO, len(e["lineas"]) * h_linea) + SEP

    return img, sin_simbolo


def png_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------
# 3. INTERFAZ Y LÓGICA PRINCIPAL
# ----------------------------------------------------------------------

def reset_zip():
    st.session_state.pop("zip_ready", None)
    st.session_state.pop("zip_data", None)


def fondo_seguro(bbox, w, h, tipo):
    """Descarga un fondo; si falla avisa y devuelve None (sin cachear el fallo)."""
    try:
        return descargar_fondo_base(bbox, w, h, tipo)
    except Exception as e:
        st.warning(f"No se pudo descargar el fondo {tipo}: {e}")
        return None


st.title("🗺️ Visor GEODE")
st.markdown("""
**CEMOSA - DEPARTAMENTO DE GEOTECNIA**
\n
Esta herramienta descarga los datos oficiales del **IGME (GEODE)** y los combina con el **PNOA** o el **MTN**.
Al descargar, obtendrás un ZIP con:
1. El mapa compuesto (según se ve en pantalla).
2. La ortofoto original (PNOA) .
3. El topográfico original (MTN).
4. La capa geológica (fondo transparente, opacidad 100 %).
5. La tabla de unidades geológicas que aparecen en la imagen, con su % de superficie (CSV).
6. Leyenda correspondiente a la cartografía geológica.
7. No se incluye a Cataluña que tiene su propio servicio.
""")


st.markdown(""" Siguiendo la directiva ITQ404 """)

# --- Sidebar (Controles) ---
with st.sidebar:
    st.header("1. Localización (ETRS89 UTM)")
    c1, c2 = st.columns(2)
    x = c1.number_input("E (m)", value=342765.0, step=100.0, format="%.1f", on_change=reset_zip)
    y = c2.number_input("N (m)", value=4203718.0, step=100.0, format="%.1f", on_change=reset_zip)
    zona = st.selectbox("Huso UTM", [29, 30, 31, 28], index=1, on_change=reset_zip)

    st.header("2. Encuadre")
    ancho = st.number_input("Ancho mapa (m)", value=2000.0, min_value=100.0, on_change=reset_zip)
    alto = st.number_input("Alto mapa (m)", value=1500.0, min_value=100.0, on_change=reset_zip)

    st.markdown("---")
    st.header("3. Visualización")
    fondo = st.radio("Fondo Visualización:", ["PNOA (Foto)", "MTN (Topo)"], horizontal=True, on_change=reset_zip)
    fondo_cod = "PNOA" if "PNOA" in fondo else "TOPO"

    blanco = st.checkbox("Fondo Blanco (Geología sola)", value=False, on_change=reset_zip)

    if not blanco:
        opacidad = st.slider("Opacidad Geología", 0.0, 1.0, 0.6, 0.1, on_change=reset_zip)
    else:
        opacidad = 1.0

# --- LÓGICA AUTOMÁTICA (PREVIEW RÁPIDA) ---

# 1. Cálculos de Coordenadas
epsg = deducir_epsg_desde_zona(zona)
media_x, media_y = ancho / 2.0, alto / 2.0
minx, maxx = x - media_x, x + media_x
miny, maxy = y - media_y, y + media_y

tf_4326 = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

esquina_utm = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)]
esquina_4326 = [tf_4326.transform(vx, vy) for (vx, vy) in esquina_utm]

lons = [p[0] for p in esquina_4326]
lats = [p[1] for p in esquina_4326]
bbox_img = (min(lons), min(lats), max(lons), max(lats))
bbox_str = f"{bbox_img[0]},{bbox_img[1]},{bbox_img[2]},{bbox_img[3]}"

# Dimensiones en píxeles (enteros; antes una era float y otra int)
MAX_PX = 1200
if ancho >= alto:
    w_px, h_px = MAX_PX, max(1, round(MAX_PX * alto / ancho))
else:
    w_px, h_px = max(1, round(MAX_PX * ancho / alto)), MAX_PX

# Escala de petición: el servicio oculta capas según la escala
escala = max(ancho / w_px, alto / h_px) / (0.0254 / DPI)
if escala > ESCALA_MAX_RECINTOS:
    st.error(f"Escala ≈ 1:{escala:,.0f}. GEODE no dibuja los recintos geológicos por encima de "
             f"1:{ESCALA_MAX_RECINTOS:,}: reduce el encuadre (máx. ≈ {ESCALA_MAX_RECINTOS * MAX_PX * 0.0254 / DPI / 1000:.0f} km).")
elif escala > ESCALA_MAX_ROTULOS:
    st.caption(f"Escala ≈ 1:{escala:,.0f}: a esta escala GEODE no rotula las unidades en el mapa "
               f"(solo por debajo de 1:{ESCALA_MAX_ROTULOS:,}).")

# 2. Descargas de lo VISIBLE
with st.spinner("Actualizando vista..."):
    try:
        img_geode = descargar_geode_transparente(bbox_str, w_px, h_px)
    except Exception as e:
        st.error(f"No se pudo descargar la geología de GEODE: {e}")
        img_geode = Image.new("RGBA", (w_px, h_px), (0, 0, 0, 0))

    img_base_visible = None if blanco else fondo_seguro(bbox_img, w_px, h_px, fondo_cod)

    error_vectores = None
    try:
        vectores = analizar_encuadre(bbox_img, bbox_str, w_px, h_px)
    except Exception as e:
        vectores, error_vectores = None, e

# 3. Composición en Pantalla
img_preview = componer_imagen(img_base_visible, img_geode, opacidad, blanco)

col_map, col_leyenda = st.columns([2, 1.2])

with col_map:
    st.image(img_preview, caption=f"Vista Previa ({'Fondo blanco' if blanco else fondo_cod})",
             width="stretch")

df_csv, img_ley = None, None
with col_leyenda:
    if vectores:
        df_csv = vectores["df"]
        if vectores["verificado"]:
            st.success(f"Unidades en la imagen: {len(df_csv)} · comprobadas una a una contra el mapa "
                       f"(cobertura {vectores['cobertura'] * 100:.1f} %)")
            if vectores["cobertura"] < 0.995:
                st.warning("Queda una parte del mapa sin unidad asignada: puede faltar alguna unidad en la leyenda.")
            if vectores["descartadas"]:
                st.caption("Unidades próximas descartadas por no verse en la imagen: "
                           + ", ".join(vectores["descartadas"]))
        else:
            st.warning(f"Unidades candidatas: {len(df_csv)}. NO se ha podido comprobar contra la imagen "
                       f"({vectores['aviso']}); puede incluir alguna unidad del borde exterior.")
        if vectores["truncado"]:
            st.warning("Alguna consulta ha llegado al máximo de recintos: reduce el encuadre.")
        img_ley, sin_simbolo = generar_leyenda(df_csv, vectores["iconos"])
        if img_ley:
            st.image(img_ley, caption="Leyenda", width="stretch")
        if sin_simbolo:
            st.warning(f"Unidades sin símbolo (recuadro vacío): {', '.join(sin_simbolo)}")
    elif error_vectores is not None:
        st.error(f"Error consultando los datos geológicos: {error_vectores}")
    else:
        st.warning("Sin datos geológicos en esta zona.")

# ----------------------------------------------------------------------
# 4. GESTIÓN DE DESCARGA
# ----------------------------------------------------------------------
st.markdown("---")
st.subheader("📦 Descarga de Datos")

if "zip_ready" not in st.session_state:
    st.session_state.zip_ready = False
    st.session_state.zip_data = None

if not st.session_state.zip_ready:
    if st.button("🚀 Generar Paquete Completo (Imágenes + Datos)"):
        with st.spinner("Descargando capas ocultas y comprimiendo..."):

            # Se piden SIEMPRE los dos fondos (la caché evita repetir la descarga).
            # Antes, con "Fondo Blanco" marcado, uno de los dos no entraba en el ZIP.
            img_pnoa_zip = fondo_seguro(bbox_img, w_px, h_px, "PNOA")
            img_mtn_zip = fondo_seguro(bbox_img, w_px, h_px, "TOPO")

            mem_zip = BytesIO()
            with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("mapa_compuesto.png", png_bytes(img_preview))
                if img_ley:
                    zf.writestr("leyenda.png", png_bytes(img_ley))
                if df_csv is not None:
                    # utf-8-sig: Excel abre bien las tildes
                    zf.writestr("datos_geologicos.csv",
                                df_csv.to_csv(sep=";", index=False).encode("utf-8-sig"))
                zf.writestr("capa_geologia.png", png_bytes(img_geode))
                if img_pnoa_zip:
                    zf.writestr("capa_pnoa.png", png_bytes(img_pnoa_zip))
                if img_mtn_zip:
                    zf.writestr("capa_mtn.png", png_bytes(img_mtn_zip))
                zf.writestr("LEEME.txt", (
                    f"Centro (ETRS89 UTM huso {zona}): E={x:.1f} N={y:.1f}\n"
                    f"Encuadre: {ancho:.0f} x {alto:.0f} m  |  Escala de peticion ~1:{escala:,.0f}\n"
                    f"BBOX imagenes (EPSG:4326, lon/lat): {bbox_str}\n"
                    f"Tamano imagenes: {w_px} x {h_px} px\n"
                    "Fuentes: IGME (GEODE 1:50.000), IGN (PNOA, MTN)\n"
                ).encode("utf-8"))

            st.session_state.zip_ready = True
            st.session_state.zip_data = mem_zip.getvalue()
            st.rerun()

if st.session_state.zip_ready:
    col_d1, col_d2 = st.columns([1, 4])
    with col_d1:
        st.download_button(
            label="📥 DESCARGAR ZIP",
            data=st.session_state.zip_data,
            file_name="geopack.zip",
            mime="application/zip",
            type="primary",
        )
    with col_d2:
        st.info("Paquete generado. Si se cambia algún dato, tendrás que volver a generar el paquete.")
