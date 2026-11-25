import json,urllib.parse,urllib.request
from sentence_transformers import SentenceTransformer
qtxt=input("Consulta semántica: "); m=SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2");v=m.encode([qtxt],normalize_embeddings=True)[0]; vec="["+",".join(str(float(x)) for x in v)+"]"; q="{!knn f=vector topK=5}"+vec
p=urllib.parse.urlencode({"q":q,"fl":"id,titulo,score","rows":5,"wt":"json"}); data=json.load(urllib.request.urlopen("http://localhost:8983/solr/ri/select?"+p));[print(d) for d in data["response"]["docs"]]
