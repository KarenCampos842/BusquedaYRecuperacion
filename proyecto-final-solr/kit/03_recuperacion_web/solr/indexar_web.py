import json,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;docs=json.loads((H.parent/"crawler"/"documentos_web.json").read_text(encoding="utf-8"));p=H.parent/"pagerank"/"pagerank.json"
if p.exists():
 pr=json.loads(p.read_text());
 for d in docs:d["pagerank"]=pr.get(d["url"],0)
req=urllib.request.Request("http://localhost:8983/solr/ri/update?commit=true",data=json.dumps(docs).encode(),headers={"Content-Type":"application/json"},method="POST");print(urllib.request.urlopen(req).read().decode())
