import numpy as np, json, cv2
from geo import *
t2 = {0:(216,1240),5:(298,1222),10:(376,1203),15:(449,1186),20:(522,1169),50:(886,1082),55:(938,1069),60:(989,1058),65:(1040,1046),70:(1088,1036),75:(1133,1022),80:(1178,1015),85:(1220,1005),90:(1263,996),95:(1302,987),100:(1341,977)}
t3 = {45:(152,1767),50:(302,1766),55:(450,1762),60:(594,1757.5),65:(739,1752),70:(881.7,1745),75:(1023,1742),80:(1163,1739),85:(1302,1734.7),90:(1438,1728.5)}
# parameter vector layout
names = ['f2','r2a','r2b','r2c','t2a','t2b','t2c','f3','r3a','r3b','r3c','t3a','t3b','t3c','a','L','D','xb','zb','yt','s1','u1','u2','s2','u3','Rx','Ry','Rz']
def unpack(p): return dict(zip(names,p))
def residuals(p):
    q=unpack(p); c2=cam_from(p[0:7]); c3=cam_from(p[7:14])
    P2=[(q['a']+r,-q['yt'],0) for r in t2]+[(0,0,0),(q['L'],0,0),(0,0,-q['D']),(q['xb'],0,q['zb']),(q['xb'],0,q['zb']-q['s2']),(q['xb']+q['u3'],0,q['zb']),(q['Rx'],q['Ry'],q['Rz'])]
    U2=list(t2.values())+[(179.5,1226),(1359,965),(80,999),(666,1051.6),(585,1000),(1105,967),(1122,962)]
    P3=[(q['a']+r,-q['yt'],0) for r in t3]+[(q['xb'],0,q['zb']),(q['xb'],0,q['zb']-q['s1']),(q['xb']+q['u1'],0,q['zb']),(q['xb']+q['u2'],0,q['zb']),(q['Rx'],q['Ry'],q['Rz'])]
    U3=list(t3.values())+[(4,1489.5),(123,1209.5),(390,1489),(1148,1467),(1188,1455)]
    e2=(project(np.array(P2,float),c2)[0]-np.array(U2,float)).ravel()
    e3=(project(np.array(P3,float),c3)[0]-np.array(U3,float)).ravel()
    prior=[(q['D']-60)/30.0, (q['f2']-q['f3'])/50.0, (q['f2']-1480)/200.0]   # weak priors: table depth, same phone camera
    return np.concatenate([e2,e3,prior])

import itertools
c2=json.load(open('cam2.json')); a,xb,zb=c2['a'],c2['xb'],c2['zb']
best=None
for C3,T3 in itertools.product([(66,70,30),(66,85,20),(60,60,45)],[(66,5,-25),(66,15,-20)]):
  for f in [1400,1600]:
    p0=np.concatenate([[c2['f'],*c2['r'],*c2['t']], lookat(C3,T3,f), [a,c2['L'],58,xb,zb,1.2,10,15,45,10,40, xb+52,0.5,zb+0.5]])
    p,res=lm(residuals,p0,400); e=np.sqrt((res[:-3]**2).mean())
    q=unpack(p); C=-rodrigues(p[8:11]).T@p[11:14]
    print(C3,T3,f,'->',round(e,2),'f3',round(p[7]),'cam3',C.round(0))
    if C[2]>0 and (best is None or e<best[1]): best=(p,e,res)
p,e,res=best; q=unpack(p); e2=res[:-3].reshape(-1,2); err=np.hypot(e2[:,0],e2[:,1])
print('BEST rms',round(e,2)); print({k:round(float(v),2) for k,v in q.items() if not k.startswith(('r2','r3','t2','t3'))})
for k,cam in (('cam2',cam_from(p[0:7])),('cam3',cam_from(p[7:14]))):
    C=-rodrigues(cam['r']).T@cam['t']; print(k,'pos',C.round(1),'f',round(cam['f']))
print('err2',err[:23].round(1)); print('err3',err[23:].round(1))
json.dump({'p':list(p),'names':names},open('ba.json','w'))
