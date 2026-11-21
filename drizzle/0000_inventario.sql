CREATE TABLE products (
  code TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  minimum INTEGER NOT NULL CHECK (minimum >= 0)
);
--> statement-breakpoint
CREATE TABLE movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL REFERENCES products(code),
  kind TEXT NOT NULL CHECK (kind IN ('entrada','salida')),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
--> statement-breakpoint
CREATE INDEX movements_code ON movements(code);
--> statement-breakpoint
CREATE VIEW inventory AS
SELECT p.code, p.name, p.category, p.minimum,
       COALESCE(SUM(CASE WHEN m.kind = 'entrada' THEN m.quantity ELSE -m.quantity END), 0) AS stock
FROM products AS p LEFT JOIN movements AS m ON p.code = m.code
GROUP BY p.code, p.name, p.category, p.minimum;
