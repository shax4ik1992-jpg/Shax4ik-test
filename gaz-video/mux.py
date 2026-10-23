"""Mux rendered videos with the SFX track -> output/gaz_matnli.mp4, output/gaz_toza.mp4."""
import os
import subprocess

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def main():
    sfx = os.path.join(OUT, "sfx.wav")
    for src, dst in (("gaz_matnli_video.mp4", "gaz_matnli.mp4"), ("gaz_toza_video.mp4", "gaz_toza.mp4")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(OUT, src), "-i", sfx, "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", os.path.join(OUT, dst)], check=True)
        print("wrote", dst)


if __name__ == "__main__":
    main()
