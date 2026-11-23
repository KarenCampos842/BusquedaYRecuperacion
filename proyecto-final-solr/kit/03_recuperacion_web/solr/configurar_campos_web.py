import json,urllib.request,urllib.error
B="http://localhost:8983/solr/ri/schema"
for f in [{"name":"url","type":"string","stored":True,"indexed":True},{"name":"titulo_web","type":"text_es_ri","stored":True,"indexed":True},{"name":"contenido_web","type":"text_es_ri","stored":True,"indexed":True},{"name":"profundidad","type":"pint","stored":True,"indexed":True},{"name":"enlaces_salientes","type":"strings","stored":True,"indexed":False,"multiValued":True},{"name":"pagerank","type":"pdouble","stored":True,"indexed":True}]:
 req=urllib.request.Request(B,data=json.dumps({"add-field":f}).encode(),headers={"Content-Type":"application/json"},method="POST")
 try:urllib.request.urlopen(req)
 except urllib.error.HTTPError as e:
  if "already exists" not in e.read().decode().lower():raise
print("Campos Web configurados")
