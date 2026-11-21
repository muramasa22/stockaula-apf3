/* Adaptador de pruebas para el Worker compilado; usa SQLite de Node en un puerto local. */
import {createServer} from "node:http";
import {DatabaseSync} from "node:sqlite";
import {readFileSync,readdirSync} from "node:fs";
import worker from "../dist/server/index.js";
const conn = new DatabaseSync(":memory:");
conn.exec("PRAGMA foreign_keys=ON");
for (const f of readdirSync("drizzle").filter(f=>f.endsWith(".sql")).sort()) conn.exec(readFileSync("drizzle/"+f,"utf8"));
class Statement {
  constructor(sql,args=[]) {this.sql=sql;this.args=args;}
  bind(...args) {return new Statement(this.sql,args);}
  async first() {return conn.prepare(this.sql).get(...this.args)??null;}
  async all() {return {results:conn.prepare(this.sql).all(...this.args)};}
}
const DB={
  prepare:sql=>new Statement(sql),
  async batch(statements) {
    conn.exec("BEGIN");
    try {
      const rows=statements.map(s=>({results:conn.prepare(s.sql).all(...s.args)}));
      conn.exec("COMMIT"); return rows;
    } catch(e) {conn.exec("ROLLBACK");throw e;}
  }
};
const portIndex=process.argv.indexOf("--port");
const port=portIndex<0?8000:Number(process.argv[portIndex+1]);
const server=createServer(async(req,res)=>{
  try {
    const chunks=[];for await(const chunk of req)chunks.push(chunk);
    const body=Buffer.concat(chunks);
    const request=new Request("http://"+req.headers.host+req.url,{method:req.method,headers:req.headers,body:body.length?body:undefined});
    const result=await worker.fetch(request,{DB});
    res.writeHead(result.status,Object.fromEntries(result.headers));res.end(Buffer.from(await result.arrayBuffer()));
  } catch(e) {res.writeHead(500);res.end(String(e));}
});
server.listen(port,"127.0.0.1",()=>console.log("StockAula en http://127.0.0.1:"+server.address().port));
