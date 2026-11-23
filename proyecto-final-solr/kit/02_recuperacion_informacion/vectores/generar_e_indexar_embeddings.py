import json,urllib.request
from pathlib import Path
from sentence_transformers import SentenceTransformer
D=Path(__file__).resolve().parents[1]; docs=json.loads((D/"corpus"/"corpus_didactico.json").read_text(encoding="utf-8")); model=SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
V=model.encode([d["titulo"]+". "+d["contenido"] for d in docs],normalize_embeddings=True)
for d,v in zip(docs,V): d["vector"]=[float(x) for x in v]
req=urllib.request.Request("http://localhost:8983/solr/ri/update?commit=true",data=json.dumps(docs).encode(),headers={"Content-Type":"application/json"},method="POST");print(urllib.request.urlopen(req).read().decode())
