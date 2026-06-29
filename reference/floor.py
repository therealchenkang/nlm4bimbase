from pyp3d import *

# 地面板 L×W, 厚 T, 顶面在 z=0 (即覆盖 Z[-T, 0])
# Cube 角点语义
L, W, T = 8000, 6000, 100

floor = translate(0, 0, -T) * scale(L, W, T) * Cube()
floor = floor.color(0.60, 0.50, 0.40, 1)
create_geometry(floor)
