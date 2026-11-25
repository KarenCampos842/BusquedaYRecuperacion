import json,urllib.request,urllib.error
BASE="http://localhost:8983/solr/ri"
def post(payload):
 req=urllib.request.Request(BASE+"/schema",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
 try: return urllib.request.urlopen(req).read()
 except urllib.error.HTTPError as e:
  body=e.read().decode()
  if "already exists" in body.lower() or "duplicate" in body.lower(): return
  raise RuntimeError(body)
post({"add-field-type":{"name":"text_es_ri","class":"solr.TextField","positionIncrementGap":"100","indexAnalyzer":{"tokenizer":{"class":"solr.StandardTokenizerFactory"},"filters":[{"class":"solr.LowerCaseFilterFactory"},{"class":"solr.ASCIIFoldingFilterFactory","preserveOriginal":"true"}]},"queryAnalyzer":{"tokenizer":{"class":"solr.StandardTokenizerFactory"},"filters":[{"class":"solr.LowerCaseFilterFactory"},{"class":"solr.ASCIIFoldingFilterFactory","preserveOriginal":"true"}]}}})
for f in [{"name":"titulo","type":"text_es_ri","stored":True,"indexed":True},{"name":"contenido","type":"text_es_ri","stored":True,"indexed":True},{"name":"categoria","type":"string","stored":True,"indexed":True},{"name":"tema","type":"string","stored":True,"indexed":True}]: post({"add-field":f})
post({"add-field-type":{"name":"vector_384_cosine","class":"solr.DenseVectorField","vectorDimension":384,"similarityFunction":"cosine"}})
post({"add-field":{"name":"vector","type":"vector_384_cosine","indexed":True,"stored":True}})
print("Esquema configurado.")
