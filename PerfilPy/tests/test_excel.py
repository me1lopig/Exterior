import io
import unittest
import zipfile

from openpyxl import Workbook

from servicios.excel import cargar_proyecto, expandir_archivos


def workbook_bytes(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


class Upload:
    def __init__(self, name, content):
        self.name = name
        self._content = content

    def getvalue(self):
        return self._content


class ExcelTests(unittest.TestCase):
    def _files(self):
        lab_headers = [f"C{i}" for i in range(40)]
        lab = [None] * 40
        lab[1], lab[2], lab[3], lab[8], lab[30] = "S-01", "SPT", 3, "12", "SPT"
        return {
            "BKFL.XLSX": workbook_bytes(
                ["id", "fecha", "pi", "pf", "estrato", "corta", "larga"],
                [["S-01", None, 0, 5, 1, "Grava", "Grava arenosa"]],
            ),
            "DPRG.XLSX": workbook_bytes(
                [f"C{i}" for i in range(8)], [["P-01", None, None, None, None, None, 0.2, 10]]
            ),
            "ListadoLab.XLSX": workbook_bytes(lab_headers, [lab]),
            "ISPT.XLSX": workbook_bytes(
                [f"C{i}" for i in range(7)], [["S-01", 3, None, None, 12, None, 0]]
            ),
            "PERFIL.xlsx": workbook_bytes(
                ["ESTACION", "Distancia", "Cota"], [["S-01", 100, 50], ["P-01", 120, 49]]
            ),
            "LOCA.XLSX": workbook_bytes(
                ["Descripcion Muestra", "Clase", "Expediente"], [["S-01", "SONDEO", "X"]]
            ),
        }

    def test_schema_recognition_ignores_loca(self):
        data = cargar_proyecto(self._files())
        self.assertEqual(list(data.perfiles["perfil"].unique()), ["PERFIL"])
        self.assertEqual(data.archivos_ignorados, ["LOCA.XLSX"])
        self.assertEqual(list(data.perfiles["tipo"]), ["Sondeo", "DPSH"])

    def test_zip_expansion(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("folder/PERFIL.xlsx", self._files()["PERFIL.xlsx"])
        files = expandir_archivos([Upload("datos.zip", stream.getvalue())])
        self.assertEqual(list(files), ["PERFIL.xlsx"])


if __name__ == "__main__":
    unittest.main()
