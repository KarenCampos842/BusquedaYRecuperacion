import json,urllib.request
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"corpus"/"corpus_didactico.json"; docs=json.loads(p.read_text(encoding="utf-8"))
req=urllib.request.Request("http://localhost:8983/solr/ri/update?commit=true",data=json.dumps(docs).encode(),headers={"Content-Type":"application/json"},method="POST")
print(urllib.request.urlopen(req).read().decode()); print("Documentos:",len(docs))
