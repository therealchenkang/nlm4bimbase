from pyp3d import *

# === 完整房屋(复合示例) ===
# 地面 + 四面墙(含门洞/窗洞) + 双坡(人字形)屋顶
#
# ★★★ 最关键的坑: BIMBase 的 Cube() 是【角点语义】[0,1]³ (最小角在原点，
#     向 +X+Y+Z 延伸)，不是中心在原点！
#     正确写法: translate(MIN_X, MIN_Y, MIN_Z) * scale(长, 宽, 高) * Cube()
#     覆盖范围 = [MIN_X, MIN_X+长] × [MIN_Y, MIN_Y+宽] × [MIN_Z, MIN_Z+高]
#     (Extrusion/Sphere/Cone 用绝对坐标，不受此影响)
# ★ 颜色必须在所有布尔运算(+-)之后再赋值
# ★ 尖屋顶 = 双坡(人字形) = 三棱柱(三角形截面 Extrusion)，不是四棱锥

# --- 房屋参数 (mm) ---
L, W = 8000, 6000           # 长(开间) × 宽(进深)
T_wall = 240                # 墙厚
H_wall = 3000               # 墙高
H_roof = 1500               # 屋顶高度(墙顶到屋脊)
door_w, door_h = 1200, 2100
win_w, win_h, sill_h = 1500, 1200, 900

# --- 地面(略大于房屋，铺到墙外) --- 覆盖 X[-500,L+500] Y[-500,W+500] Z[-100,0]
floor = translate(-500, -500, -100) * scale(L + 1000, W + 1000, 100) * Cube()
floor = floor.color(0.60, 0.50, 0.40, 1)

# --- 四面墙(角点语义，围成封闭筒) ---
wall_front = translate(0, 0,         0) * scale(L,     T_wall,         H_wall) * Cube()  # X[0,L] Y[0,T]
wall_back  = translate(0, W-T_wall,   0) * scale(L,     T_wall,         H_wall) * Cube()  # X[0,L] Y[W-T,W]
wall_left  = translate(0, T_wall,     0) * scale(T_wall, W-2*T_wall,    H_wall) * Cube()  # X[0,T] Y[T,W-T]
wall_right = translate(L-T_wall, T_wall, 0) * scale(T_wall, W-2*T_wall, H_wall) * Cube()  # X[L-T,L] Y[T,W-T]
walls = Combine(wall_front, wall_back, wall_left, wall_right)

# --- 正面墙开门洞(居中) --- 洞 X[L/2-door_w/2, L/2+door_w/2] Y穿透 Z[0,door_h]
walls = walls - (translate(L/2 - door_w/2, -10, 0) * scale(door_w, T_wall + 20, door_h) * Cube())
# --- 背面墙开窗洞(居中, 窗台高 sill_h) ---
walls = walls - (translate(L/2 - win_w/2, W-T_wall-10, sill_h) * scale(win_w, T_wall + 20, win_h) * Cube())

# 布尔运算结束后再赋颜色
walls = walls.color(0.90, 0.88, 0.82, 1)

# --- 双坡(人字形)屋顶 = 三棱柱(Extrusion 绝对坐标，已实测定位正确) ---
tri_pts = [
    GeVec3d(0,   0, H_wall),           # 底边左
    GeVec3d(L,   0, H_wall),           # 底边右
    GeVec3d(L/2, 0, H_wall + H_roof),  # 屋脊顶点
]
roof = Extrusion(tri_pts, GeVec3d(0, W, 0))
roof = roof.color(0.72, 0.25, 0.22, 1)

# --- 组合所有构件 ---
create_geometry(Combine(floor, walls, roof))
