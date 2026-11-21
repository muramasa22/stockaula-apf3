"""Ejecuta el mismo control en una estación Git y en GitHub Actions."""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--event",default="manual")
args=parser.parse_args()
os.chdir(ROOT)
commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
now=dt.datetime.now(dt.timezone.utc)
run_id=now.strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6]
dest=ROOT/"runs"/run_id
dest.mkdir(parents=True)
steps=[
    ("sintaxis-python",[sys.executable,"-m","py_compile","app.py"],{}),
    ("sintaxis-interfaz",["node","--check","static/app.js"],{}),
    ("construccion-worker",["node","scripts/build.mjs"],{}),
    ("sintaxis-worker",["node","--check","dist/server/index.js"],{}),
    ("contrato-python",[sys.executable,"-m","unittest","discover","-s","tests","-v"],{"STOCKAULA_RUNTIME":"python"}),
    ("contrato-worker",[sys.executable,"-m","unittest","discover","-s","tests","-v"],{"STOCKAULA_RUNTIME":"worker"})
]
summary={"run_id":run_id,"commit":commit,"event":args.event,"started_utc":now.isoformat(),"steps":[]}
print("CI",run_id,commit[:12],"evento",args.event,flush=True)
for name,command,extra in steps:
    result=subprocess.run(command,capture_output=True,text=True,env={**os.environ,**extra})
    log=result.stdout+result.stderr
    (dest/(name+".log")).write_text(log,encoding="utf-8")
    passed=result.returncode==0
    summary["steps"].append({"name":name,"exit_code":result.returncode})
    count=next((line.strip() for line in log.splitlines() if line.startswith("Ran ")), "")
    print(("OK   " if passed else "FALLO"),name,count,flush=True)
    if not passed: print(log[-1800:],flush=True)
    if not passed and name not in ("contrato-python","contrato-worker"): break
summary["status"]="success" if len(summary["steps"])==len(steps) and all(s["exit_code"]==0 for s in summary["steps"]) else "failure"
if summary["status"]=="success":
    summary["worker_sha256"]=hashlib.sha256((ROOT/"dist/server/index.js").read_bytes()).hexdigest()
summary["finished_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
(dest/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print("RESULTADO",summary["status"],"·",dest.relative_to(ROOT),flush=True)
sys.exit(0 if summary["status"]=="success" else 1)
