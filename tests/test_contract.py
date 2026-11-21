"""Contrato HTTP común. Cada caso inicia un servidor y una base independientes."""
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = os.environ.get("STOCKAULA_RUNTIME", "python")


class InventoryContract(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / "stock.db"
        self.start_server()

    def start_server(self):
        command = ([sys.executable, "-u", "app.py", "--db", str(self.database)]
                   if RUNTIME == "python" else ["node", "scripts/worker-local.mjs"])
        self.server = subprocess.Popen(command + ["--port", "0"], cwd=ROOT, text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.addCleanup(self.stop_server)
        self.url = self.server.stdout.readline().strip().removeprefix("StockAula en ")
        self.assertTrue(self.url.startswith("http://127.0.0.1:"), "El servidor debe iniciar y anunciar su puerto.")

    def stop_server(self):
        if self.server.poll() is None:
            self.server.terminate()
            self.server.wait(timeout=5)
        self.server.stdout.close()

    def call(self, path, data=None, headers=None):
        kwargs = {} if data is None else {"data": json.dumps(data).encode(),
                                          "headers": {"Content-Type": "application/json", **(headers or {})}}
        req = request.Request(self.url + path, **kwargs)
        try:
            reply = request.urlopen(req, timeout=6)
        except error.HTTPError as exc:
            reply = exc
        with reply:
            return reply.status, json.load(reply)

    def product(self, code="MAT-001", minimum=5):
        return self.call("/api/products", {"code": code, "name":"Papel bond A4","category":"Papelería","minimum":minimum})

    def move(self, kind, amount, key=None, code="MAT-001"):
        return self.call("/api/movements", {"code":code,"kind":kind,"quantity":amount,
                                            "reason":"Práctica de almacén","request_key":key or str(uuid.uuid4())})

    def state(self):
        status, data = self.call("/api/state")
        self.assertEqual(status, 200)
        return data

    def test_salud_y_tablero_vacio(self):
        self.assertEqual(self.call("/api/health")[1]["service"], "StockAula")
        self.assertEqual(self.state()["stats"], dict(products=0,units=0,alerts=0,movements=0))

    def test_catalogo_normaliza_codigo_y_rechaza_duplicados(self):
        self.assertEqual(self.product(" mat-001 ")[0], 201)
        self.assertEqual(self.product("MAT-001")[0], 409)
        self.assertEqual([p["code"] for p in self.state()["products"]], ["MAT-001"])

    def test_campos_y_minimo_validos(self):
        self.assertEqual(self.product(minimum=-1)[0], 400)
        self.assertEqual(self.product("!!")[0], 400)
        self.assertEqual(self.call("/api/products", {"code":"MAT-001","name":"  ","category":"Papelería","minimum":5})[0],400)
        self.assertEqual(self.state()["products"], [])

    def test_saldo_minimo_inclusivo(self):
        self.product()
        self.move("entrada", 10)
        self.assertEqual(self.state()["stats"]["alerts"], 0)
        self.move("salida", 5)
        self.assertEqual(self.state()["stats"], dict(products=1,units=5,alerts=1,movements=2))

    def test_stock_insuficiente_sin_asiento(self):
        self.product(); self.move("entrada", 20); self.move("salida", 16)
        before = self.state()
        self.assertEqual(self.move("salida", 5)[0], 409)
        self.assertEqual(self.state(), before)
        self.assertEqual(before["stats"]["units"], 4)

    def test_producto_inexistente(self):
        self.assertEqual(self.move("salida", 2, code="XYZ")[0], 404)
        self.assertEqual(self.state()["movements"], [])

    def test_cantidades_solo_enteras_positivas(self):
        self.product()
        for value in (0,-1,1.5,"3",True,1000000):
            with self.subTest(value=value):
                self.assertEqual(self.move("entrada",value)[0],400)
        self.assertEqual(self.state()["stats"]["units"],0)

    def test_historial_ordenado_y_motivo(self):
        self.product()
        self.move("entrada", 8); self.move("salida", 3)
        rows = self.state()["movements"]
        self.assertEqual([r["kind"] for r in rows], ["salida","entrada"])
        self.assertEqual(rows[0]["reason"],"Práctica de almacén")
        self.assertEqual(rows[0]["name"],"Papel bond A4")

    def test_dos_salidas_compiten_por_una_unidad(self):
        self.product(); self.move("entrada", 1)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(lambda _: self.move("salida",1)[0], range(2)))
        self.assertEqual(sorted(replies),[201,409])
        self.assertEqual(self.state()["stats"]["units"],0)
        self.assertEqual(self.state()["stats"]["movements"],2)

    def test_escritura_desde_otro_origen(self):
        self.assertEqual(self.call("/api/products",{},{"Origin":"https://otro.ejemplo"})[0],403)

    def test_json_malformado_y_tipo_de_contenido(self):
        self.assertEqual(self.call("/api/products",{},{"Content-Type":"text/plain"})[0],415)
        bad = request.Request(self.url+"/api/products",data=b"[",headers={"Content-Type":"application/json"})
        with self.assertRaises(error.HTTPError) as caught:
            request.urlopen(bad,timeout=5)
        self.assertEqual(caught.exception.code,400)
        caught.exception.close()

    def test_activos_de_la_interfaz(self):
        for path,needle in [("/",b"StockAula"),("/app.js",b"/api/state"),("/style.css",b".summary")]:
            with request.urlopen(self.url+path,timeout=5) as reply:
                self.assertEqual(reply.status,200)
                self.assertIn(needle,reply.read())
