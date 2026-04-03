# r_draw.py
# Column and span pixel drawers — write directly into the framebuffer bytearray.
# Ported from r_draw.c / r_draw.h
#
# The framebuffer is a bytearray of SCREENWIDTH*SCREENHEIGHT bytes,
# one palette-index byte per pixel, in row-major order.
# Your hook code reads this bytearray and converts it to whatever
# display format you need.

from doomdef import SCREENWIDTH, SCREENHEIGHT, FRACBITS

MAXWIDTH  = 1120
MAXHEIGHT = 832
SBARHEIGHT = 32

# ------------------------------------------------------------------
# The framebuffer — your hook replaces this with your own bytearray
# if you want zero-copy.  The renderer writes here every frame.
# ------------------------------------------------------------------
screen: bytearray = bytearray(SCREENWIDTH * SCREENHEIGHT)

# Address lookup tables (built by R_InitBuffer)
# ylookup[y] = base offset in 'screen' for screen row y
ylookup:   list = [0] * MAXHEIGHT
# columnofs[x] = pixel offset within a row for column x (handles windowed mode)
columnofs: list = list(range(MAXWIDTH))

# View window geometry (set by R_InitBuffer)
viewwindowx: int = 0
viewwindowy: int = 0

# ------------------------------------------------------------------
# Column draw state (dc_* globals)
# ------------------------------------------------------------------
dc_colormap   = None   # int colormap-level (0-31), or raw bytearray slice
dc_x:          int = 0
dc_yl:         int = 0
dc_yh:         int = 0
dc_iscale:     int = 0
dc_texturemid: int = 0
dc_source      = None  # bytes / bytearray / memoryview of texture column

# Span draw state (ds_* globals)
ds_y:       int = 0
ds_x1:      int = 0
ds_x2:      int = 0
ds_colormap = None
ds_xfrac:   int = 0
ds_yfrac:   int = 0
ds_xstep:   int = 0
ds_ystep:   int = 0
ds_source   = None   # 64×64 flat data (bytes / bytearray)

# Translation tables
translationtables: bytearray = bytearray(256 * 3)
dc_translation    = None

# Fuzz effect
FUZZTABLE = 50
FUZZOFF   = SCREENWIDTH
_fuzzoffset = [
    FUZZOFF,-FUZZOFF,FUZZOFF,-FUZZOFF,FUZZOFF,FUZZOFF,-FUZZOFF,
    FUZZOFF,FUZZOFF,-FUZZOFF,FUZZOFF,FUZZOFF,FUZZOFF,-FUZZOFF,
    FUZZOFF,FUZZOFF,FUZZOFF,-FUZZOFF,-FUZZOFF,-FUZZOFF,-FUZZOFF,
    FUZZOFF,-FUZZOFF,-FUZZOFF,FUZZOFF,FUZZOFF,FUZZOFF,FUZZOFF,-FUZZOFF,
    FUZZOFF,-FUZZOFF,FUZZOFF,FUZZOFF,-FUZZOFF,-FUZZOFF,FUZZOFF,
    FUZZOFF,-FUZZOFF,-FUZZOFF,-FUZZOFF,-FUZZOFF,FUZZOFF,FUZZOFF,
    FUZZOFF,FUZZOFF,-FUZZOFF,FUZZOFF,FUZZOFF,-FUZZOFF,FUZZOFF
]
fuzzpos: int = 0


def _colormap_byte(cm, idx: int) -> int:
    """
    Apply colormap to palette index idx.
    cm can be:
      int   → colormap level; look up in r_data.colormaps
      bytes/bytearray/memoryview → direct 256-byte table
    """
    if cm is None:
        return idx
    if isinstance(cm, int):
        from r_data import colormaps
        return colormaps[cm * 256 + idx]
    return cm[idx]


# ------------------------------------------------------------------
# R_DrawColumn  — solid wall/sprite column, high detail
# ------------------------------------------------------------------
def R_DrawColumn():
    count = dc_yh - dc_yl
    if count < 0:
        return

    fracstep = dc_iscale
    frac = dc_texturemid + (dc_yl - _centery()) * fracstep

    dest = ylookup[dc_yl] + columnofs[dc_x]

    src  = dc_source
    cm   = dc_colormap
    sw   = SCREENWIDTH
    fb   = screen

    for _ in range(count + 1):
        fb[dest] = _colormap_byte(cm, src[(frac >> FRACBITS) & 127])
        dest += sw
        frac += fracstep


