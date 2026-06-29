from pyp3d import *

# 楼板: 6米×3米, 厚120mm, 底面在标高 Z
# Cube 角点语义: 覆盖 X[0,L] Y[0,W] Z[Z, Z+T]
L, W, T, Z = 6000, 3000, 120, 3000

slab = translate(0, 0, Z) * scale(L, W, T) * Cube()
create_geometry(slab)
