from pyp3d import *

# 墙体: 长6米, 厚300mm, 高3米
# ★ Cube() 是角点语义: translate 给最小角点，scale 给尺寸
# 本墙覆盖 X[0,L] Y[0,T] Z[0,H]，立于地面
L, T, H = 6000, 300, 3000

wall = translate(0, 0, 0) * scale(L, T, H) * Cube()
create_geometry(wall)