def R_DrawColumnLow():
    count = dc_yh - dc_yl
    if count < 0:
        return

    x    = dc_x << 1
    fracstep = dc_iscale
    frac = dc_texturemid + (dc_yl - _centery()) * fracstep
    dest  = ylookup[dc_yl] + columnofs[x]
    dest2 = ylookup[dc_yl] + columnofs[x + 1]

    src = dc_source
    cm  = dc_colormap
    sw  = SCREENWIDTH
    fb  = screen

    for _ in range(count + 1):
        pix = _colormap_byte(cm, src[(frac >> FRACBITS) & 127])
        fb[dest]  = pix
        fb[dest2] = pix
        dest  += sw
        dest2 += sw
        frac  += fracstep


# ------------------------------------------------------------------
# R_DrawFuzzColumn  — spectre/invisibility
# ------------------------------------------------------------------
def R_DrawFuzzColumn():
    global fuzzpos
    import r_main
    vh = r_main.viewheight

    if not dc_yl:
        dc_yl_local = 1
    else:
        dc_yl_local = dc_yl

    dc_yh_local = dc_yh
    if dc_yh_local == vh - 1:
        dc_yh_local = vh - 2

    count = dc_yh_local - dc_yl_local
    if count < 0:
        return

    from r_data import colormaps
    dest = ylookup[dc_yl_local] + columnofs[dc_x]
    fb   = screen
    sw   = SCREENWIDTH

    for _ in range(count + 1):
        fb[dest] = colormaps[6 * 256 + fb[dest + _fuzzoffset[fuzzpos]]]
        fuzzpos += 1
        if fuzzpos == FUZZTABLE:
            fuzzpos = 0
        dest += sw


def R_DrawFuzzColumnLow():
    global fuzzpos
    import r_main
    vh = r_main.viewheight

    if not dc_yl:
        dc_yl_local = 1
    else:
        dc_yl_local = dc_yl
    dc_yh_local = dc_yh
    if dc_yh_local == vh - 1:
        dc_yh_local = vh - 2

    count = dc_yh_local - dc_yl_local
    if count < 0:
        return

    x     = dc_x << 1
    from r_data import colormaps
    dest  = ylookup[dc_yl_local] + columnofs[x]
    dest2 = ylookup[dc_yl_local] + columnofs[x + 1]
    fb    = screen
    sw    = SCREENWIDTH

    for _ in range(count + 1):
        pix  = colormaps[6 * 256 + fb[dest  + _fuzzoffset[fuzzpos]]]
        pix2 = colormaps[6 * 256 + fb[dest2 + _fuzzoffset[fuzzpos]]]
        fb[dest]  = pix
        fb[dest2] = pix2
        fuzzpos += 1
        if fuzzpos == FUZZTABLE:
            fuzzpos = 0
        dest  += sw
        dest2 += sw


# ------------------------------------------------------------------
# R_DrawTranslatedColumn  — player color shirt remapping
# ------------------------------------------------------------------
def R_DrawTranslatedColumn():
    count = dc_yh - dc_yl
    if count < 0:
        return

    fracstep = dc_iscale
    frac = dc_texturemid + (dc_yl - _centery()) * fracstep
    dest = ylookup[dc_yl] + columnofs[dc_x]

    src  = dc_source
    cm   = dc_colormap
    tr   = dc_translation
    sw   = SCREENWIDTH
    fb   = screen

    for _ in range(count + 1):
        fb[dest] = _colormap_byte(cm, tr[src[frac >> FRACBITS]])
        dest += sw
        frac += fracstep


def R_DrawTranslatedColumnLow():
    count = dc_yh - dc_yl
    if count < 0:
        return

    x = dc_x << 1
    fracstep = dc_iscale
    frac = dc_texturemid + (dc_yl - _centery()) * fracstep
    dest  = ylookup[dc_yl] + columnofs[x]
    dest2 = ylookup[dc_yl] + columnofs[x + 1]

    src = dc_source
    cm  = dc_colormap
    tr  = dc_translation
    sw  = SCREENWIDTH
    fb  = screen

    for _ in range(count + 1):
        pix = _colormap_byte(cm, tr[src[frac >> FRACBITS]])
        fb[dest]  = pix
        fb[dest2] = pix
        dest  += sw
        dest2 += sw
        frac  += fracstep


