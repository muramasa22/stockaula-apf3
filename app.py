"""StockAula. Servidor local de demostración con Python y SQLite."""
import argparse
import json
import re
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SQL = json.loads((ROOT / "model/sql.json").read_text(encoding="utf-8"))
LIMIT = json.loads((ROOT / "model/fields.json").read_text(encoding="utf-8"))
VERSION = "0.3.0-rc.1"
ASSETS = {"/": ("index.html", "text/html"), "/style.css": ("style.css", "text/css"),
          "/app.js": ("app.js", "text/javascript")}


class RequestError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def text_field(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise RequestError(400, "Completa los campos de texto dentro del límite.")
    return value.strip()


def number(value, minimum):
    if type(value) not in (float, int) or not minimum <= value <= LIMIT["maxNumber"] or int(value) != value:
        raise RequestError(400, "La cantidad o el mínimo deben ser enteros dentro del rango.")
    return int(value)


def product_code(value):
    code = text_field(value, LIMIT["maxCode"]).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]*", code):
        raise RequestError(400, "Usa letras, dígitos, puntos, guiones o guiones bajos en el código.")
    return code


def connect(path):
    db = sqlite3.connect(path, isolation_level=None, timeout=8)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialize(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
        for migration in sorted((ROOT / "drizzle").glob("*.sql")):
            if db.execute("SELECT 1 FROM schema_migrations WHERE name=?", (migration.name,)).fetchone():
                continue
            for statement in migration.read_text(encoding="utf-8").split("--> statement-breakpoint"):
                if statement.strip():
                    db.execute(statement.strip())
            db.execute("INSERT INTO schema_migrations VALUES (?)", (migration.name,))
        db.commit()


def state(db):
    db.execute("BEGIN")
    try:
        return {"products": [dict(r) for r in db.execute(SQL["catalog"])],
                "movements": [dict(r) for r in db.execute(SQL["recent"])],
                "stats": dict(db.execute(SQL["statistics"]).fetchone())}
    finally:
        db.commit()


def add_product(db, data):
    code = product_code(data.get("code"))
    name = text_field(data.get("name"), LIMIT["maxName"])
    category = text_field(data.get("category"), LIMIT["maxCategory"])
    minimum = number(data.get("minimum"), 0)
    if not db.execute(SQL["addProduct"], (code, name, category, minimum)).fetchone():
        raise RequestError(409, "El código ya está registrado.")
    return 201, {"code": code}


def add_movement(db, data):
    code = product_code(data.get("code"))
    kind = data.get("kind")
    if kind not in ("entrada", "salida"):
        raise RequestError(400, "Selecciona entrada o salida.")
    quantity = number(data.get("quantity"), 1)
    reason = text_field(data.get("reason"), LIMIT["maxReason"])
    key = data.get("request_key")
    if "request_key" in data and (not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", key)):
        raise RequestError(400, "La clave de operación no es válida.")
    row = db.execute(SQL["addMovement"], (kind, quantity, reason, key, code, kind, quantity)).fetchone()
    if row:
        return 201, {"id": row["id"], "replayed": False}
    previous = db.execute(SQL["byRequestKey"], (key,)).fetchone() if key else None
    if previous:
        if (previous["code"], previous["kind"], previous["quantity"], previous["reason"]) != (code, kind, quantity, reason):
            raise RequestError(409, "La clave ya identifica otro movimiento.")
        return 200, {"id": previous["id"], "replayed": True}
    if not db.execute(SQL["getProduct"], (code,)).fetchone():
        raise RequestError(404, "No se encontró el material.")
    raise RequestError(409, "Stock insuficiente para esta salida.")


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            with closing(connect(self.server.database)) as db:
                db.execute(SQL["statistics"]).fetchone()
            self.reply(200, {"service": "StockAula", "version": VERSION, "storage": "SQLite"})
        elif path == "/api/state":
            with closing(connect(self.server.database)) as db:
                self.reply(200, state(db))
        elif path in ASSETS:
            filename, kind = ASSETS[path]
            self.reply(200, (ROOT / "static" / filename).read_bytes(), kind)
        else:
            self.reply(404, {"error": "Ruta no disponible."})

    def do_POST(self):
        try:
            action = {"/api/products": add_product, "/api/movements": add_movement}.get(urlsplit(self.path).path)
            if action is None:
                raise RequestError(404, "Ruta no disponible.")
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                raise RequestError(403, "Origen de escritura no permitido.")
            if self.headers.get_content_type() != "application/json":
                raise RequestError(415, "Envía datos JSON.")
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 8192:
                raise RequestError(400, "El cuerpo de la solicitud no es válido.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise RequestError(400, "Se esperaba un objeto JSON.")
            with closing(connect(self.server.database)) as db:
                status, result = action(db, data)
            self.reply(status, result)
        except (ValueError, UnicodeError):
            self.reply(400, {"error": "JSON inválido."})
        except RequestError as exc:
            self.reply(exc.status, {"error": str(exc)})
        except sqlite3.Error:
            self.reply(503, {"error": "El almacén no está disponible. Vuelve a intentarlo."})


def serve(port, database, host="127.0.0.1"):
    initialize(database)
    server = ThreadingHTTPServer((host, port), Handler)
    server.database = database
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", type=Path, default=ROOT / "data/stockaula-apf3.sqlite3")
    args = parser.parse_args()
    server = serve(args.port, args.db)
    print(f"StockAula en http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
