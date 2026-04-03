# r_bsp.py
# BSP traversal and seg clipping
# Ported from r_bsp.c / r_bsp.h

from doomdef import (
    SCREENWIDTH, FRACBITS,
    ANG90, ANG180, ANG270,
    NF_SUBSECTOR,
)
from r_defs import (
    DrawSeg, MAXDRAWSEGS,
    SIL_NONE, SIL_BOTTOM, SIL_TOP, SIL_BOTH,
    BOXTOP, BOXBOTTOM, BOXLEFT, BOXRIGHT,
)
from tables import ANGLETOFINESHIFT, ANG45

# ------------------------------------------------------------------
# Shared seg state (read by r_segs.py)
# ------------------------------------------------------------------
curline    = None   # current Seg being processed
sidedef    = None   # curline.sidedef
linedef    = None   # curline.linedef
frontsector = None  # subsector sector
backsector  = None  # seg back sector or None

rw_x:    int = 0
rw_stopx: int = 0
segtextured: bool = False
markfloor:   bool = False
markceiling: bool = False
skymap:      bool = False

# ------------------------------------------------------------------
# DrawSeg pool
# ------------------------------------------------------------------
drawsegs: list = [DrawSeg() for _ in range(MAXDRAWSEGS)]
ds_p: int = 0          # index into drawsegs (next free slot)

# Active floor/ceiling planes (set per subsector)
floorplane   = None
ceilingplane = None


# ------------------------------------------------------------------
# ClipRange — solid seg occlusion list
# ------------------------------------------------------------------
MAXSEGS = SCREENWIDTH // 2 + 1

class _ClipRange:
    __slots__ = ('first', 'last')
    def __init__(self, first=0, last=0):
        self.first = first
        self.last  = last

solidsegs: list = [_ClipRange() for _ in range(MAXSEGS)]
newend: int = 0    # index of one past last valid entry


# ------------------------------------------------------------------
# R_ClearDrawSegs
# ------------------------------------------------------------------
def R_ClearDrawSegs():
    global ds_p
    ds_p = 0


# ------------------------------------------------------------------
# R_ClearClipSegs
# ------------------------------------------------------------------
def R_ClearClipSegs():
    global newend
    import r_main
    solidsegs[0].first = -0x7FFFFFFF
    solidsegs[0].last  = -1
    solidsegs[1].first = r_main.viewwidth
    solidsegs[1].last  = 0x7FFFFFFF
    newend = 2


# ------------------------------------------------------------------
# R_ClipSolidWallSegment
# ------------------------------------------------------------------
def R_ClipSolidWallSegment(first: int, last: int):
    global newend

    # Find first range touching [first, last]
    start = 0
    while solidsegs[start].last < first - 1:
        start += 1

    if first < solidsegs[start].first:
        if last < solidsegs[start].first - 1:
            # Entirely visible — insert new clip post
            R_StoreWallRange(first, last)
            # shift entries up
            nxt = newend
            newend += 1
            while nxt != start:
                solidsegs[nxt].first = solidsegs[nxt - 1].first
                solidsegs[nxt].last  = solidsegs[nxt - 1].last
                nxt -= 1
            solidsegs[start].first = first
            solidsegs[start].last  = last
            return

        # Fragment above start
        R_StoreWallRange(first, solidsegs[start].first - 1)
        solidsegs[start].first = first

    # Bottom contained in start?
    if last <= solidsegs[start].last:
        return

    nxt = start
    while last >= solidsegs[nxt + 1].first - 1:
        R_StoreWallRange(solidsegs[nxt].last + 1, solidsegs[nxt + 1].first - 1)
        nxt += 1
        if last <= solidsegs[nxt].last:
            solidsegs[start].last = solidsegs[nxt].last
            _crunch(start, nxt)
            return

    R_StoreWallRange(solidsegs[nxt].last + 1, last)
    solidsegs[start].last = last
    _crunch(start, nxt)


def _crunch(start: int, nxt: int):
    global newend
    if nxt == start:
        return
    while nxt + 1 < newend:
        nxt += 1
        start += 1
        solidsegs[start].first = solidsegs[nxt].first
        solidsegs[start].last  = solidsegs[nxt].last
    newend = start + 1


