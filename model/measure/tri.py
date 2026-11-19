import numpy as np, json
from geo import *
b=json.load(open('ba.json')); p=np.array(b['p']); c2=cam_from(p[0:7]); c3=cam_from(p[7:14]); q=dict(zip(b['names'],p))
F = {
 'presser_cap_top':((669,716),(129,789)), 'rod_top':((783,683),(448,713)), 'rod_base':((783,745),(461,840)),
 'upper_disc':((763.6,779),(213,1010)), 'tension_nut':((763.6,884),(224,1214.6)), 'J_hook':((788,818),(337.4,1070.3)),
 'K_tip':((869.4,794.7),(546,1050.6)), 'winder_spindle_top':((867,711),(568,822)), 'winder_tension_top':((958.5,686),(918,772)),
 'black_cap':((1013,711),(1055,868)), 'panel_nose':((945.5,757.3),(546,1040)), 'panel_TR':((1137.5,722),(1305,983)),
 'panel_BR':((1141.8,789),(1290,1143)), 'panel_BL':((990.5,811),(770,1150)), 'P_btn':((1124.4,740.4),(1282,1022)),
 'Reset_btn':((1120.5,766.7),(1268,1096)), 'plus_btn':((1102,742),(1172,1018)), 'minus_btn':((1106,768.8),(1160,1093)),
 'oil_window':((1062,941.5),(1057,1366)), 'sticker_QR':((1121.5,815.5),(1242,1201)), 'A7_A_botleft':((1022,844.5),(954.5,1205.5)),
 'motor_QR':((1159,883.8),(1345.7,1304.7)), 'usb':((1159.5,917),(1350,1358)), 'rubber_R':((1122,962),(1188,1455)),
 'np_D_right':((733.6,1010),(308,1304)), 'round_plate':((750.5,1006),(333,1339)), 'np_screw_front':((717,1015.5),(236,1358)),
 'np_screw_back':((702.7,1005),(259,1276.5)), 'slide_hole':((638,1022),(102,1321)), 'head_TR':((1139,710.7),(1320,962)),
 'spool_plate_L':((824,504),(975,190)), 'spool_plate_R':((942,501),(1262,188)),
}
out={}
print(f"{'feature':22s}   x(table)  y(up)   z     rms px")
for k,(a2,a3) in F.items():
    X,e=triangulate([(c2,a2),(c3,a3)]); out[k]=list(X)
    print(f"{k:22s} {X[0]:8.1f} {X[1]:7.1f} {X[2]:7.1f}   {e:5.1f}")
json.dump(out,open('tri.json','w'),indent=1)
print('bed FL corner (virtual)', round(q['xb'],2), round(q['zb'],2))
