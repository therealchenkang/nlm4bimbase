from pyp3d import *

# 楼梯: 12级, 踏步宽300mm, 高150mm, 楼梯宽度1000mm (Cube 角点语义)
num_steps = 12
tread_w = 300
tread_h = 150
stair_width = 1000

steps = []
for i in range(num_steps):
    # 每级踏步: X[i*tread_w, (i+1)*tread_w] Y[0, stair_width] Z[i*tread_h, (i+1)*tread_h]
    step = translate(i * tread_w, 0, i * tread_h) * scale(tread_w, stair_width, tread_h) * Cube()
    steps.append(step)

create_geometry(Combine(*steps))
