import numpy as np, json, sys
from geo import *
b=json.load(open('ba.json')); p=np.array(b['p']); C={'2':cam_from(p[0:7]),'3':cam_from(p[7:14])}
ZA=-15.7; ZP=-12.7
pts = [  # (label, photo, u, v, plane: ('z',val)|('y',val)|('x',val))
 ('arm top-front edge above J', '3',450,905,('z',ZA)), ('arm top-front edge (P2)', '2',800,752,('z',ZA)),
 ('stripe top @x300','3',300,967,('z',ZA)), ('stripe bottom @x300','3',300,995,('z',ZA)),
 ('stripe top @x60','3',60,962,('z',ZA)), ('stripe top @x540','3',540,980,('z',ZA)), ('stripe bot @x540','3',540,1000,('z',ZA)),
 ('arm front-bottom edge @x500','3',500,1104,('z',ZA)), ('arm front-bottom edge @x700','3',700,1106,('z',ZA)),
 ('needle head left edge @y1050','3',40,1050,('z',ZA)), ('needle head left edge @y1150','3',52,1150,('z',ZA)),
 ('needle head right side @y1150','3',340,1150,('z',ZA)), ('needle head bottom','3',130,1201,('z',ZA)),
 ('panel TL corner','3',800,962,('z',ZP)), ('panel nose','3',546,1040,('z',ZP)), ('panel BL','3',770,1150,('z',ZP)),
 ('panel TR','3',1305,983,('z',ZP)), ('panel BR','3',1290,1143,('z',ZP)),
 ('housing top-front edge @x1000','3',1000,953,('z',ZP)),
 ('pillar front-left edge @y1300','3',822,1300,('z',ZP)), ('pillar front-left edge @y1200','3',818,1200,('z',ZP)),
 ('pillar base-left','3',818,1392,('z',ZP)), ('pillar front-right edge @y1300','3',1312,1300,('z',ZP)),
 ('pillar left face back edge @y1300','3',742,1300,('x',None)),
 ('bed back edge seen in throat','3',500,1173,('y',0.3)),
 ('LCD left','3',858,1000,('z',ZP)),
]
res={}
for lab,ph,u,v,(ax,val) in pts:
    cam=C[ph]
    if ax=='x':
        val=res['pillar front-left edge @y1300'][0]
    n={'x':np.array([1.,0,0]),'y':np.array([0,1.,0]),'z':np.array([0,0,1.])}[ax]
    X=back_to_plane((u,v),cam,n,val); res[lab]=X
    print(f"{lab:36s} P{ph} ({u},{v}) -> x {X[0]:6.1f}  y {X[1]:6.1f}  z {X[2]:6.1f}")
json.dump({k:list(v) for k,v in res.items()},open('bp.json','w'),indent=1)