# ------------------------------------------------------------------
# R_ClipPassWallSegment
# ------------------------------------------------------------------
def R_ClipPassWallSegment(first: int, last: int):
    start = 0
    while solidsegs[start].last < first - 1:
        start += 1

    if first < solidsegs[start].first:
        if last < solidsegs[start].first - 1:
            R_StoreWallRange(first, last)
            return
        R_StoreWallRange(first, solidsegs[start].first - 1)

    if last <= solidsegs[start].last:
        return

    while last >= solidsegs[start + 1].first - 1:
        R_StoreWallRange(solidsegs[start].last + 1, solidsegs[start + 1].first - 1)
        start += 1
        if last <= solidsegs[start].last:
            return

    R_StoreWallRange(solidsegs[start].last + 1, last)


# ------------------------------------------------------------------
# R_StoreWallRange  — forward-declared; implemented in r_segs.py
# After r_segs is imported it replaces this stub.
# ------------------------------------------------------------------
def R_StoreWallRange(start: int, stop: int):
    raise RuntimeError('R_StoreWallRange not yet initialised — import r_segs first')


# ------------------------------------------------------------------
# R_AddLine
# ------------------------------------------------------------------
def R_AddLine(line):
    global curline, sidedef, linedef, frontsector, backsector
    global rw_angle1

    import r_main

    curline = line

    angle1 = r_main.R_PointToAngle(line.v1.x, line.v1.y)
    angle2 = r_main.R_PointToAngle(line.v2.x, line.v2.y)

    span = (angle1 - angle2) & 0xFFFFFFFF
    if span >= ANG180:
        return   # back face

    rw_angle1 = angle1
    angle1 = (angle1 - r_main.viewangle) & 0xFFFFFFFF
    angle2 = (angle2 - r_main.viewangle) & 0xFFFFFFFF

    tspan = (angle1 + r_main.clipangle) & 0xFFFFFFFF
    clip2 = r_main.clipangle * 2

    if tspan > clip2:
        tspan -= clip2
        if tspan >= span:
            return
        angle1 = r_main.clipangle

    tspan = (r_main.clipangle - angle2) & 0xFFFFFFFF
    if tspan > clip2:
        tspan -= clip2
        if tspan >= span:
            return
        angle2 = (-r_main.clipangle) & 0xFFFFFFFF

    a1 = ((angle1 + ANG90) >> ANGLETOFINESHIFT) & (len(r_main.viewangletox) - 1)
    a2 = ((angle2 + ANG90) >> ANGLETOFINESHIFT) & (len(r_main.viewangletox) - 1)
    x1 = r_main.viewangletox[a1]
    x2 = r_main.viewangletox[a2]

    if x1 == x2:
        return

    backsector = line.backsector

    if not backsector:
        R_ClipSolidWallSegment(x1, x2 - 1)
        return

    if (backsector.ceilingheight <= frontsector.floorheight or
            backsector.floorheight >= frontsector.ceilingheight):
        R_ClipSolidWallSegment(x1, x2 - 1)
        return

    if (backsector.ceilingheight != frontsector.ceilingheight or
            backsector.floorheight != frontsector.floorheight):
        R_ClipPassWallSegment(x1, x2 - 1)
        return

    # Identical floor/ceiling — reject invisible trigger lines
    if (backsector.ceilingpic == frontsector.ceilingpic and
            backsector.floorpic == frontsector.floorpic and
            backsector.lightlevel == frontsector.lightlevel and
            curline.sidedef.midtexture == 0):
        return

    R_ClipPassWallSegment(x1, x2 - 1)


# ------------------------------------------------------------------
# checkcoord table for bbox corner selection
# ------------------------------------------------------------------
_checkcoord = [
    [3, 0, 2, 1],
    [3, 0, 2, 0],
    [3, 1, 2, 0],
    [0, 0, 0, 0],   # unused (boxpos==3)
    [2, 0, 2, 1],
    [0, 0, 0, 0],   # boxpos==5: always visible
    [3, 1, 3, 0],
    [0, 0, 0, 0],   # unused (boxpos==7)
    [2, 0, 3, 1],
    [2, 1, 3, 1],
    [2, 1, 3, 0],
]


