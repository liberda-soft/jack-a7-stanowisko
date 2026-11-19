import numpy as np, json, cv2
from PIL import Image, ImageDraw, ImageFont
from geo import *
I='/private/tmp/claude-501/-Users-kacperliberda-Documents-caataalog-ctlg/f713d02d-b838-4da4-904d-1349f46f4a50/images/'
OUT='../blend/tex/'
b=json.load(open('ba.json')); p=np.array(b['p'])
cams={'c2':{'f':p[0],'r':list(p[1:4]),'t':list(p[4:7])},'c3':{'f':p[7],'r':list(p[8:11]),'t':list(p[11:14])}}
# --- logo alpha from rectified arm front (x 41.5..72, y 23..9.5 @40px/cm)
a=cv2.imread(OUT+'armfront.png'); hsv=cv2.cvtColor(a,cv2.COLOR_BGR2HSV)
x0,x1,y0,y1=52.2,60.7,15.9,18.4
c0,c1=int((x0-41.5)*40),int((x1-41.5)*40); r0,r1=int((23-y1)*40),int((23-y0)*40)
roi=hsv[r0:r1,c0:c1]; m=((roi[:,:,0]>85)&(roi[:,:,0]<110)&(roi[:,:,1]>90)).astype(np.uint8)*255
m=cv2.resize(m,(m.shape[1]*4,m.shape[0]*4),interpolation=cv2.INTER_CUBIC); m=cv2.GaussianBlur(m,(5,5),0); m=((m>110)*255).astype(np.uint8)
rgba=np.zeros((m.shape[0],m.shape[1],4),np.uint8); rgba[:,:,0]=18; rgba[:,:,1]=163; rgba[:,:,2]=216; rgba[:,:,3]=m
Image.fromarray(rgba).save(OUT+'logo.png'); print('logo',m.shape,(x0,x1,y0,y1))
# --- ruler (front face 104.1 x 4 cm), ticks from x=2.0
W_,H_=8192,315; s=W_/104.1
im=Image.new('RGB',(W_,H_),(206,140,86)); d=ImageDraw.Draw(im)
rng=np.random.default_rng(3)
for i in range(260):
    y=rng.uniform(0,H_); col=(int(rng.uniform(170,200)),int(rng.uniform(108,128)),int(rng.uniform(62,78)))
    d.line([(0,y),(W_,y+rng.uniform(-6,6))],fill=col,width=int(rng.uniform(1,4)))
try: f=ImageFont.truetype('/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf',58)
except Exception: f=ImageFont.load_default()
for mm in range(0,1001):
    x=(2.0+mm/10)*s
    if mm%10: continue
    cm=mm//10; L=0.55 if cm%10==0 else (0.45 if cm%5==0 else 0.3)
    w=10 if cm%10==0 else (7 if cm%5==0 else 4)
    d.rectangle([x-w/2,H_*(0.92-L),x+w/2,H_*0.92],fill=(28,18,10))
    if cm%5==0:
        t=str(cm); tw=d.textlength(t,font=f); d.text((x-tw/2,H_*0.06),t,fill=(28,18,10),font=f)
im.save(OUT+'ruler.jpg',quality=90)
# --- photo crops for camera-projection mapping (photo 3)
img3=cv2.imread(I+'3.jpg')
crops={'panelproj':(500,930,1340,1200),'pillarproj':(800,1150,1330,1420)}
for k,(u0,v0,u1,v1) in crops.items(): cv2.imwrite(OUT+k+'.jpg',img3[v0:v1,u0:u1],[cv2.IMWRITE_JPEG_QUALITY,93])
json.dump({'cams':cams,'crops':crops,'W':1500,'H':2000},open('../blend/calib.json','w'),indent=1)
print('ok')
