from pyp3d import *

# 独立基础: 底面2400×2400mm, 高600mm, 顶面在 z=0 (覆盖 Z[-BH, 0])
# Cube 角点语义
BL, BW, BH = 2400, 2400, 600

foundation = translate(-BL/2, -BW/2, -BH) * scale(BL, BW, BH) * Cube()
create_geometry(foundation)