# ------------------------------------------------------------------
# R_DrawSpan  — floor/ceiling horizontal span, high detail
# The original uses a 32-bit packed position trick (x in hi 16, y in lo 16).
# We replicate it faithfully for identical flat texture mapping.
# ------------------------------------------------------------------
def R_DrawSpan():
    position = ((ds_xfrac << 10) & 0xffff0000) | ((ds_yfrac >> 6) & 0x0000ffff)
    step      = ((ds_xstep << 10) & 0xffff0000) | ((ds_ystep >> 6) & 0x0000ffff)
    # mask to 32-bit unsigned
    position &= 0xFFFFFFFF
    step      &= 0xFFFFFFFF

    dest  = ylookup[ds_y] + columnofs[ds_x1]
    count = ds_x2 - ds_x1

    src = ds_source
    cm  = ds_colormap
    fb  = screen

    for _ in range(count + 1):
        ytemp = (position >> 4) & 0x0fc0
        xtemp = (position >> 26) & 0x3f
        spot  = xtemp | ytemp
        fb[dest] = _colormap_byte(cm, src[spot])
        dest += 1
        position = (position + step) & 0xFFFFFFFF


def R_DrawSpanLow():
    position = ((ds_xfrac << 10) & 0xffff0000) | ((ds_yfrac >> 6) & 0x0000ffff)
    step      = ((ds_xstep << 10) & 0xffff0000) | ((ds_ystep >> 6) & 0x0000ffff)
    position &= 0xFFFFFFFF
    step      &= 0xFFFFFFFF

    count = ds_x2 - ds_x1
    x1    = ds_x1 << 1

    dest  = ylookup[ds_y] + columnofs[x1]
    src   = ds_source
    cm    = ds_colormap
    fb    = screen

    for _ in range(count + 1):
        ytemp = (position >> 4) & 0x0fc0
        xtemp = (position >> 26) & 0x3f
        spot  = xtemp | ytemp
        pix   = _colormap_byte(cm, src[spot])
        fb[dest]     = pix
        fb[dest + 1] = pix
        dest     += 2
        position = (position + step) & 0xFFFFFFFF


# ------------------------------------------------------------------
# R_InitBuffer  — build ylookup / columnofs
# ------------------------------------------------------------------
def R_InitBuffer(width: int, height: int):
    global viewwindowx, viewwindowy

    viewwindowx = (SCREENWIDTH - width) >> 1

    for i in range(width):
        columnofs[i] = viewwindowx + i

    if width == SCREENWIDTH:
        viewwindowy = 0
    else:
        viewwindowy = (SCREENHEIGHT - SBARHEIGHT - height) >> 1

    for i in range(height):
        ylookup[i] = (i + viewwindowy) * SCREENWIDTH


# ------------------------------------------------------------------
# R_InitTranslationTables  — green → gray / brown / red shirt ramps
# ------------------------------------------------------------------
def R_InitTranslationTables():
    global translationtables
    translationtables = bytearray(256 * 3)
    for i in range(256):
        if 0x70 <= i <= 0x7f:
            translationtables[i]         = 0x60 + (i & 0xf)   # gray
            translationtables[i + 256]   = 0x40 + (i & 0xf)   # brown
            translationtables[i + 512]   = 0x20 + (i & 0xf)   # red
        else:
            translationtables[i]         = i
            translationtables[i + 256]   = i
            translationtables[i + 512]   = i


# ------------------------------------------------------------------
# R_VideoErase  — copy background buffer over screen (windowed mode)
# ------------------------------------------------------------------
def R_VideoErase(ofs: int, count: int):
    # In full-screen mode there's no background; this is a no-op.
    pass


# ------------------------------------------------------------------
# R_FillBackScreen / R_DrawViewBorder — border drawing (windowed mode)
# Full-screen is always used in our port, so these are stubs.
# ------------------------------------------------------------------
def R_FillBackScreen():
    pass

def R_DrawViewBorder():
    pass


# ------------------------------------------------------------------
# Helper: centery cached reference (avoids import cycle)
# ------------------------------------------------------------------
def _centery() -> int:
    import r_main
    return r_main.centery