# ------------------------------------------------------------------
# R_CheckBBox
# ------------------------------------------------------------------
def R_CheckBBox(bspcoord: list) -> bool:
    import r_main

    # Determine corner quadrant
    if r_main.viewx <= bspcoord[BOXLEFT]:
        boxx = 0
    elif r_main.viewx < bspcoord[BOXRIGHT]:
        boxx = 1
    else:
        boxx = 2

    if r_main.viewy >= bspcoord[BOXTOP]:
        boxy = 0
    elif r_main.viewy > bspcoord[BOXBOTTOM]:
        boxy = 1
    else:
        boxy = 2

    boxpos = (boxy << 2) + boxx
    if boxpos == 5:
        return True

    cc = _checkcoord[boxpos]
    x1 = bspcoord[cc[0]]
    y1 = bspcoord[cc[1]]
    x2 = bspcoord[cc[2]]
    y2 = bspcoord[cc[3]]

    angle1 = (r_main.R_PointToAngle(x1, y1) - r_main.viewangle) & 0xFFFFFFFF
    angle2 = (r_main.R_PointToAngle(x2, y2) - r_main.viewangle) & 0xFFFFFFFF

    span = (angle1 - angle2) & 0xFFFFFFFF
    if span >= ANG180:
        return True

    clip2 = r_main.clipangle * 2
    tspan = (angle1 + r_main.clipangle) & 0xFFFFFFFF
    if tspan > clip2:
        tspan -= clip2
        if tspan >= span:
            return False
        angle1 = r_main.clipangle

    tspan = (r_main.clipangle - angle2) & 0xFFFFFFFF
    if tspan > clip2:
        tspan -= clip2
        if tspan >= span:
            return False
        angle2 = (-r_main.clipangle) & 0xFFFFFFFF

    a1 = ((angle1 + ANG90) >> ANGLETOFINESHIFT) & (len(r_main.viewangletox) - 1)
    a2 = ((angle2 + ANG90) >> ANGLETOFINESHIFT) & (len(r_main.viewangletox) - 1)
    sx1 = r_main.viewangletox[a1]
    sx2 = r_main.viewangletox[a2]

    if sx1 == sx2:
        return False
    sx2 -= 1

    start = 0
    while solidsegs[start].last < sx2:
        start += 1

    if sx1 >= solidsegs[start].first and sx2 <= solidsegs[start].last:
        return False

    return True


# ------------------------------------------------------------------
# R_Subsector
# ------------------------------------------------------------------
def R_Subsector(num: int):
    global frontsector, floorplane, ceilingplane
    import r_main
    import r_plane
    import r_things
    import p_setup
    import doomstat

    sub = p_setup.subsectors[num]
    frontsector = sub.sector

    # Floor plane
    if frontsector.floorheight < r_main.viewz:
        floorplane = r_plane.R_FindPlane(
            frontsector.floorheight,
            frontsector.floorpic,
            frontsector.lightlevel)
    else:
        floorplane = None

    # Ceiling plane
    if (frontsector.ceilingheight > r_main.viewz or
            frontsector.ceilingpic == doomstat.skyflatnum):
        ceilingplane = r_plane.R_FindPlane(
            frontsector.ceilingheight,
            frontsector.ceilingpic,
            frontsector.lightlevel)
    else:
        ceilingplane = None

    r_things.R_AddSprites(frontsector)

    # Process segs
    count = sub.numlines
    seg_idx = sub.firstline
    for _ in range(count):
        R_AddLine(p_setup.segs[seg_idx])
        seg_idx += 1

    if newend > 32:
        raise RuntimeError('R_Subsector: solidsegs overflow')


# ------------------------------------------------------------------
# R_RenderBSPNode
# ------------------------------------------------------------------
def R_RenderBSPNode(bspnum: int):
    import p_setup
    import r_main

    if bspnum & NF_SUBSECTOR:
        idx = 0 if bspnum == 0xFFFFFFFF else (bspnum & ~NF_SUBSECTOR)
        R_Subsector(idx)
        return

    bsp  = p_setup.nodes[bspnum]
    side = r_main.R_PointOnSide(r_main.viewx, r_main.viewy, bsp)

    R_RenderBSPNode(bsp.children[side])

    if R_CheckBBox(bsp.bbox[side ^ 1]):
        R_RenderBSPNode(bsp.children[side ^ 1])
