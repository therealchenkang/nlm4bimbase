from pyp3d import *

# 墙体开洞: 长6米墙，开1.5m×2m门洞 (Cube 角点语义)
L, T, H = 6000, 300, 3000
ww, wh = 1500, 2000     # 洞口宽, 高
wx = (L - ww) / 2       # 洞口 X 起点(居中)

wall = translate(0, 0, 0) * scale(L, T, H) * Cube()                  # X[0,L] Y[0,T] Z[0,H]
opening = translate(wx, -10, 0) * scale(ww, T + 20, wh) * Cube()     # 穿透墙厚

result = wall - opening
create_geometry(result)
