# r_plane.py
# Floor and ceiling (visplane) rendering
# Ported from r_plane.c / r_plane.h

from doomdef import SCREENWIDTH, SCREENHEIGHT, FRACBITS, FRACUNIT, fixed_mul, fixed_div
from r_defs import VisPlane, BOXTOP, BOXBOTTOM, BOXLEFT, BOXRIGHT
from tables import ANGLETOFINESHIFT, finesine, finecosine

MAXVISPLANES = 128
MAXOPENINGS  = SCREENWIDTH * 64

# ------------------------------------------------------------------
# Visplane pool
# ------------------------------------------------------------------
visplanes:     list = [VisPlane() for _ in range(MAXVISPLANES)]
lastvisplane:  int  = 0    # index of next free slot
floorplane           = None   # VisPlane or None (set per subsector)
ceilingplane         = None

# Opening (clip span) buffer — Python list of ints replacing short[]
openings:     list = [0] * MAXOPENINGS
lastopening:  int  = 0   # index of next free slot

# Column clip arrays
floorclip:   list = [SCREENHEIGHT] * SCREENWIDTH
ceilingclip: list = [-1]          * SCREENWIDTH

# Span start accumulator (per screen row)
spanstart: list = [0] * SCREENHEIGHT
spanstop:  list = [0] * SCREENHEIGHT

# Plane texture mapping state
planezlight   = None    # list of colormap levels for this plane
planeheight:  int = 0

# Per-row caches
cachedheight:   list = [0] * SCREENHEIGHT
cacheddistance: list = [0] * SCREENHEIGHT
cachedxstep:    list = [0] * SCREENHEIGHT
cachedystep:    list = [0] * SCREENHEIGHT

basexscale: int = 0
baseyscale: int = 0

# sky
ANGLETOSKYSHIFT = 22


# ------------------------------------------------------------------
# R_InitPlanes
# ------------------------------------------------------------------
def R_InitPlanes():
    pass   # nothing to initialise


# ------------------------------------------------------------------
# R_ClearPlanes
# ------------------------------------------------------------------
def R_ClearPlanes():
    global lastvisplane, lastopening, basexscale, baseyscale
    import r_main
    from doomdef import ANG90

    for i in range(r_main.viewwidth):
        floorclip[i]   = r_main.viewheight
        ceilingclip[i] = -1

    lastvisplane = 0
    lastopening  = 0

    for i in range(SCREENHEIGHT):
        cachedheight[i] = 0

    # Base scales for flat texture mapping
    angle = (r_main.viewangle - ANG90) >> ANGLETOFINESHIFT
    angle &= 0x1FFF
    basexscale =  fixed_div(finecosine[angle], r_main.centerxfrac)
    baseyscale = -fixed_div(finesine[angle],   r_main.centerxfrac)


# ------------------------------------------------------------------
# R_FindPlane
# ------------------------------------------------------------------
def R_FindPlane(height: int, picnum: int, lightlevel: int) -> VisPlane:
    global lastvisplane
    import doomstat

    if picnum == doomstat.skyflatnum:
        height     = 0
        lightlevel = 0

    for i in range(lastvisplane):
        pl = visplanes[i]
        if pl.height == height and pl.picnum == picnum and pl.lightlevel == lightlevel:
            return pl

    if lastvisplane == MAXVISPLANES:
        raise RuntimeError('R_FindPlane: no more visplanes')

    pl = visplanes[lastvisplane]
    lastvisplane += 1
    pl.height     = height
    pl.picnum     = picnum
    pl.lightlevel = lightlevel
    pl.minx       = SCREENWIDTH
    pl.maxx       = -1
    for i in range(SCREENWIDTH):
        pl.top[i]    = 0xFF
        pl.bottom[i] = 0xFF
    return pl


# ------------------------------------------------------------------
# R_CheckPlane
# ------------------------------------------------------------------
def R_CheckPlane(pl: VisPlane, start: int, stop: int) -> VisPlane:
    global lastvisplane

    intrl  = pl.minx if start < pl.minx else start
    unionl = start   if start < pl.minx else pl.minx
    intrh  = pl.maxx if stop  > pl.maxx else stop
    unionh = stop    if stop  > pl.maxx else pl.maxx

    # check if intersection range is already used
    x = intrl
    while x <= intrh:
        if pl.top[x] != 0xFF:
            break
        x += 1

    if x > intrh:
        pl.minx = unionl
        pl.maxx = unionh
        return pl

    # need new visplane
    if lastvisplane == MAXVISPLANES:
        raise RuntimeError('R_CheckPlane: no more visplanes')

    newpl = visplanes[lastvisplane]
    lastvisplane += 1
    newpl.height     = pl.height
    newpl.picnum     = pl.picnum
    newpl.lightlevel = pl.lightlevel
    newpl.minx       = start
    newpl.maxx       = stop
    for i in range(SCREENWIDTH):
        newpl.top[i]    = 0xFF
        newpl.bottom[i] = 0xFF
    return newpl


