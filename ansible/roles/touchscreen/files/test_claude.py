#!/usr/bin/env python3

import time, numpy as np
from st7796 import st7796
from PIL import Image, ImageDraw

# 用现有驱动初始化屏幕（包含 lcd_init）
dev = st7796()

# 临时把 SPI 频率降至 40MHz 进行测试
dev.SPI.max_speed_hz = 32000000

def push_fast(dev, img):
    arr = np.asarray(img)
    pix = np.zeros((320, 480, 2), dtype=np.uint8)
    pix[..., [0]] = np.add(np.bitwise_and(arr[..., [0]], 0xF8), np.right_shift(arr[..., [1]], 5))
    pix[..., [1]] = np.add(np.bitwise_and(np.left_shift(arr[..., [1]], 3), 0xE0), np.right_shift(arr[..., [2]], 3))
    dev.command(0x36)
    dev.data(0xE8)
    dev.set_windows(0, 0, dev.height, dev.width, 1)
    dev.digital_write(dev.GPIO_DC_PIN, True)
    data = pix.tobytes()
    for i in range(0, len(data), 4096):
        dev.SPI.writebytes2(data[i:i+4096])

# 红
push_fast(dev, Image.new('RGB', (480, 320), (255, 0, 0)))
time.sleep(2)

# 绿
push_fast(dev, Image.new('RGB', (480, 320), (0, 255, 0)))
time.sleep(2)

# 蓝
push_fast(dev, Image.new('RGB', (480, 320), (0, 0, 255)))
time.sleep(2)

# 文字
img = Image.new('RGB', (480, 320), (20, 20, 20))
draw = ImageDraw.Draw(img)
draw.text((40, 100), '40MHz test', fill=(255, 255, 0))
draw.text((40, 160), 'Colors correct?', fill=(255, 255, 255))
push_fast(dev, img)
time.sleep(5)

t = time.time()
for _ in range(10):
    push_fast(dev, img)
print(f'avg: {(time.time()-t)/10*1000:.1f}ms')