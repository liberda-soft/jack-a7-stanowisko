import sys
from PIL import Image, ImageChops
I='/private/tmp/claude-501/-Users-kacperliberda-Documents-caataalog-ctlg/f713d02d-b838-4da4-904d-1349f46f4a50/images/'
R='../blend/out/'
for ph,cam,box in (('3','c3',(0,330,750,750)),('2','c2',(250,60,750,640))):
    photo=Image.open(I+ph+'.jpg').convert('RGBA').resize((750,1000))
    ren=Image.open(R+f'render_{cam}.png').convert('RGBA')
    a=ren.split()[3].point(lambda v: int(v*.55))
    ren.putalpha(a); comp=Image.alpha_composite(photo,ren)
    comp.crop(box).resize((int((box[2]-box[0])*1.4),int((box[3]-box[1])*1.4))).save(f'ov_{ph}.png')
    # edge overlay: render edges in red over photo
    e=Image.open(R+f'render_{cam}.png').convert('L').filter(__import__('PIL.ImageFilter',fromlist=['x']).FIND_EDGES).point(lambda v:255 if v>40 else 0)
    red=Image.new('RGBA',photo.size,(255,0,40,255)); red.putalpha(e)
    Image.alpha_composite(photo,red).crop(box).resize((int((box[2]-box[0])*1.4),int((box[3]-box[1])*1.4))).save(f'ed_{ph}.png')
print('ok')