# ------------------------------------------------------------------
# R_MapPlane  — emit one horizontal span
# ------------------------------------------------------------------
def R_MapPlane(y: int, x1: int, x2: int):
    import r_draw
    import r_main

    if planeheight != cachedheight[y]:
        cachedheight[y]   = planeheight
        distance          = fixed_mul(planeheight, r_main.yslope[y])
        cacheddistance[y] = distance
        cachedxstep[y]    = fixed_mul(distance, basexscale)
        cachedystep[y]    = fixed_mul(distance, baseyscale)
    else:
        distance = cacheddistance[y]

    r_draw.ds_xstep = cachedxstep[y]
    r_draw.ds_ystep = cachedystep[y]

    length = fixed_mul(distance, r_main.distscale[x1])
    angle  = ((r_main.viewangle + r_main.xtoviewangle[x1]) >> ANGLETOFINESHIFT) & 0x1FFF
    r_draw.ds_xfrac =  r_main.viewx + fixed_mul(finecosine[angle], length)
    r_draw.ds_yfrac = -r_main.viewy - fixed_mul(finesine[angle],   length)

    if r_main.fixedcolormap:
        r_draw.ds_colormap = r_main.fixedcolormap
    else:
        from r_main import MAXLIGHTZ, LIGHTZSHIFT
        index = distance >> LIGHTZSHIFT
        if index >= MAXLIGHTZ:
            index = MAXLIGHTZ - 1
        r_draw.ds_colormap = planezlight[index]

    r_draw.ds_y  = y
    r_draw.ds_x1 = x1
    r_draw.ds_x2 = x2

    import r_main as _rm
    _rm.spanfunc()


# ------------------------------------------------------------------
# R_MakeSpans  — advance span boundaries column by column
# ------------------------------------------------------------------
def R_MakeSpans(x: int, t1: int, b1: int, t2: int, b2: int):
    while t1 < t2 and t1 <= b1:
        R_MapPlane(t1, spanstart[t1], x - 1)
        t1 += 1
    while b1 > b2 and b1 >= t1:
        R_MapPlane(b1, spanstart[b1], x - 1)
        b1 -= 1
    while t2 < t1 and t2 <= b2:
        spanstart[t2] = x
        t2 += 1
    while b2 > b1 and b2 >= t2:
        spanstart[b2] = x
        b2 -= 1


# ------------------------------------------------------------------
# R_DrawPlanes  — render all collected visplanes at end of frame
# ------------------------------------------------------------------
def R_DrawPlanes():
    import r_main
    import r_draw
    import doomstat
    from r_data import (
        firstflat, flattranslation, numflats,
        colormaps, skytexture,
    )
    from wad import get_wad
    global planezlight, planeheight

    from r_main import (
        LIGHTLEVELS, LIGHTSEGSHIFT, MAXLIGHTZ, LIGHTZSHIFT,
        extralight, fixedcolormap, zlight,
        pspriteiscale, detailshift, xtoviewangle, viewangle,
        colfunc,
    )
    import r_sky

    for pi in range(lastvisplane):
        pl = visplanes[pi]
        if pl.minx > pl.maxx:
            continue

        # ---------- sky ----------
        if pl.picnum == doomstat.skyflatnum:
            r_draw.dc_iscale     = pspriteiscale >> detailshift
            r_draw.dc_colormap   = 0   # colormaps[0] = full bright
            r_draw.dc_texturemid = r_sky.skytexturemid

            for x in range(pl.minx, pl.maxx + 1):
                r_draw.dc_yl = pl.top[x]
                r_draw.dc_yh = pl.bottom[x]
                if r_draw.dc_yl <= r_draw.dc_yh:
                    angle = (viewangle + xtoviewangle[x]) >> ANGLETOSKYSHIFT
                    r_draw.dc_x = x
                    from r_data import R_GetColumn
                    r_draw.dc_source = R_GetColumn(skytexture, angle)
                    r_main.colfunc()
            continue

        # ---------- regular flat ----------
        lump_idx = firstflat + flattranslation[pl.picnum]
        wad = get_wad()
        r_draw.ds_source = wad.get_lump_by_index(lump_idx).data

        planeheight = abs(pl.height - r_main.viewz)
        light = (pl.lightlevel >> LIGHTSEGSHIFT) + extralight
        light = max(0, min(light, LIGHTLEVELS - 1))
        planezlight = zlight[light]

        pl.top[pl.maxx + 1] = 0xFF
        pl.top[pl.minx - 1] = 0xFF

        stop = pl.maxx + 1
        for x in range(pl.minx, stop + 1):
            R_MakeSpans(
                x,
                pl.top[x - 1]    if pl.top[x - 1]    != 0xFF else 0,
                pl.bottom[x - 1] if pl.bottom[x - 1] != 0xFF else -1,
                pl.top[x]        if pl.top[x]         != 0xFF else 0,
                pl.bottom[x]     if pl.bottom[x]      != 0xFF else -1,
            )
