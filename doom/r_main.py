# r_main.py
# Renderer main: POV setup, trig utilities, lighting tables, render loop
# Ported from r_main.c / r_main.h

from doomdef import (
    SCREENWIDTH, SCREENHEIGHT, FRACBITS, FRACUNIT,
    ANG90, ANG180, ANG270,
    fixed_mul, fixed_div,
    NF_SUBSECTOR,
)
from tables import (
    finesine, finecosine, finetangent, tantoangle,
    ANGLETOFINESHIFT, FINEANGLES, SlopeDiv,
    ANG45,
)

# ------------------------------------------------------------------
# Lighting constants
# ------------------------------------------------------------------
LIGHTLEVELS    = 16
LIGHTSEGSHIFT  = 4
MAXLIGHTSCALE  = 48
LIGHTSCALESHIFT = 12
MAXLIGHTZ      = 128
LIGHTZSHIFT    = 20
NUMCOLORMAPS   = 32
FIELDOFVIEW    = 2048       # fine angles in screen width

DISTMAP        = 2

# ------------------------------------------------------------------
# View / POV state
# ------------------------------------------------------------------
viewx: int = 0
viewy: int = 0
viewz: int = 0
viewangle: int = 0
viewcos: int = 0
viewsin: int = 0
viewplayer = None

# Current seg rendering state (used by r_segs.py)
rw_normalangle: int = 0
rw_angle1:      int = 0
rw_distance:    int = 0

# ------------------------------------------------------------------
# Screen geometry
# ------------------------------------------------------------------
viewwindowx: int = 0
viewwindowy: int = 0
viewwidth:   int = SCREENWIDTH
viewheight:  int = SCREENHEIGHT
scaledviewwidth: int = SCREENWIDTH

