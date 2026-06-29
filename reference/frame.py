from pyp3d import *

# 单层单跨框架: 柱+梁 (Cube 角点语义)
span = 6000
H_floor = 3000
Cx, Cy = 400, 400
H_beam, W_beam = 500, 300

parts = []

# 两根柱: 每根 X[ix*span, ix*span+Cx] Y[0,Cy] Z[0,H_floor]
for ix in range(2):
    col = translate(ix * span, 0, 0) * scale(Cx, Cy, H_floor) * Cube()
    parts.append(col)

# 一根梁(连接两柱顶): X[0, span+Cx] Y[0, W_beam] Z[H_floor-H_beam, H_floor]
beam = translate(0, 0, H_floor - H_beam) * scale(span + Cx, W_beam, H_beam) * Cube()
parts.append(beam)

create_geometry(Combine(*parts))
