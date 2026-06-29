from pyp3d import *

# 四坡屋顶(近似) = 矩形底面 → 较小矩形顶面 用 Loft 放样
# 四个梯形坡面交汇于顶部的短脊(较小矩形)。
L, W = 8000, 6000
H_wall = 3000
H_roof = 2000
TL, TW = 2000, 1000   # 顶部脊的尺寸(小于底面)

base = translate(0, 0, H_wall) * \
       Section(Vec2(0, 0), Vec2(L, 0), Vec2(L, W), Vec2(0, W))
top = translate((L - TL) / 2, (W - TW) / 2, H_wall + H_roof) * \
      Section(Vec2(0, 0), Vec2(TL, 0), Vec2(TL, TW), Vec2(0, TW))

roof = Loft(base, top)
roof = roof.color(0.72, 0.25, 0.22, 1)

create_geometry(roof)
