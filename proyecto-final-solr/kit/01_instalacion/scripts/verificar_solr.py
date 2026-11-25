import json,urllib.request
url="http://localhost:8983/solr/admin/cores?action=STATUS&core=ri&wt=json"
try:
 data=json.load(urllib.request.urlopen(url,timeout=5)); print("OK: Solr y core ri disponibles." if "ri" in data.get("status",{}) else "Solr responde, pero falta core ri.")
except Exception as e: print("ERROR:",e)
