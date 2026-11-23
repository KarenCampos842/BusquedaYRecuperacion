import csv,json,urllib.parse,urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent; rel={}
for r in csv.DictReader(open(D/"juicios_relevancia.csv",encoding="utf-8")): rel.setdefault(r["query_id"],set()).add(r["doc_id"])
for q in csv.DictReader(open(D/"consultas.csv",encoding="utf-8")):
 p=urllib.parse.urlencode({"q":q["consulta"],"defType":"edismax","qf":"titulo^3 contenido","fl":"id,score","rows":10,"wt":"json"})
 got=[d["id"] for d in json.load(urllib.request.urlopen("http://localhost:8983/solr/ri/select?"+p))["response"]["docs"]]; R=rel[q["query_id"]]
 print(q["query_id"],"P@5=",round(sum(x in R for x in got[:5])/5,2),"Recall@10=",round(sum(x in R for x in got)/len(R),2),got)
