import threading
import time
import traceback
from PIL import Image

# Boot doom in a background thread
import d_main

def _run():
    try:
        d_main.D_DoomMain()
    except Exception:
        traceback.print_exc()

t = threading.Thread(target=_run, daemon=True)
t.start()

# Wait for the engine to reach the demo screen
time.sleep(8)

# Grab framebuffer and palette
import v_video
import i_video
from doomdef import SCREENWIDTH, SCREENHEIGHT

raw     = bytes(v_video.screens[0])
palette = bytes(i_video.current_palette)

# Convert indexed -> RGB
rgb = bytearray(SCREENWIDTH * SCREENHEIGHT * 3)
for i, idx in enumerate(raw):
    rgb[i*3:i*3+3] = palette[idx*3:idx*3+3]

img = Image.frombytes("RGB", (SCREENWIDTH, SCREENHEIGHT), bytes(rgb))
img.save("doom_snapshot.png")
print("Saved doom_snapshot.png")
