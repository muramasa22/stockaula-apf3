"""Muestra SA-01 por HTTP en una base temporal; no modifica el inventario de clase."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]


def call(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = request.Request(base + path, data=data, headers={"Content-Type":"application/json"})
    try:
        response = request.urlopen(req,timeout=6)
    except error.HTTPError as exc:
        response = exc
    with response:
        return response.status,json.load(response)


def demo():
    with tempfile.TemporaryDirectory() as tmp:
        cmd=[sys.executable,"-u",str(ROOT/"app.py"),"--port","0","--db",str(Path(tmp)/"demo.db")]
        with subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True) as server:
            try:
                base=server.stdout.readline().strip().removeprefix("StockAula en ")
                print("Entorno local temporal | StockAula")
                status,_ = call(base,"/api/products",{"code":"MAT-001","name":"Papel bond A4","category":"Papelería","minimum":5})
                print(f"Alta de MAT-001                        HTTP {status}")
                common={"code":"MAT-001","reason":"Práctica de almacén"}
                entry={**common,"kind":"entrada","quantity":20,"request_key":"entrada-demo-001"}
                withdrawal={**common,"kind":"salida","quantity":6,"request_key":"salida-demo-001"}
                status,_=call(base,"/api/movements",entry)
                print(f"Entrada de 20 unidades                 HTTP {status}")
                first,one=call(base,"/api/movements",withdrawal)
                print(f"Salida de 6 | folio salida-demo-001    HTTP {first} · movimiento {one['id']}")
                second,two=call(base,"/api/movements",withdrawal)
                print(f"Reenvío del mismo folio                HTTP {second} · movimiento {two['id']}")
                changed,_=call(base,"/api/movements",{**withdrawal,"quantity":7})
                print(f"Mismo folio con otra cantidad          HTTP {changed}")
                denied,_=call(base,"/api/movements",{**withdrawal,"quantity":15,"request_key":"salida-demo-002"})
                print(f"Salida mayor que el saldo              HTTP {denied}")
                _,values=call(base,"/api/state")
                stats=values["stats"]
                print(f"Saldo final: {stats['units']} unidades | Movimientos guardados: {stats['movements']}")
                if (first,second,one["id"],two["id"],changed,denied,stats["units"],stats["movements"])!=(201,200,2,2,409,409,14,2):
                    raise SystemExit("La demostración no cumplió los criterios.")
            finally:
                server.terminate()
                server.wait(timeout=5)


if __name__ == "__main__":
    demo()
