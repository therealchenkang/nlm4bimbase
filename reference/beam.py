from pyp3d import *

# 梁: 跨度6米, 宽300mm, 高500mm, 顶标高 Z+H (即底面在 Z)
# Cube 角点语义: 覆盖 X[0,L] Y[0,W] Z[Z, Z+H]
L, W, H, Z = 6000, 300, 500, 3000

beam = translate(0, 0, Z) * scale(L, W, H) * Cube()
create_geometry(beam)
