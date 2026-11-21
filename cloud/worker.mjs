/* El constructor incorpora SQL, LIMIT y ASSETS antes de este módulo. */
const version = "0.3.0-rc.1";
class Problem extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
function field(value, max) {
  if (typeof value !== "string" || !value.trim() || Array.from(value.trim()).length > max)
    throw new Problem(400, "Completa los campos de texto dentro del límite.");
  return value.trim();
}
function integer(value, min) {
  if (!Number.isInteger(value) || value < min || value > LIMIT.maxNumber)
    throw new Problem(400, "La cantidad o el mínimo deben ser enteros dentro del rango.");
  return value;
}
function codeOf(value) {
  const code = field(value, LIMIT.maxCode).toUpperCase();
  if (!/^[A-Z0-9][A-Z0-9._-]*$/.test(code))
    throw new Problem(400, "Usa letras, dígitos, puntos, guiones o guiones bajos en el código.");
  return code;
}
function json(data, status = 200) {
  return Response.json(data,{status,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
}
async function registerProduct(db, data) {
  const code = codeOf(data.code);
  const name = field(data.name, LIMIT.maxName), category = field(data.category, LIMIT.maxCategory);
  const minimum = integer(data.minimum, 0);
  const row = await db.prepare(SQL.addProduct).bind(code,name,category,minimum).first();
  if (!row) throw new Problem(409,"El código ya está registrado.");
  return json({code},201);
}
async function registerMovement(db, data) {
  const code = codeOf(data.code), kind = data.kind;
  if (!["entrada","salida"].includes(kind)) throw new Problem(400,"Selecciona entrada o salida.");
  const quantity = integer(data.quantity,1), reason = field(data.reason,LIMIT.maxReason);
  const key = data.request_key ?? null;
  if (Object.hasOwn(data,"request_key") && (typeof key !== "string" || !/^[A-Za-z0-9_-]{8,100}$/.test(key)))
    throw new Problem(400,"La clave de operación no es válida.");
  const row = await db.prepare(SQL.addMovement).bind(kind,quantity,reason,key,code,kind,quantity).first();
  if (row) return json({id:row.id,replayed:false},201);
  const previous = key ? await db.prepare(SQL.byRequestKey).bind(key).first() : null;
  if (previous) {
    if (previous.code !== code || previous.kind !== kind || previous.quantity !== quantity || previous.reason !== reason)
      throw new Problem(409,"La clave ya identifica otro movimiento.");
    return json({id:previous.id,replayed:true},200);
  }
  if (!await db.prepare(SQL.getProduct).bind(code).first()) throw new Problem(404,"No se encontró el material.");
  throw new Problem(409,"Stock insuficiente para esta salida.");
}
export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url), path = url.pathname, db = env.DB;
      if (request.method === "GET") {
        if (Object.hasOwn(ASSETS,path)) {
          const [type,body] = ASSETS[path];
          return new Response(body,{headers:{"Content-Type":type+"; charset=utf-8","Cache-Control":"no-cache","X-Content-Type-Options":"nosniff"}});
        }
        if (path === "/api/health") {
          await db.prepare(SQL.statistics).first();
          return json({service:"StockAula",version,storage:"D1"});
        }
        if (path === "/api/state") {
          const [products,movements,stats] = await db.batch([SQL.catalog,SQL.recent,SQL.statistics].map(q=>db.prepare(q)));
          return json({products:products.results,movements:movements.results,stats:stats.results[0]});
        }
      }
      if (request.method === "POST" && ["/api/products","/api/movements"].includes(path)) {
        const origin = request.headers.get("Origin");
        if (origin && origin !== url.origin) throw new Problem(403,"Origen de escritura no permitido.");
        if ((request.headers.get("Content-Type") || "").split(";")[0].trim() !== "application/json")
          throw new Problem(415,"Envía datos JSON.");
        const body = await request.text();
        if (body.length > 8192) throw new Problem(400,"El cuerpo de la solicitud no es válido.");
        let data;
        try { data = JSON.parse(body); } catch { throw new Problem(400,"JSON inválido."); }
        if (!data || typeof data !== "object" || Array.isArray(data)) throw new Problem(400,"Se esperaba un objeto JSON.");
        return await (path === "/api/products" ? registerProduct(db,data) : registerMovement(db,data));
      }
      return json({error:"Ruta no disponible."},404);
    } catch (err) {
      if (err instanceof Problem) return json({error:err.message},err.status);
      console.error("Error del almacén", err.message);
      return json({error:"El almacén no está disponible. Vuelve a intentarlo."},503);
    }
  }
};
