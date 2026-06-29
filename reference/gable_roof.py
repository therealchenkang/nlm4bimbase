from pyp3d import *

# 双坡(人字形)屋顶 ★ = 三棱柱
# 中文"尖屋顶/坡屋顶"通常指双坡：两个斜屋面交汇于一条屋脊线。
# 几何构造 = 三角形截面(XZ平面) 沿房屋宽度(Y)方向拉伸。
# 注意：不是四棱锥(顶点收于一点)。
L, W = 8000, 6000          # 房屋长 × 宽
H_wall = 3000              # 墙顶标高(屋顶底面)
H_roof = 2000              # 屋顶高度(墙顶到屋脊)

tri_pts = [
    GeVec3d(0,   0, H_wall),          # 底边左
    GeVec3d(L,   0, H_wall),          # 底边右
    GeVec3d(L/2, 0, H_wall + H_roof), # 屋脊顶点
]
roof = Extrusion(tri_pts, GeVec3d(0, W, 0))   # 沿 Y 拉伸成三棱柱
roof = roof.color(0.72, 0.25, 0.22, 1)        # 暗红色

create_geometry(roof)
