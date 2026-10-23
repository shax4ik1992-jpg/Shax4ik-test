"""Render the video.

  python3 render.py                 # full render -> output/gaz_matnli.mp4 + output/gaz_toza.mp4
  python3 render.py --stills 3 15.2 # preview PNGs at given seconds -> output/stills/
  python3 render.py --from 40 --to 50 --workers 2   # partial render (for checks)
"""
import argparse
import os
import subprocess
import sys

# keep big numpy buffers in the heap instead of mmap/munmap per frame (avoids page-fault storms)
if os.environ.get("MALLOC_MMAP_THRESHOLD_") is None:
    env = dict(os.environ, MALLOC_MMAP_THRESHOLD_="1073741824", MALLOC_TRIM_THRESHOLD_="4294967296")
    os.execve(sys.executable, [sys.executable] + sys.argv, env)

import multiprocessing as mp  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import config as C  # noqa: E402
from timeline import DURATION  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")


def ffmpeg_writer(path):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{C.W}x{C.H}",
           "-r", str(C.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def worker(args):
    wid, f0, f1, tmp = args
    import scenes
    w_clean = ffmpeg_writer(os.path.join(tmp, f"clean_{wid:02d}.mp4"))
    w_cap = ffmpeg_writer(os.path.join(tmp, f"cap_{wid:02d}.mp4"))
    for f in range(f0, f1):
        t = f / C.FPS
        clean, cap = scenes.draw_frame(t)
        w_clean.stdin.write(clean.tobytes())
        w_cap.stdin.write(cap.tobytes())
        if wid == 0 and f % 60 == 0:
            print(f"  worker0 {f - f0}/{f1 - f0} frames", flush=True)
    for w in (w_clean, w_cap):
        w.stdin.close()
        w.wait()
    return wid


def concat(parts, out):
    lst = out + ".txt"
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                   check=True)
    os.remove(lst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.stills is not None:
        import scenes
        sd = os.path.join(OUT, "stills")
        os.makedirs(sd, exist_ok=True)
        for t in a.stills:
            _, cap = scenes.draw_frame(t)
            cv2.imwrite(os.path.join(sd, f"t{t:06.2f}.jpg"), cv2.cvtColor(cap, cv2.COLOR_RGBA2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
            print("still", t)
        return
    t1 = DURATION if a.t1 is None else min(a.t1, DURATION)
    F0, F1 = int(a.t0 * C.FPS), int(round(t1 * C.FPS))
    tmp = os.path.join(OUT, "_parts")
    os.makedirs(tmp, exist_ok=True)
    n = a.workers
    step = (F1 - F0 + n - 1) // n
    jobs = [(i, F0 + i * step, min(F1, F0 + (i + 1) * step), tmp) for i in range(n) if F0 + i * step < F1]
    print(f"render {F1 - F0} frames ({(F1 - F0) / C.FPS:.1f}s) with {len(jobs)} workers")
    with mp.get_context("fork").Pool(len(jobs)) as pool:
        for wid in pool.imap_unordered(worker, jobs):
            print(f"  part {wid} done", flush=True)
    for kind, name in (("clean", "gaz_toza"), ("cap", "gaz_matnli")):
        parts = [os.path.join(tmp, f"{kind}_{j[0]:02d}.mp4") for j in jobs]
        concat(parts, os.path.join(OUT, f"{name}{a.suffix}_video.mp4"))
    print("video done")


if __name__ == "__main__":
    main()
