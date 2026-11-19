"""Camera calibration from the table ruler + triangulation helpers.
World frame (cm): origin = table top, front-left corner of the laminate+edge outline.
x → right along the front edge, y → up, z → toward the operator (front edge at z=0, back at z=-D)."""
import numpy as np, cv2, json, sys

W, H = 1500, 2000

def rodrigues(r):
    R, _ = cv2.Rodrigues(np.asarray(r, float).reshape(3, 1)); return R

def project(P, cam):
    f, r, t = cam['f'], cam['r'], cam['t']
    R = rodrigues(r); Pc = (R @ np.asarray(P, float).T).T + t
    return np.stack([W/2 + f*Pc[:, 0]/Pc[:, 2], H/2 + f*Pc[:, 1]/Pc[:, 2]], 1), Pc[:, 2]

def lm(fun, x0, iters=200):
    x = np.asarray(x0, float); lam = 1e-3
    for _ in range(iters):
        r0 = fun(x); J = np.zeros((len(r0), len(x)))
        for i in range(len(x)):
            d = np.zeros_like(x); d[i] = 1e-6*max(1, abs(x[i])); J[:, i] = (fun(x+d)-r0)/d[i]
        A = J.T@J; g = J.T@r0
        while True:
            dx = -np.linalg.solve(A + lam*np.diag(np.diag(A)+1e-9), g)
            if (fun(x+dx)**2).sum() < (r0**2).sum(): x = x+dx; lam = max(lam/3, 1e-9); break
            lam *= 5
            if lam > 1e9: return x, r0
        if np.abs(dx).max() < 1e-8: break
    return x, fun(x)

def cam_from(x): return {'f': x[0], 'r': x[1:4], 't': x[4:7]}

def back_to_plane(uv, cam, n, d):
    """intersect pixel ray with plane n·X = d"""
    R = rodrigues(cam['r']); C = -R.T @ cam['t']
    ray = R.T @ np.array([(uv[0]-W/2)/cam['f'], (uv[1]-H/2)/cam['f'], 1.0])
    s = (d - n @ C)/(n @ ray); return C + s*ray

def triangulate(obs):
    """obs: list of (cam, (u,v)). Linear least squares on rays, then LM refine."""
    A = []; b = []
    for cam, uv in obs:
        R = rodrigues(cam['r']); C = -R.T @ cam['t']
        d = R.T @ np.array([(uv[0]-W/2)/cam['f'], (uv[1]-H/2)/cam['f'], 1.0]); d /= np.linalg.norm(d)
        Pm = np.eye(3) - np.outer(d, d); A.append(Pm); b.append(Pm @ C)
    X = np.linalg.solve(sum(A), sum(b))
    res = lambda X: np.concatenate([project(X[None], c)[0][0]-np.array(uv) for c, uv in obs])
    X, r = lm(res, X, 50)
    return X, float(np.sqrt((r**2).mean()))

def lookat(C, T, f):
    C=np.asarray(C,float); T=np.asarray(T,float)
    z=T-C; z/=np.linalg.norm(z)            # camera forward
    up=np.array([0,1.,0]); x=np.cross(z,up); x/=np.linalg.norm(x)   # image x to the right
    y=np.cross(z,x)                         # image y down
    R=np.stack([x,y,z]); r,_=cv2.Rodrigues(R); t=-R@C
    return np.concatenate([[f],r.ravel(),t])
