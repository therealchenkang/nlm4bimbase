from pyp3d import *

# 方柱: 截面400×400mm, 高3米 (Cube 角点语义，立于地面)
Cx, Cy, H = 400, 400, 3000
col = translate(-Cx/2, -Cy/2, 0) * scale(Cx, Cy, H) * Cube()
create_geometry(col)

# 圆柱: 半径300mm, 高4米 (Cone 用绝对坐标，不受 Cube 语义影响)
R, H2 = 300, 4000
col2 = Cone(GeVec3d(0, 0, 0), GeVec3d(0, 0, H2), R, R)
# create_geometry(col2)
