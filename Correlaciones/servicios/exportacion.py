from __future__ import annotations

import csv
import io

from modelos.esquemas import ResultadoCorrelacion


def resultados_a_csv(resultados: list[ResultadoCorrelacion]) -> bytes:
    salida = io.StringIO(newline="")
    campos = ["autor", "aplicacion", "formula", "valor", "unidad", "parametros", "aplicable", "estado", "criterio", "nota", "referencia"]
    escritor = csv.DictWriter(salida, fieldnames=campos, delimiter=";")
    escritor.writeheader()
    escritor.writerows(resultado.como_fila() for resultado in resultados)
    return salida.getvalue().encode("utf-8-sig")

