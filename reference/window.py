from pyp3d import *

# 墙上开窗洞 + 玻璃(含窗台高度) (Cube 角点语义)
L, T, H = 6000, 240, 3000
win_w, win_h = 1500, 1200
sill_h = 900              # 窗台高(地面到窗洞底)
win_x = (L - win_w) / 2   # 窗洞 X 起点(居中)

# 墙体开窗洞
wall = translate(0, 0, 0) * scale(L, T, H) * Cube()
opening = translate(win_x, -10, sill_h) * scale(win_w, T + 20, win_h) * Cube()
wall = wall - opening
wall = wall.color(0.90, 0.88, 0.82, 1)

# 玻璃(薄板，半透明)
glass = translate(win_x + 30, T/3, sill_h + 30) * scale(win_w - 60, T/3, win_h - 60) * Cube()
glass = glass.color(0.60, 0.80, 0.95, 0.5)

create_geometry(Combine(wall, glass))
