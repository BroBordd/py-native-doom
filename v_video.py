# v_video.py
# DESCRIPTION:
#   Software rendering framebuffers.

from doomdef import SCREENWIDTH, SCREENHEIGHT

# Doom uses 4 screen buffers.
# screens[0] is the main rendering surface.
# screens[1] - screens[3] are used for menus, the automap, and screen wipe effects.
# Each pixel is 1 byte (8-bit indexed color).
screens = [bytearray(SCREENWIDTH * SCREENHEIGHT) for _ in range(4)]

def V_Init():
    """
    Initializes the video system.
    Normally this allocates memory, but we pre-allocated the bytearrays above.
    """
    pass

def V_EnableLoadingDisk(*args, **kwargs):
    pass


def V_DrawPatchDirect(x, y, patch):
    """Bypasses the buffer to draw directly to the screen; 
    for now, redirect to V_DrawPatch."""
    V_DrawPatch(x, y, patch)

LOADING_DISK_W = 16
LOADING_DISK_H = 16


def V_RestoreBuffer():
    pass


def V_DrawPatch(x, y, patch):
    """Decode a DOOM patch lump (raw bytes) and blit it into screens[0]."""
    import struct
    if not patch or len(patch) < 8:
        return
    width, height, leftoffset, topoffset = struct.unpack_from('<hhhh', patch, 0)
    x -= leftoffset
    y -= topoffset
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        return
    buf = screens[0]
    for col in range(width):
        offset = struct.unpack_from('<I', patch, 8 + col * 4)[0]
        px = x + col
        if px < 0 or px >= SCREENWIDTH:
            continue
        pos = offset
        while pos < len(patch):
            topdelta = patch[pos]; pos += 1
            if topdelta == 0xFF:
                break
            count = patch[pos]; pos += 1
            pos += 1  # unused
            for row in range(count):
                py = y + topdelta + row
                if 0 <= py < SCREENHEIGHT:
                    buf[py * SCREENWIDTH + px] = patch[pos]
                pos += 1
            pos += 1  # unused


def V_DrawPatchDirect(x, y, patch):
    """
    Called by the engine to draw patches (like menus) directly 
    to the visible screen buffer.
    """
    # Simply redirect to your existing V_DrawPatch logic 
    # which writes to screens[0].
    V_DrawPatch(x, y, patch)

def V_CopyRect(src_scrn, x, y, width, height, dest_scrn, destx, desty):
    """
    Copies a rectangular area from one screen buffer to another.
    Required for menus and screen wipes.
    """
    import doomdef
    scr_width = doomdef.SCREENWIDTH
    
    src = screens[src_scrn]
    dest = screens[dest_scrn]
    
    for row in range(height):
        src_offset = (y + row) * scr_width + x
        dest_offset = (desty + row) * scr_width + destx
        dest[dest_offset : dest_offset + width] = src[src_offset : src_offset + width]

def V_GetStrategy():
    """Returns the current video strategy (usually 0 for software)."""
    return 0
