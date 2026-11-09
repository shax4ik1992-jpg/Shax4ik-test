import numpy as np
from PIL import Image
import sys
out = sys.argv[1]
W, H = 2400, 1350
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
base = np.array([14, 22, 38], np.float32)
img = np.ones((H, W, 3), np.float32) * base
def glow(cx, cy, r, col, strength):
    d = np.sqrt(((x - cx) / r) ** 2 + ((y - cy) / r) ** 2)
    a = np.clip(1 - d, 0, 1) ** 2.2 * strength
    return a[..., None] * (np.array(col, np.float32) - base)
img += glow(0.80 * W, 0.30 * H, 0.75 * W, [38, 56, 90], 0.85)
img += glow(0.02 * W, 1.05 * H, 0.55 * W, [26, 40, 66], 0.7)
# soft vignette
d = np.sqrt(((x - W / 2) / (W / 1.2)) ** 2 + ((y - H / 2) / (H / 1.1)) ** 2)
img *= (1 - 0.18 * np.clip(d, 0, 1) ** 2)[..., None]
rng = np.random.default_rng(7)
img += rng.normal(0, 1.6, (H, W, 1))
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, quality=93, subsampling=0)
