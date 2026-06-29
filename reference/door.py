from pyp3d import *

# 墙上开门洞 + 门扇 (Cube 角点语义)
# ★ 颜色必须在所有布尔运算之后再赋值
L, T, H = 6000, 240, 3000
door_w, door_h = 1200, 2100
door_x = (L - door_w) / 2     # 门洞 X 起点(居中)

# 墙体: X[0,L] Y[0,T] Z[0,H]
wall = translate(0, 0, 0) * scale(L, T, H) * Cube()

# 门洞(穿透墙厚)
opening = translate(door_x, -10, 0) * scale(door_w, T + 20, door_h) * Cube()
wall = wall - opening
wall = wall.color(0.90, 0.88, 0.82, 1)

# 门扇(略小于洞口，贴在墙一侧)
door_panel = translate(door_x + 20, T/2, 20) * scale(door_w - 40, T/2, door_h - 40) * Cube()
door_panel = door_panel.color(0.40, 0.25, 0.15, 1)

create_geometry(Combine(wall, door_panel))
