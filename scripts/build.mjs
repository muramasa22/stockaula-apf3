import {readFile,mkdir,writeFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";
process.chdir(fileURLToPath(new URL("..",import.meta.url)));
const read = p => readFile(p,"utf8");
const assets = {};
for (const [path,file,type] of [["/","index.html","text/html"],["/style.css","style.css","text/css"],["/app.js","app.js","text/javascript"]]) {
  assets[path] = [type, await read("static/"+file)];
}
const settings = {SQL:JSON.parse(await read("model/sql.json")),LIMIT:JSON.parse(await read("model/fields.json")),ASSETS:assets};
const definitions = Object.entries(settings).map(([name,value]) => "const "+name+" = "+JSON.stringify(value)+";").join("\n");
await mkdir("dist/server",{recursive:true});
await mkdir("dist/.openai",{recursive:true});
await writeFile("dist/server/index.js",definitions+"\n"+await read("cloud/worker.mjs"));
await writeFile("dist/.openai/hosting.json",await read(".openai/hosting.json"));
console.log("Worker compilado con HTML, CSS, JavaScript y consultas compartidas.");
