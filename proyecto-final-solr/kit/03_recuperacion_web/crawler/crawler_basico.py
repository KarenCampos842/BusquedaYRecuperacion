from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse
from urllib.request import urlopen
from collections import deque
import json,sys
SEED=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8000/index.html"; MAX=int(sys.argv[2]) if len(sys.argv)>2 else 3; HOST=urlparse(SEED).netloc
class P(HTMLParser):
 def __init__(self): super().__init__();self.title="";self.text=[];self.links=[];self.intitle=False
 def handle_starttag(self,t,a):
  d=dict(a); self.intitle=t=="title" or self.intitle
  if t=="a" and d.get("href"): self.links.append(d["href"])
 def handle_endtag(self,t):
  if t=="title":self.intitle=False
 def handle_data(self,x):
  s=" ".join(x.split())
  if s:self.text.append(s);self.title+=s if self.intitle else ""
Q=deque([(SEED,0)]);seen=set();docs=[];edges=[]
while Q:
 u,dep=Q.popleft()
 if u in seen or dep>MAX:continue
 seen.add(u);p=P();p.feed(urlopen(u).read().decode())
 outs=[]
 for h in p.links:
  v=urljoin(u,h).split("#")[0]
  if urlparse(v).netloc==HOST:outs.append(v);edges.append((u,v));Q.append((v,dep+1))
 docs.append({"id":u,"url":u,"titulo_web":p.title,"contenido_web":" ".join(p.text),"profundidad":dep,"enlaces_salientes":outs})
open("documentos_web.json","w",encoding="utf-8").write(json.dumps(docs,ensure_ascii=False,indent=2));open("enlaces.json","w",encoding="utf-8").write(json.dumps(edges,indent=2));print("Páginas",len(docs),"enlaces",len(edges))
