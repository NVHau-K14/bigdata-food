import pandas as pd, numpy as np, glob, sys
SP=sys.argv[1]
r=pd.read_parquet(glob.glob(SP+"/clean/ratings_clean.parquet/*.parquet")[0])
f=pd.read_parquet(glob.glob(SP+"/clean/foods_clean.parquet/*.parquet")[0])
n=len(r); nu=r.user_id.nunique(); nf=r.food_id.nunique()
print("rows",n,"users",nu,"foods_rated",nf,"foods_catalog",len(f),"has_ratings all true:",bool(f.has_ratings.all()))
print("sparsity %.4f"%((1-n/(nu*nf))*100))
print("mean %.4f std(pop) %.4f"%(r.rating.mean(), r.rating.std(ddof=0)))
vc=r.rating.value_counts().sort_index()
for k,v in vc.items(): print("level",k,v,"%.2f"%(v/n*100))
pu=r.groupby("user_id").size(); pf=r.groupby("food_id").size()
q=[0,.25,.5,.75,.9,.99,1]
print("per_user",[float(x) for x in pu.quantile(q)],"mean %.1f"%pu.mean())
print("per_food",[float(x) for x in pf.quantile(q)],"mean %.2f"%pf.mean())
print("median per user",pu.median(),"median per food",pf.median())
print("min share %.2f max share %.2f"%(vc.min()/n*100, vc.max()/n*100))
