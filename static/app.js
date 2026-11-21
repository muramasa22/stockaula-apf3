"use strict";
const byId = id => document.getElementById(id);
const productForm = byId("product-form"), movementForm = byId("movement-form");
let inventory = {products:[],movements:[],stats:{}};
let pending = null;
const formatter = new Intl.DateTimeFormat("es-PE",{dateStyle:"short",timeStyle:"short",timeZone:"America/Lima"});
function element(tag,text,className) {
  const item = document.createElement(tag); item.textContent = text;
  if (className) item.className = className;
  return item;
}
function notify(message,bad=false) {
  const box=byId("notice"); box.textContent=message; box.hidden=false; box.classList.toggle("bad",bad);
}
async function api(path, options) {
  const response = await fetch(path,options);
  let value;
  try { value=await response.json(); } catch { throw new Error("No se pudo leer la respuesta. Verifica tu conexión."); }
  if (!response.ok) throw new Error(value.error || "La operación no pudo completarse.");
  return value;
}
function paintCatalog() {
  const query=byId("search").value.toLocaleLowerCase().trim(), low=byId("only-low").checked;
  const rows=inventory.products.filter(p=>(!low || p.stock<=p.minimum) && (p.code+" "+p.name).toLocaleLowerCase().includes(query));
  const body=byId("materials"); body.replaceChildren();
  for (const p of rows) {
    const row=document.createElement("tr"), status=document.createElement("td"), alert=p.stock<=p.minimum;
    status.append(element("span",alert?"Por reponer":"Disponible",alert?"pill low":"pill"));
    row.append(element("td",p.code,"code"),element("td",p.name),element("td",p.category),element("td",p.stock,"num"),element("td",p.minimum,"num"),status);
    body.append(row);
  }
  const empty=byId("catalog-empty"); empty.hidden=rows.length>0;
  empty.querySelector("h2").textContent=inventory.products.length ? "Sin coincidencias" : "Aún no hay materiales";
  empty.querySelector("p").textContent=inventory.products.length ? "Cambia la búsqueda o el filtro de reposición." : "Registra el primer material para empezar a controlar sus existencias.";
}
async function refresh() {
  inventory=await api("/api/state");
  for (const [key,n] of Object.entries(inventory.stats)) byId("stat-"+key).textContent=n;
  paintCatalog();
  const history=byId("movement-list"); history.replaceChildren(); byId("history-empty").hidden=inventory.movements.length>0;
  for (const m of inventory.movements) {
    const row=document.createElement("tr");
    row.append(element("td",formatter.format(new Date(m.created_at))),element("td",m.name),element("td",m.kind==="entrada"?"Entrada":"Salida"),element("td",m.quantity,"num"),element("td",m.reason)); history.append(row);
  }
}
for (const b of document.querySelectorAll("[data-view]")) b.onclick=()=>{
  for (const tab of document.querySelectorAll("[data-view]")) {
    const active=tab===b; tab.setAttribute("aria-pressed",String(active)); byId(tab.dataset.view).hidden=!active;
  }
};
byId("search").oninput=paintCatalog; byId("only-low").onchange=paintCatalog;
byId("new-product").onclick=()=>{productForm.reset();productForm.querySelector(".form-error").hidden=true;byId("product-dialog").showModal();};
byId("new-movement").onclick=()=>{
  if(!inventory.products.length) {notify("Primero registra un material en el catálogo.",true);return;}
  const select=movementForm.elements.code; select.replaceChildren();
  for(const p of inventory.products) select.add(new Option(p.code+" · "+p.name+" ("+p.stock+" u.)",p.code));
  movementForm.reset();movementForm.querySelector(".form-error").hidden=true;byId("movement-dialog").showModal();
};
for(const b of document.querySelectorAll("[data-close]")) b.onclick=()=>b.closest("dialog").close();
for(const form of [productForm,movementForm]) form.onsubmit=async event=>{
  event.preventDefault(); const button=form.querySelector("[type=submit]"); if(button.disabled)return;
  const error=form.querySelector(".form-error"); error.hidden=true;
  const data=Object.fromEntries(new FormData(form)), movement=form===movementForm;
  if(movement) {
    data.quantity=Number(data.quantity);
    const signature=JSON.stringify(data);
    if(!pending || pending.signature!==signature) pending={signature,key:crypto.randomUUID()};
    data.request_key=pending.key;
  } else data.minimum=Number(data.minimum);
  button.disabled=true;
  try {
    const reply=await api(movement?"/api/movements":"/api/products",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    if(movement) pending=null;
    form.closest("dialog").close();
    notify(movement ? (reply.replayed?"Movimiento ya registrado.":"Movimiento registrado.") : "Material registrado.");
    try {await refresh();} catch {notify("Se guardó la operación. Recarga la página para actualizar los indicadores.",true);}
  } catch(e) {error.textContent=e.message;error.hidden=false;} finally {button.disabled=false;}
};
refresh().catch(e=>notify(e.message,true));
