import numpy as np, json, cv2
from geo import *
I='/private/tmp/claude-501/-Users-kacperliberda-Documents-caataalog-ctlg/f713d02d-b838-4da4-904d-1349f46f4a50/images/'
OUT='../blend/tex/'
b=json.load(open('ba.json')); p=np.array(b['p']); c2=cam_from(p[0:7]); c3=cam_from(p[7:14])
img3=cv2.imread(I+'3.jpg'); img2=cv2.imread(I+'2.jpg')
def rectify(img,cam,x0,x1,y0,y1,z,ppcm=40,name='x'):
    w=int((x1-x0)*ppcm); h=int((y1-y0)*ppcm)
    xs=np.linspace(x0,x1,w); ys=np.linspace(y1,y0,h)
    X,Y=np.meshgrid(xs,ys); P=np.stack([X.ravel(),Y.ravel(),np.full(X.size,z)],1)
    uv,_=project(P,cam); mx=uv[:,0].reshape(h,w).astype(np.float32); my=uv[:,1].reshape(h,w).astype(np.float32)
    out=cv2.remap(img,mx,my,cv2.INTER_CUBIC); cv2.imwrite(OUT+name+'.png',out); print(name,out.shape)
rectify(img3,c3,59.8,88.2,14.6,23.2,-12.7,ppcm=48,name='panel')
rectify(img3,c3,72.0,90.0,3.6,13.9,-12.7,ppcm=48,name='sticker')
rectify(img3,c3,41.5,72.0,9.5,23.0,-15.7,ppcm=40,name='armfront')
rectify(img3,c3,89.6,97.8,0.0,24.0,-14.5,ppcm=40,name='motorfront')
