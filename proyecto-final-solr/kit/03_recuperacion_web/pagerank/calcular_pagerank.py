import json
from pathlib import Path
H=Path(__file__).resolve().parent;E=json.loads((H.parent/"crawler"/"enlaces.json").read_text());N=sorted(set(x for e in E for x in e));O={n:[] for n in N}
for a,b in E:O[a].append(b)
d=.85;pr={n:1/len(N) for n in N}
for _ in range(50):
 new={n:(1-d)/len(N) for n in N};dang=sum(pr[n] for n in N if not O[n])
 for n in N:new[n]+=d*dang/len(N)
 for a in N:
  if O[a]:
   for b in O[a]:new[b]+=d*pr[a]/len(O[a])
 pr=new
for n,s in sorted(pr.items(),key=lambda x:x[1],reverse=True):print(f"{s:.6f}",n)
(H/"pagerank.json").write_text(json.dumps(pr,indent=2))