centerx:     int = SCREENWIDTH  // 2
centery:     int = SCREENHEIGHT // 2
centerxfrac: int = (SCREENWIDTH  // 2) << FRACBITS
centeryfrac: int = (SCREENHEIGHT // 2) << FRACBITS
projection:  int = (SCREENWIDTH  // 2) << FRACBITS

detailshift: int = 0          # 0=high, 1=low
setsizeneeded: bool = False
setblocks: int = 11
setdetail: int = 0

# Sprite scale
pspritescale:  int = FRACUNIT
pspriteiscale: int = FRACUNIT

# Per-column arrays (built by R_ExecuteSetViewSize)
screenheightarray: list = [SCREENHEIGHT] * SCREENWIDTH
yslope:     list = [0] * SCREENHEIGHT
distscale:  list = [0] * SCREENWIDTH

# ------------------------------------------------------------------
# Angle → screen-X lookup tables
# ------------------------------------------------------------------
viewangletox: list = [0] * (FINEANGLES // 2)   # fine half-angle → screen x
xtoviewangle: list = [0] * (SCREENWIDTH + 1)   # screen x → view angle offset
clipangle:    int  = 0

# ------------------------------------------------------------------
# Lighting tables
# Each entry is an integer colormap-level (0=bright,31=dark).
# The renderer uses these as indices into r_data.colormaps.
# ------------------------------------------------------------------
# scalelight[lightlevel][scaleidx] → colormap level (int 0-31)
scalelight:      list = [[0] * MAXLIGHTSCALE for _ in range(LIGHTLEVELS)]
scalelightfixed: list = [0] * MAXLIGHTSCALE
# zlight[lightlevel][zdistidx] → colormap level (int 0-31)
zlight:          list = [[0] * MAXLIGHTZ for _ in range(LIGHTLEVELS)]

extralight:     int = 0
fixedcolormap:  int = 0    # 0 = off; otherwise player colormap index

# lighting pointer used by r_segs
walllights: list = scalelight[0]

# ------------------------------------------------------------------
# Profiling counters
# ------------------------------------------------------------------
validcount:  int = 1
framecount:  int = 0
sscount:     int = 0
linecount:   int = 0
loopcount:   int = 0

# ------------------------------------------------------------------
# Draw-function pointers  (set by R_ExecuteSetViewSize)
# ------------------------------------------------------------------
colfunc      = None
basecolfunc  = None
fuzzcolfunc  = None
transcolfunc = None
spanfunc     = None


# ------------------------------------------------------------------
# R_AddPointToBox
# ------------------------------------------------------------------
def R_AddPointToBox(x: int, y: int, box: list):
    from r_defs import BOXLEFT, BOXRIGHT, BOXBOTTOM, BOXTOP
    if x < box[BOXLEFT]:   box[BOXLEFT]   = x
    if x > box[BOXRIGHT]:  box[BOXRIGHT]  = x
    if y < box[BOXBOTTOM]: box[BOXBOTTOM] = y
    if y > box[BOXTOP]:    box[BOXTOP]    = y


# ------------------------------------------------------------------
# R_PointOnSide
# ------------------------------------------------------------------
def R_PointOnSide(x: int, y: int, node) -> int:
    """0 = front (right), 1 = back (left)."""
    if not node.dx:
        if x <= node.x:
            return 1 if node.dy > 0 else 0
        return 1 if node.dy < 0 else 0

    if not node.dy:
        if y <= node.y:
            return 1 if node.dx < 0 else 0
        return 1 if node.dx > 0 else 0

    dx = x - node.x
    dy = y - node.y

    # Sign-bit fast path
    if (node.dy ^ node.dx ^ dx ^ dy) & 0x80000000:
        if (node.dy ^ dx) & 0x80000000:
            return 1
        return 0

    left  = fixed_mul(node.dy >> FRACBITS, dx)
    right = fixed_mul(dy, node.dx >> FRACBITS)

    return 0 if right < left else 1


# ------------------------------------------------------------------
# R_PointOnSegSide
# ------------------------------------------------------------------
def R_PointOnSegSide(x: int, y: int, seg) -> int:
    lx  = seg.v1.x
    ly  = seg.v1.y
    ldx = seg.v2.x - lx
    ldy = seg.v2.y - ly

    if not ldx:
        if x <= lx:
            return 1 if ldy > 0 else 0
        return 1 if ldy < 0 else 0

    if not ldy:
        if y <= ly:
            return 1 if ldx < 0 else 0
        return 1 if ldx > 0 else 0

    dx = x - lx
    dy = y - ly

    if (ldy ^ ldx ^ dx ^ dy) & 0x80000000:
        if (ldy ^ dx) & 0x80000000:
            return 1
        return 0

    left  = fixed_mul(ldy >> FRACBITS, dx)
    right = fixed_mul(dy, ldx >> FRACBITS)
    return 0 if right < left else 1


# ------------------------------------------------------------------
# R_PointToAngle  (relative to current viewx/viewy)
# ------------------------------------------------------------------
def R_PointToAngle(x: int, y: int) -> int:
    x -= viewx
    y -= viewy

    if not x and not y:
        return 0

    if x >= 0:
        if y >= 0:
            if x > y:
                return tantoangle[SlopeDiv(y, x)]
            else:
                return (ANG90 - 1 - tantoangle[SlopeDiv(x, y)]) & 0xFFFFFFFF
        else:
            y = -y
            if x > y:
                return (-tantoangle[SlopeDiv(y, x)]) & 0xFFFFFFFF
            else:
                return (ANG270 + tantoangle[SlopeDiv(x, y)]) & 0xFFFFFFFF
    else:
        x = -x
        if y >= 0:
            if x > y:
                return (ANG180 - 1 - tantoangle[SlopeDiv(y, x)]) & 0xFFFFFFFF
            else:
                return (ANG90 + tantoangle[SlopeDiv(x, y)]) & 0xFFFFFFFF
        else:
            y = -y
            if x > y:
                return (ANG180 + tantoangle[SlopeDiv(y, x)]) & 0xFFFFFFFF
            else:
                return (ANG270 - 1 - tantoangle[SlopeDiv(x, y)]) & 0xFFFFFFFF


# ------------------------------------------------------------------
# R_PointToAngle2  (arbitrary origin)
# ------------------------------------------------------------------
def R_PointToAngle2(x1: int, y1: int, x2: int, y2: int) -> int:
    global viewx, viewy
    viewx = x1
    viewy = y1
    return R_PointToAngle(x2, y2)


# ------------------------------------------------------------------
# R_PointToDist
# ------------------------------------------------------------------
def R_PointToDist(x: int, y: int) -> int:
    from tables import DBITS
    dx = abs(x - viewx)
    dy = abs(y - viewy)

    if dy > dx:
        dx, dy = dy, dx

    if dx == 0:
        frac = 0
    else:
        frac = fixed_div(dy, dx)

    angle = ((tantoangle[frac >> DBITS] + ANG90) >> ANGLETOFINESHIFT) & 0x1FFF
    dist  = fixed_div(dx, finesine[angle])
    return dist


# ------------------------------------------------------------------
# R_ScaleFromGlobalAngle
# ------------------------------------------------------------------
def R_ScaleFromGlobalAngle(visangle: int) -> int:
    anglea = (ANG90 + (visangle - viewangle)) & 0xFFFFFFFF
    angleb = (ANG90 + (visangle - rw_normalangle)) & 0xFFFFFFFF

    sinea = finesine[(anglea >> ANGLETOFINESHIFT) & 0x1FFF]
    sineb = finesine[(angleb >> ANGLETOFINESHIFT) & 0x1FFF]
    num   = fixed_mul(projection, sineb) << detailshift
    den   = fixed_mul(rw_distance, sinea)

    if den > (num >> FRACBITS):
        scale = fixed_div(num, den)
        scale = max(256, min(scale, 64 * FRACUNIT))
    else:
        scale = 64 * FRACUNIT

    return scale


# ------------------------------------------------------------------
# R_PointInSubsector
# ------------------------------------------------------------------
def R_PointInSubsector(x: int, y: int):
    from p_setup import nodes, subsectors, numnodes  # type: ignore
    import p_setup

    if not p_setup.nodes:
        return p_setup.subsectors[0]

    nodenum = len(p_setup.nodes) - 1

    while not (nodenum & NF_SUBSECTOR):
        node = p_setup.nodes[nodenum]
        side = R_PointOnSide(x, y, node)
        nodenum = node.children[side]

    return p_setup.subsectors[nodenum & ~NF_SUBSECTOR]


# ------------------------------------------------------------------
# R_InitTextureMapping
# ------------------------------------------------------------------
def R_InitTextureMapping():
    global clipangle, viewangletox, xtoviewangle

    focallength = fixed_div(centerxfrac,
                            finetangent[FINEANGLES // 4 + FIELDOFVIEW // 2])

    half = FINEANGLES // 2
    viewangletox = [0] * half

    for i in range(half):
        ft = finetangent[i]
        if ft > FRACUNIT * 2:
            t = -1
        elif ft < -FRACUNIT * 2:
            t = viewwidth + 1
        else:
            t = fixed_mul(ft, focallength)
            t = (centerxfrac - t + FRACUNIT - 1) >> FRACBITS
            t = max(-1, min(t, viewwidth + 1))
        viewangletox[i] = t

    xtoviewangle = [0] * (viewwidth + 1)
    for x in range(viewwidth + 1):
        i = 0
        while viewangletox[i] > x:
            i += 1
        xtoviewangle[x] = ((i << ANGLETOFINESHIFT) - ANG90) & 0xFFFFFFFF

    # Fix fencepost entries
    for i in range(half):
        if viewangletox[i] == -1:
            viewangletox[i] = 0
        elif viewangletox[i] == viewwidth + 1:
            viewangletox[i] = viewwidth

    clipangle = xtoviewangle[0]


# ------------------------------------------------------------------
# R_InitLightTables
# ------------------------------------------------------------------
def R_InitLightTables():
    for i in range(LIGHTLEVELS):
        startmap = ((LIGHTLEVELS - 1 - i) * 2) * NUMCOLORMAPS // LIGHTLEVELS
        for j in range(MAXLIGHTZ):
            scale = fixed_div(
                (SCREENWIDTH // 2) * FRACUNIT,
                (j + 1) << LIGHTZSHIFT
            ) >> LIGHTSCALESHIFT
            level = startmap - scale // DISTMAP
            level = max(0, min(level, NUMCOLORMAPS - 1))
            zlight[i][j] = level


# ------------------------------------------------------------------
# R_ExecuteSetViewSize
# ------------------------------------------------------------------
def R_ExecuteSetViewSize():
    global setsizeneeded, detailshift
    global viewwidth, viewheight, scaledviewwidth
    global centerx, centery, centerxfrac, centeryfrac, projection
    global pspritescale, pspriteiscale
    global colfunc, basecolfunc, fuzzcolfunc, transcolfunc, spanfunc

    setsizeneeded = False

    if setblocks == 11:
        scaledviewwidth = SCREENWIDTH
        viewheight      = SCREENHEIGHT
    else:
        scaledviewwidth = setblocks * 32
        viewheight      = (setblocks * 168 // 10) & ~7

    detailshift = setdetail
    viewwidth   = scaledviewwidth >> detailshift

    centery      = viewheight  // 2
    centerx      = viewwidth   // 2
    centerxfrac  = centerx << FRACBITS
    centeryfrac  = centery << FRACBITS
    projection   = centerxfrac

    # Import draw functions lazily
    import r_draw
    if not detailshift:
        colfunc = basecolfunc = r_draw.R_DrawColumn
        fuzzcolfunc  = r_draw.R_DrawFuzzColumn
        transcolfunc = r_draw.R_DrawTranslatedColumn
        spanfunc     = r_draw.R_DrawSpan
    else:
        colfunc = basecolfunc = r_draw.R_DrawColumnLow
        fuzzcolfunc  = r_draw.R_DrawFuzzColumnLow
        transcolfunc = r_draw.R_DrawTranslatedColumnLow
        spanfunc     = r_draw.R_DrawSpanLow

    import r_draw as _rd
    _rd.R_InitBuffer(scaledviewwidth, viewheight)

    R_InitTextureMapping()

    pspritescale  = FRACUNIT * viewwidth  // SCREENWIDTH
    pspriteiscale = FRACUNIT * SCREENWIDTH // viewwidth

    for i in range(viewwidth):
        screenheightarray[i] = viewheight

    for i in range(viewheight):
        dy = ((i - viewheight // 2) << FRACBITS) + FRACUNIT // 2
        dy = abs(dy)
        yslope[i] = fixed_div(
            ((viewwidth << detailshift) // 2) * FRACUNIT, dy
        )

    for i in range(viewwidth):
        cosadj = abs(finecosine[(xtoviewangle[i] >> ANGLETOFINESHIFT) & 0x1FFF])
        distscale[i] = fixed_div(FRACUNIT, cosadj)

    # Scale-based lighting
    for i in range(LIGHTLEVELS):
        startmap = ((LIGHTLEVELS - 1 - i) * 2) * NUMCOLORMAPS // LIGHTLEVELS
        for j in range(MAXLIGHTSCALE):
            level = startmap - j * SCREENWIDTH // (viewwidth << detailshift) // DISTMAP
            level = max(0, min(level, NUMCOLORMAPS - 1))
            scalelight[i][j] = level


# ------------------------------------------------------------------
# R_SetViewSize
# ------------------------------------------------------------------
def R_SetViewSize(blocks: int, detail: int):
    global setsizeneeded, setblocks, setdetail
    setsizeneeded = True
    setblocks     = blocks
    setdetail     = detail


# ------------------------------------------------------------------
# R_Init
# ------------------------------------------------------------------
def R_Init():
    global framecount
    from r_data import R_InitData
    R_InitData()

    R_SetViewSize(11, 0)          # full-screen, high detail
    R_ExecuteSetViewSize()

    import r_plane
    r_plane.R_InitPlanes()

    R_InitLightTables()

    import r_sky
    r_sky.R_InitSkyMap()

    import r_things
    r_things.R_InitTranslationTables()

    framecount = 0


# ------------------------------------------------------------------
# R_SetupFrame
# ------------------------------------------------------------------
def R_SetupFrame(player):
    global viewplayer, viewx, viewy, viewangle, extralight
    global viewz, viewsin, viewcos, fixedcolormap, walllights
    global sscount, framecount, validcount

    viewplayer = player
    viewx      = player.mo.x
    viewy      = player.mo.y
    viewangle  = (player.mo.angle + _get_doomstat().viewangleoffset) & 0xFFFFFFFF
    extralight = player.extralight
    viewz      = player.viewz

    fine = (viewangle >> ANGLETOFINESHIFT) & 0x1FFF
    viewsin = finesine[fine]
    viewcos = finecosine[fine]

    sscount = 0

    if player.fixedcolormap:
        fixedcolormap = player.fixedcolormap
        walllights = scalelightfixed
        for i in range(MAXLIGHTSCALE):
            scalelightfixed[i] = fixedcolormap
    else:
        fixedcolormap = 0

    framecount += 1
    validcount += 1


def _get_doomstat():
    import doomstat
    return doomstat


# ------------------------------------------------------------------
# R_RenderPlayerView  — the main render entry point per frame
# ------------------------------------------------------------------
def R_RenderPlayerView(player):
    R_SetupFrame(player)

    import r_bsp
    import r_plane
    import r_things

    r_bsp.R_ClearClipSegs()
    r_bsp.R_ClearDrawSegs()
    r_plane.R_ClearPlanes()
    r_things.R_ClearSprites()

    import p_setup
    r_bsp.R_RenderBSPNode(len(p_setup.nodes) - 1)

    r_plane.R_DrawPlanes()
    r_things.R_DrawMasked()
