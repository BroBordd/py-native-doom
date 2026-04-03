import p_ceilng
import p_floor
import p_tick
# p_map.py
# Movement clipping, collision detection, blockmap iteration,
# shooting/aiming/use traces, radius attack, sector change.
# Ported from p_map.c
#
# On import this module patches the stubs in p_mobj.py so that
# P_TryMove, P_CheckPosition, P_AproxDistance, etc. resolve correctly.

from doomdef import (
    FRACBITS, FRACUNIT, ANG90, ANG180,
    fixed_mul, fixed_div,
    MAXRADIUS,
    ML_BLOCKING, ML_BLOCKMONSTERS, ML_TWOSIDED,
    SCREENWIDTH, SCREENHEIGHT,
)
from tables import ANGLETOFINESHIFT, finesine, finecosine
from r_defs import BOXTOP, BOXBOTTOM, BOXLEFT, BOXRIGHT
from p_mobj import (
    MF_SOLID, MF_SPECIAL, MF_SHOOTABLE, MF_NOCLIP,
    MF_MISSILE, MF_SKULLFLY, MF_PICKUP, MF_NOBLOCKMAP,
    MF_NOSECTOR, MF_DROPOFF, MF_FLOAT, MF_TELEPORT,
    MF_CORPSE, MF_DROPPED,
    ONFLOORZ,
)

# ------------------------------------------------------------------
# Blockmap helpers (geometry from p_setup)
# ------------------------------------------------------------------
MAPBLOCKSHIFT = FRACBITS + 7   # 23 — 128 map units per block
MAPBLOCKUNITS = 128
MAXSPECIALCROSS = 20
MAXSPECIALCROSS_ORIGINAL = 8

# ------------------------------------------------------------------
# Global movement state
# ------------------------------------------------------------------
tmbbox   = [0, 0, 0, 0]
tmthing  = None
tmflags  = 0
tmx:     int = 0
tmy:     int = 0
floatok: bool = False

tmfloorz:   int = 0
tmceilingz: int = 0
tmdropoffz: int = 0
ceilingline = None      # Line or None — sky-hack check

spechit:    list = [None] * MAXSPECIALCROSS
numspechit: int  = 0

# Slide move state
bestslidefrac:   int = 0
secondslidefrac: int = 0
bestslideline    = None
secondslideline  = None
slidemo          = None
tmxmove: int = 0
tmymove: int = 0

# Shoot/aim state
linetarget = None
shootthing = None
shootz:     int = 0
la_damage:  int = 0
attackrange:int = 0
aimslope:   int = 0
topslope:   int = 0
bottomslope:int = 0

# Use state
usething = None

# Radius attack state
bombsource = None
bombspot   = None
bombdamage: int = 0

# Sector change state
crushchange: bool = False
nofit:       bool = False

# Path-traverse intercept type flags
PT_ADDLINES  = 1
PT_ADDTHINGS = 2

# ------------------------------------------------------------------
# P_AproxDistance
# ------------------------------------------------------------------
def P_AproxDistance(dx: int, dy: int) -> int:
    dx = abs(dx)
    dy = abs(dy)
    if dx < dy:
        return dx + dy - (dx >> 1)
    return dx + dy - (dy >> 1)


# ------------------------------------------------------------------
# Blockmap cell → actual indices
# ------------------------------------------------------------------
def _blockmap_cell(bx: int, by: int) -> int:
    import p_setup
    if bx < 0 or by < 0 or bx >= p_setup.bmapwidth or by >= p_setup.bmapheight:
        return -1
    return by * p_setup.bmapwidth + bx


# ------------------------------------------------------------------
# P_BlockThingsIterator
# ------------------------------------------------------------------
def P_BlockThingsIterator(x: int, y: int, func) -> bool:
    import p_setup
    cell = _blockmap_cell(x, y)
    if cell < 0:
        return True
    mobj = p_setup.blocklinks[cell]
    while mobj is not None:
        nxt = mobj.bnext
        if not func(mobj):
            return False
        mobj = nxt
    return True


# ------------------------------------------------------------------
# P_BlockLinesIterator
# ------------------------------------------------------------------
def P_BlockLinesIterator(x: int, y: int, func) -> bool:
    import p_setup, r_main
    cell = _blockmap_cell(x, y)
    if cell < 0:
        return True
    for li_idx in p_setup.blockmap[cell]:
        ld = p_setup.lines[li_idx]
        if ld.validcount == r_main.validcount:
            continue
        ld.validcount = r_main.validcount
        if not func(ld):
            return False
    return True


# ------------------------------------------------------------------
# P_SetThingPosition / P_UnsetThingPosition
# ------------------------------------------------------------------
def P_SetThingPosition(mobj):
    import p_setup
    from r_main import R_PointInSubsector

    ss = R_PointInSubsector(mobj.x, mobj.y)
    mobj.subsector = ss

    if not (mobj.flags & MF_NOSECTOR):
        sec = ss.sector
        mobj.sprev = None
        mobj.snext = sec.thinglist
        if sec.thinglist:
            sec.thinglist.sprev = mobj
        sec.thinglist = mobj

    if not (mobj.flags & MF_NOBLOCKMAP):
        bx = (mobj.x - p_setup.bmaporgx) >> MAPBLOCKSHIFT
        by = (mobj.y - p_setup.bmaporgy) >> MAPBLOCKSHIFT
        cell = _blockmap_cell(bx, by)
        if cell >= 0:
            mobj.bprev = None
            mobj.bnext = p_setup.blocklinks[cell]
            if p_setup.blocklinks[cell]:
                p_setup.blocklinks[cell].bprev = mobj
            p_setup.blocklinks[cell] = mobj
        else:
            mobj.bprev = mobj.bnext = None


def P_UnsetThingPosition(mobj):
    import p_setup

    if not (mobj.flags & MF_NOSECTOR):
        if mobj.snext:
            mobj.snext.sprev = mobj.sprev
        if mobj.sprev:
            mobj.sprev.snext = mobj.snext
        else:
            if mobj.subsector and mobj.subsector.sector:
                mobj.subsector.sector.thinglist = mobj.snext

    if not (mobj.flags & MF_NOBLOCKMAP):
        if mobj.bnext:
            mobj.bnext.bprev = mobj.bprev
        if mobj.bprev:
            mobj.bprev.bnext = mobj.bnext
        else:
            bx = (mobj.x - p_setup.bmaporgx) >> MAPBLOCKSHIFT
            by = (mobj.y - p_setup.bmaporgy) >> MAPBLOCKSHIFT
            cell = _blockmap_cell(bx, by)
            if cell >= 0:
                p_setup.blocklinks[cell] = mobj.bnext


# ------------------------------------------------------------------
# P_LineOpening
# ------------------------------------------------------------------
openrange:  int = 0
opentop:    int = 0
openbottom: int = 0
lowfloor:   int = 0

def P_LineOpening(line):
    global openrange, opentop, openbottom, lowfloor

    if line.sidenum[1] == -1:
        # single sided — completely closed
        openrange = 0
        return

    front = line.frontsector
    back  = line.backsector

    if front is None or back is None:
        openrange = 0
        return

    opentop    = min(front.ceilingheight, back.ceilingheight)
    openbottom = max(front.floorheight,   back.floorheight)

    if front.floorheight < back.floorheight:
        lowfloor = back.floorheight
    else:
        lowfloor = front.floorheight

    openrange = opentop - openbottom


# ------------------------------------------------------------------
# P_PointOnLineSide
# ------------------------------------------------------------------
def P_PointOnLineSide(x: int, y: int, line) -> int:
    """0 = front, 1 = back."""
    if not line.dx:
        return 0 if x <= line.v1.x else 1
    if not line.dy:
        return 0 if y <= line.v1.y else 1
    dx = x - line.v1.x
    dy = y - line.v1.y
    left  = fixed_mul(line.dy >> FRACBITS, dx)
    right = fixed_mul(dy,                  line.dx >> FRACBITS)
    return 0 if right < left else 1


# ------------------------------------------------------------------
# P_BoxOnLineSide
# Returns -1 if the box straddles the line (possible collision).
# ------------------------------------------------------------------
def P_BoxOnLineSide(tmbox: list, ld) -> int:
    from r_defs import SlopeType
    stype = ld.slopetype

    if stype == 0:   # HORIZONTAL
        p1 = 1 if tmbox[BOXTOP]    <= ld.v1.y else 0
        p2 = 1 if tmbox[BOXBOTTOM] <= ld.v1.y else 0
    elif stype == 1: # VERTICAL
        p1 = 1 if tmbox[BOXRIGHT]  >= ld.v1.x else 0
        p2 = 1 if tmbox[BOXLEFT]   >= ld.v1.x else 0
    elif stype == 2: # POSITIVE slope
        p1 = P_PointOnLineSide(tmbox[BOXLEFT],  tmbox[BOXTOP],    ld)
        p2 = P_PointOnLineSide(tmbox[BOXRIGHT], tmbox[BOXBOTTOM], ld)
    else:             # NEGATIVE slope
        p1 = P_PointOnLineSide(tmbox[BOXRIGHT], tmbox[BOXTOP],    ld)
        p2 = P_PointOnLineSide(tmbox[BOXLEFT],  tmbox[BOXBOTTOM], ld)

    return p1 if p1 == p2 else -1


# ------------------------------------------------------------------
# PIT_CheckLine
# ------------------------------------------------------------------
def PIT_CheckLine(ld) -> bool:
    global tmfloorz, tmceilingz, tmdropoffz, ceilingline, numspechit

    if (tmbbox[BOXRIGHT]  <= ld.bbox[BOXLEFT]   or
            tmbbox[BOXLEFT]   >= ld.bbox[BOXRIGHT]  or
            tmbbox[BOXTOP]    <= ld.bbox[BOXBOTTOM] or
            tmbbox[BOXBOTTOM] >= ld.bbox[BOXTOP]):
        return True

    if P_BoxOnLineSide(tmbbox, ld) != -1:
        return True

    if not ld.backsector:
        return False   # one-sided

    if not (tmthing.flags & MF_MISSILE):
        if ld.flags & ML_BLOCKING:
            return False
        if not tmthing.player and (ld.flags & ML_BLOCKMONSTERS):
            return False

    P_LineOpening(ld)

    if opentop < tmceilingz:
        tmceilingz = opentop
        ceilingline = ld
    if openbottom > tmfloorz:
        tmfloorz = openbottom
    if lowfloor < tmdropoffz:
        tmdropoffz = lowfloor

    if ld.special:
        if numspechit < MAXSPECIALCROSS:
            spechit[numspechit] = ld
        numspechit += 1

    return True


# ------------------------------------------------------------------
# PIT_CheckThing
# ------------------------------------------------------------------
def PIT_CheckThing(thing) -> bool:
    from p_mobj import P_SetMobjState, P_DamageMobj

    if not (thing.flags & (MF_SOLID | MF_SPECIAL | MF_SHOOTABLE)):
        return True

    blockdist = thing.radius + tmthing.radius
    if (abs(thing.x - tmx) >= blockdist or
            abs(thing.y - tmy) >= blockdist):
        return True

    if thing is tmthing:
        return True

    # skull slam
    if tmthing.flags & MF_SKULLFLY:
        from m_random import P_Random
        damage = ((P_Random() % 8) + 1) * tmthing.info.damage
        P_DamageMobj(thing, tmthing, tmthing, damage)
        tmthing.flags &= ~MF_SKULLFLY
        tmthing.momx = tmthing.momy = tmthing.momz = 0
        P_SetMobjState(tmthing, tmthing.info.spawnstate)
        return False

    # missile collision
    if tmthing.flags & MF_MISSILE:
        if tmthing.z > thing.z + thing.height:
            return True
        if tmthing.z + tmthing.height < thing.z:
            return True
        if tmthing.target:
            import info as info_mod
            tt = tmthing.target.type
            ht = thing.type
            if (tt == ht or
                    (tt == info_mod.MT_KNIGHT  and ht == info_mod.MT_BRUISER) or
                    (tt == info_mod.MT_BRUISER and ht == info_mod.MT_KNIGHT)):
                if thing is tmthing.target:
                    return True
                if thing.type != 0:  # MT_PLAYER=0
                    return False
        if not (thing.flags & MF_SHOOTABLE):
            return not (thing.flags & MF_SOLID)
        from m_random import P_Random
        damage = ((P_Random() % 8) + 1) * tmthing.info.damage
        P_DamageMobj(thing, tmthing, tmthing.target, damage)
        return False

    # pickup
    if thing.flags & MF_SPECIAL:
        solid = bool(thing.flags & MF_SOLID)
        if tmflags & MF_PICKUP:
            P_TouchSpecialThing(thing, tmthing)
        return not solid

    return not (thing.flags & MF_SOLID)


# ------------------------------------------------------------------
# PIT_StompThing
# ------------------------------------------------------------------
def PIT_StompThing(thing) -> bool:
    from p_mobj import P_DamageMobj
    if not (thing.flags & MF_SHOOTABLE):
        return True
    blockdist = thing.radius + tmthing.radius
    if abs(thing.x - tmx) >= blockdist or abs(thing.y - tmy) >= blockdist:
        return True
    if thing is tmthing:
        return True
    import doomstat
    if not tmthing.player and doomstat.gamemap != 30:
        return False
    P_DamageMobj(thing, tmthing, tmthing, 10000)
    return True


# ------------------------------------------------------------------
# P_CheckPosition
# ------------------------------------------------------------------
def P_CheckPosition(thing, x: int, y: int) -> bool:
    global tmthing, tmflags, tmx, tmy, ceilingline
    global tmfloorz, tmceilingz, tmdropoffz, numspechit
    import r_main, p_setup

    tmthing = thing
    tmflags = thing.flags
    tmx = x
    tmy = y

    tmbbox[BOXTOP]    = y + thing.radius
    tmbbox[BOXBOTTOM] = y - thing.radius
    tmbbox[BOXRIGHT]  = x + thing.radius
    tmbbox[BOXLEFT]   = x - thing.radius

    newsubsec = r_main.R_PointInSubsector(x, y)
    ceilingline = None

    tmfloorz   = tmdropoffz = newsubsec.sector.floorheight
    tmceilingz = newsubsec.sector.ceilingheight

    r_main.validcount += 1
    numspechit = 0

    if tmflags & MF_NOCLIP:
        return True

    xl = (tmbbox[BOXLEFT]   - p_setup.bmaporgx - MAXRADIUS) >> MAPBLOCKSHIFT
    xh = (tmbbox[BOXRIGHT]  - p_setup.bmaporgx + MAXRADIUS) >> MAPBLOCKSHIFT
    yl = (tmbbox[BOXBOTTOM] - p_setup.bmaporgy - MAXRADIUS) >> MAPBLOCKSHIFT
    yh = (tmbbox[BOXTOP]    - p_setup.bmaporgy + MAXRADIUS) >> MAPBLOCKSHIFT

    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not P_BlockThingsIterator(bx, by, PIT_CheckThing):
                return False

    xl = (tmbbox[BOXLEFT]   - p_setup.bmaporgx) >> MAPBLOCKSHIFT
    xh = (tmbbox[BOXRIGHT]  - p_setup.bmaporgx) >> MAPBLOCKSHIFT
    yl = (tmbbox[BOXBOTTOM] - p_setup.bmaporgy) >> MAPBLOCKSHIFT
    yh = (tmbbox[BOXTOP]    - p_setup.bmaporgy) >> MAPBLOCKSHIFT

    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not P_BlockLinesIterator(bx, by, PIT_CheckLine):
                return False

    return True


# ------------------------------------------------------------------
# P_TryMove
# ------------------------------------------------------------------
def P_TryMove(thing, x: int, y: int) -> bool:
    global floatok
    import p_setup

    floatok = False
    if not P_CheckPosition(thing, x, y):
        return False

    if not (thing.flags & MF_NOCLIP):
        if tmceilingz - tmfloorz < thing.height:
            return False
        floatok = True
        if not (thing.flags & MF_TELEPORT) and tmceilingz - thing.z < thing.height:
            return False
        if not (thing.flags & MF_TELEPORT) and tmfloorz - thing.z > 24 * FRACUNIT:
            return False
        if not (thing.flags & (MF_DROPOFF | MF_FLOAT)) and tmfloorz - tmdropoffz > 24 * FRACUNIT:
            return False

    P_UnsetThingPosition(thing)
    oldx = thing.x
    oldy = thing.y
    thing.floorz   = tmfloorz
    thing.ceilingz = tmceilingz
    thing.x = x
    thing.y = y
    P_SetThingPosition(thing)

    if not (thing.flags & (MF_TELEPORT | MF_NOCLIP)):
        i = numspechit
        while i > 0:
            i -= 1
            ld = spechit[i]
            side    = P_PointOnLineSide(thing.x, thing.y, ld)
            oldside = P_PointOnLineSide(oldx,    oldy,    ld)
            if side != oldside and ld.special:
                _cross_special_line(p_setup.lines.index(ld), oldside, thing)

    return True


# ------------------------------------------------------------------
# P_TeleportMove
# ------------------------------------------------------------------
def P_TeleportMove(thing, x: int, y: int) -> bool:
    global tmthing, tmflags, tmx, tmy
    import p_setup, r_main

    tmthing = thing
    tmflags = thing.flags
    tmx = x
    tmy = y

    tmbbox[BOXTOP]    = y + thing.radius
    tmbbox[BOXBOTTOM] = y - thing.radius
    tmbbox[BOXRIGHT]  = x + thing.radius
    tmbbox[BOXLEFT]   = x - thing.radius

    newsubsec = r_main.R_PointInSubsector(x, y)
    global ceilingline, tmfloorz, tmceilingz, tmdropoffz, numspechit
    ceilingline = None
    tmfloorz = tmdropoffz = newsubsec.sector.floorheight
    tmceilingz = newsubsec.sector.ceilingheight
    r_main.validcount += 1
    numspechit = 0

    xl = (tmbbox[BOXLEFT]   - p_setup.bmaporgx - MAXRADIUS) >> MAPBLOCKSHIFT
    xh = (tmbbox[BOXRIGHT]  - p_setup.bmaporgx + MAXRADIUS) >> MAPBLOCKSHIFT
    yl = (tmbbox[BOXBOTTOM] - p_setup.bmaporgy - MAXRADIUS) >> MAPBLOCKSHIFT
    yh = (tmbbox[BOXTOP]    - p_setup.bmaporgy + MAXRADIUS) >> MAPBLOCKSHIFT

    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not P_BlockThingsIterator(bx, by, PIT_StompThing):
                return False

    P_UnsetThingPosition(thing)
    thing.floorz   = tmfloorz
    thing.ceilingz = tmceilingz
    thing.x = x
    thing.y = y
    P_SetThingPosition(thing)
    return True


# ------------------------------------------------------------------
# P_ThingHeightClip
# ------------------------------------------------------------------
def P_ThingHeightClip(thing) -> bool:
    onfloor = (thing.z == thing.floorz)
    P_CheckPosition(thing, thing.x, thing.y)
    thing.floorz   = tmfloorz
    thing.ceilingz = tmceilingz
    if onfloor:
        thing.z = thing.floorz
    else:
        if thing.z + thing.height > thing.ceilingz:
            thing.z = thing.ceilingz - thing.height
    if thing.ceilingz - thing.floorz < thing.height:
        return False
    return True


# ------------------------------------------------------------------
# P_HitSlideLine / P_SlideMove
# ------------------------------------------------------------------
def P_HitSlideLine(ld):
    global tmxmove, tmymove
    from r_defs import SlopeType

    if ld.slopetype == SlopeType.HORIZONTAL:
        tmymove = 0;  return
    if ld.slopetype == SlopeType.VERTICAL:
        tmxmove = 0;  return

    side = P_PointOnLineSide(slidemo.x, slidemo.y, ld)
    lineangle = _r_point_to_angle2(0, 0, ld.dx, ld.dy)
    if side == 1:
        lineangle = (lineangle + ANG180) & 0xFFFFFFFF
    moveangle  = _r_point_to_angle2(0, 0, tmxmove, tmymove)
    deltaangle = (moveangle - lineangle) & 0xFFFFFFFF
    if deltaangle > ANG180:
        deltaangle = (deltaangle + ANG180) & 0xFFFFFFFF

    la = (lineangle  >> ANGLETOFINESHIFT) & 0x1FFF
    da = (deltaangle >> ANGLETOFINESHIFT) & 0x1FFF
    movelen = P_AproxDistance(tmxmove, tmymove)
    newlen   = fixed_mul(movelen, finecosine[da])
    tmxmove  = fixed_mul(newlen,  finecosine[la])
    tmymove  = fixed_mul(newlen,  finesine[la])


def _r_point_to_angle2(x1, y1, x2, y2):
    from r_main import R_PointToAngle2
    return R_PointToAngle2(x1, y1, x2, y2)


def P_SlideMove(mo):
    global slidemo, bestslidefrac, secondslidefrac
    global bestslideline, secondslideline, tmxmove, tmymove

    slidemo  = mo
    hitcount = 0

    while True:
        hitcount += 1
        if hitcount == 3:
            # stairstep
            if not P_TryMove(mo, mo.x, mo.y + mo.momy):
                P_TryMove(mo, mo.x + mo.momx, mo.y)
            return

        bestslidefrac = FRACUNIT + 1

        P_PathTraverse(mo.x + mo.radius, mo.y + mo.radius,
                       mo.x + mo.radius + mo.momx, mo.y + mo.radius + mo.momy,
                       PT_ADDLINES, _ptr_slide_traverse)
        P_PathTraverse(mo.x - mo.radius, mo.y + mo.radius,
                       mo.x - mo.radius + mo.momx, mo.y + mo.radius + mo.momy,
                       PT_ADDLINES, _ptr_slide_traverse)
        P_PathTraverse(mo.x + mo.radius, mo.y - mo.radius,
                       mo.x + mo.radius + mo.momx, mo.y - mo.radius + mo.momy,
                       PT_ADDLINES, _ptr_slide_traverse)

        if bestslidefrac == FRACUNIT + 1:
            if not P_TryMove(mo, mo.x, mo.y + mo.momy):
                P_TryMove(mo, mo.x + mo.momx, mo.y)
            return

        bsf = bestslidefrac - 0x800
        if bsf > 0:
            newx = fixed_mul(mo.momx, bsf)
            newy = fixed_mul(mo.momy, bsf)
            if not P_TryMove(mo, mo.x + newx, mo.y + newy):
                # stairstep
                if not P_TryMove(mo, mo.x, mo.y + mo.momy):
                    P_TryMove(mo, mo.x + mo.momx, mo.y)
                return

        bsf2 = FRACUNIT - (bsf + 0x800)
        if bsf2 > FRACUNIT:
            bsf2 = FRACUNIT
        if bsf2 <= 0:
            return

        tmxmove = fixed_mul(mo.momx, bsf2)
        tmymove = fixed_mul(mo.momy, bsf2)
        P_HitSlideLine(bestslideline)
        mo.momx = tmxmove
        mo.momy = tmymove
        if P_TryMove(mo, mo.x + tmxmove, mo.y + tmymove):
            return
        # retry


class _Intercept:
    __slots__ = ('frac', 'isaline', 'd')
    def __init__(self, frac, isaline, d):
        self.frac    = frac
        self.isaline = isaline
        self.d       = d


def _ptr_slide_traverse(intercept) -> bool:
    global bestslidefrac, secondslidefrac, bestslideline, secondslideline
    li = intercept.d
    if not (li.flags & ML_TWOSIDED):
        if P_PointOnLineSide(slidemo.x, slidemo.y, li):
            return True
        # blocking
    else:
        P_LineOpening(li)
        if openrange < slidemo.height:
            pass
        elif opentop - slidemo.z < slidemo.height:
            pass
        elif openbottom - slidemo.z > 24 * FRACUNIT:
            pass
        else:
            return True  # doesn't block

    if intercept.frac < bestslidefrac:
        secondslidefrac = bestslidefrac
        secondslideline = bestslideline
        bestslidefrac   = intercept.frac
        bestslideline   = li
    return False


# ------------------------------------------------------------------
# P_PathTraverse  — DDA ray-march through blockmap
# ------------------------------------------------------------------

class _DivLine:
    __slots__ = ('x', 'y', 'dx', 'dy')
    def __init__(self, x=0, y=0, dx=0, dy=0):
        self.x = x; self.y = y; self.dx = dx; self.dy = dy

trace = _DivLine()

_intercepts: list = []


def _intercept_vector(v2: _DivLine, v1: _DivLine) -> int:
    """Fraction along v2 where it intersects v1."""
    den = fixed_mul(v1.dy >> FRACBITS, v2.dx) - fixed_mul(v1.dx >> FRACBITS, v2.dy)
    if den == 0:
        return 0
    num = fixed_mul((v1.x - v2.x) >> FRACBITS, v1.dy) + \
          fixed_mul((v2.y - v1.y) >> FRACBITS, v1.dx)
    return fixed_div(num, den)


def _add_line_intercepts(x: int, y: int, func) -> bool:
    import p_setup, r_main
    cell = _blockmap_cell(x, y)
    if cell < 0:
        return True
    for li_idx in p_setup.blockmap[cell]:
        ld = p_setup.lines[li_idx]
        if ld.validcount == r_main.validcount:
            continue
        ld.validcount = r_main.validcount

        s1 = P_PointOnLineSide(trace.x, trace.y, ld)
        s2 = P_PointOnLineSide(trace.x + trace.dx, trace.y + trace.dy, ld)
        if s1 == s2:
            continue   # line not crossed

        divl = _DivLine()
        divl.x  = ld.v1.x
        divl.y  = ld.v1.y
        divl.dx = ld.dx
        divl.dy = ld.dy
        frac = _intercept_vector(trace, divl)

        # Check sides
        s3 = _point_on_divline_side(ld.v1.x, ld.v1.y, trace)
        s4 = _point_on_divline_side(ld.v2.x, ld.v2.y, trace)
        if s3 == s4:
            continue

        _intercepts.append(_Intercept(frac, True, ld))
    return True


def _add_thing_intercepts(x: int, y: int) -> bool:
    import p_setup
    cell = _blockmap_cell(x, y)
    if cell < 0:
        return True
    mobj = p_setup.blocklinks[cell]
    while mobj:
        nxt = mobj.bnext
        s1 = _point_on_divline_side(mobj.x, mobj.y, trace)
        trx = mobj.x + mobj.radius
        try_ = mobj.y + mobj.radius
        s2 = _point_on_divline_side(trx, try_, trace)
        if s1 != s2:
            s3 = P_PointOnLineSide(trace.x, trace.y,
                                   _fake_line(mobj.x - mobj.radius, mobj.y,
                                              mobj.x + mobj.radius, mobj.y))
            frac = _intercept_vector(trace, _DivLine(
                mobj.x, mobj.y - mobj.radius, 0, mobj.radius * 2))
            _intercepts.append(_Intercept(frac, False, mobj))
        mobj = nxt
    return True


def _point_on_divline_side(x: int, y: int, dl: _DivLine) -> int:
    if not dl.dx:
        return 0 if x <= dl.x else 1
    if not dl.dy:
        return 0 if y <= dl.y else 1
    dx = (x - dl.x) >> FRACBITS
    dy = (y - dl.y) >> FRACBITS
    left  = (dl.dy >> FRACBITS) * dx
    right = dy * (dl.dx >> FRACBITS)
    return 1 if right <= left else 0


def _fake_line(x1, y1, x2, y2):
    """Minimal line-like object for _point_on_divline_side."""
    class _FL:
        pass
    fl = _FL()
    fl.dx = x2 - x1; fl.dy = y2 - y1
    class _V: pass
    fl.v1 = _V(); fl.v1.x = x1; fl.v1.y = y1
    fl.v2 = _V(); fl.v2.x = x2; fl.v2.y = y2
    return fl


def P_PathTraverse(x1: int, y1: int, x2: int, y2: int, flags: int, trav) -> bool:
    import p_setup, r_main
    global _intercepts

    _intercepts = []

    trace.x  = x1
    trace.y  = y1
    trace.dx = x2 - x1
    trace.dy = y2 - y1

    x1 -= p_setup.bmaporgx
    y1 -= p_setup.bmaporgy

    bx1 = x1 >> MAPBLOCKSHIFT
    by1 = y1 >> MAPBLOCKSHIFT
    x2 -= p_setup.bmaporgx
    y2 -= p_setup.bmaporgy
    bx2 = x2 >> MAPBLOCKSHIFT
    by2 = y2 >> MAPBLOCKSHIFT

    # Simple DDA march through blockmap cells
    r_main.validcount += 1

    xs = 1 if bx2 >= bx1 else -1
    ys = 1 if by2 >= by1 else -1

    bx = bx1
    by = by1
    steps = abs(bx2 - bx1) + abs(by2 - by1) + 1
    for _ in range(steps):
        if flags & PT_ADDLINES:
            _add_line_intercepts(bx, by, trav)
        if flags & PT_ADDTHINGS:
            _add_thing_intercepts(bx, by)
        # advance DDA
        if abs(bx2 - bx) > abs(by2 - by):
            bx += xs
        else:
            by += ys

    # Sort intercepts by frac and call traversal function
    _intercepts.sort(key=lambda i: i.frac)
    for ic in _intercepts:
        if ic.frac > FRACUNIT:
            break
        if not trav(ic):
            return False
    return True


# ------------------------------------------------------------------
# PTR_AimTraverse / P_AimLineAttack
# ------------------------------------------------------------------
def PTR_AimTraverse(intercept) -> bool:
    global topslope, bottomslope, aimslope, linetarget

    if intercept.isaline:
        li = intercept.d
        if not (li.flags & ML_TWOSIDED):
            return False
        P_LineOpening(li)
        if openbottom >= opentop:
            return False
        dist = fixed_mul(attackrange, intercept.frac)
        if li.backsector is None or li.frontsector.floorheight != li.backsector.floorheight:
            slope = fixed_div(openbottom - shootz, dist)
            if slope > bottomslope:
                bottomslope = slope
        if li.backsector is None or li.frontsector.ceilingheight != li.backsector.ceilingheight:
            slope = fixed_div(opentop - shootz, dist)
            if slope < topslope:
                topslope = slope
        if topslope <= bottomslope:
            return False
        return True

    th = intercept.d
    if th is shootthing:
        return True
    if not (th.flags & MF_SHOOTABLE):
        return True

    dist = fixed_mul(attackrange, intercept.frac)
    thingtopslope    = fixed_div(th.z + th.height - shootz, dist)
    thingbottomslope = fixed_div(th.z - shootz, dist)

    if thingtopslope < bottomslope:
        return True
    if thingbottomslope > topslope:
        return True

    aimslope   = (thingtopslope + thingbottomslope) // 2
    linetarget = th
    return False


def P_AimLineAttack(t1, angle: int, distance: int) -> int:
    global shootthing, shootz, topslope, bottomslope, attackrange, linetarget
    from p_mobj import P_SubstNullMobj

    t1 = P_SubstNullMobj(t1)
    fine = (angle >> ANGLETOFINESHIFT) & 0x1FFF
    shootthing  = t1
    x2 = t1.x + (distance >> FRACBITS) * finecosine[fine]
    y2 = t1.y + (distance >> FRACBITS) * finesine[fine]
    shootz      = t1.z + (t1.height >> 1) + 8 * FRACUNIT
    topslope    =  (SCREENHEIGHT // 2) * FRACUNIT // (SCREENWIDTH // 2)
    bottomslope = -(SCREENHEIGHT // 2) * FRACUNIT // (SCREENWIDTH // 2)
    attackrange = distance
    linetarget  = None

    P_PathTraverse(t1.x, t1.y, x2, y2,
                   PT_ADDLINES | PT_ADDTHINGS,
                   PTR_AimTraverse)
    return aimslope if linetarget else 0


# ------------------------------------------------------------------
# PTR_ShootTraverse / P_LineAttack
# ------------------------------------------------------------------
def PTR_ShootTraverse(intercept) -> bool:
    import doomstat
    from p_mobj import P_SpawnPuff, P_SpawnBlood, P_DamageMobj

    if intercept.isaline:
        li = intercept.d
        if li.special:
            _shoot_special_line(shootthing, li)
        if not (li.flags & ML_TWOSIDED):
            _hitline(intercept, li)
            return False
        P_LineOpening(li)
        dist = fixed_mul(attackrange, intercept.frac)
        if li.backsector is None:
            slope = fixed_div(openbottom - shootz, dist)
            if slope > aimslope:
                _hitline(intercept, li)
                return False
            slope = fixed_div(opentop - shootz, dist)
            if slope < aimslope:
                _hitline(intercept, li)
                return False
        else:
            if li.frontsector.floorheight != li.backsector.floorheight:
                slope = fixed_div(openbottom - shootz, dist)
                if slope > aimslope:
                    _hitline(intercept, li)
                    return False
            if li.frontsector.ceilingheight != li.backsector.ceilingheight:
                slope = fixed_div(opentop - shootz, dist)
                if slope < aimslope:
                    _hitline(intercept, li)
                    return False
        return True

    th = intercept.d
    if th is shootthing:
        return True
    if not (th.flags & MF_SHOOTABLE):
        return True

    dist             = fixed_mul(attackrange, intercept.frac)
    thingtopslope    = fixed_div(th.z + th.height - shootz, dist)
    thingbottomslope = fixed_div(th.z - shootz, dist)
    if thingtopslope < aimslope:
        return True
    if thingbottomslope > aimslope:
        return True

    frac = intercept.frac - fixed_div(10 * FRACUNIT, attackrange)
    x = trace.x + fixed_mul(trace.dx, frac)
    y = trace.y + fixed_mul(trace.dy, frac)
    z = shootz  + fixed_mul(aimslope, fixed_mul(frac, attackrange))

    if th.flags & MF_NOBLOOD:
        P_SpawnPuff(x, y, z)
    else:
        P_SpawnBlood(x, y, z, la_damage)

    if la_damage:
        P_DamageMobj(th, shootthing, shootthing, la_damage)
    return False


def _hitline(intercept, li):
    from p_mobj import P_SpawnPuff
    import doomstat
    frac = intercept.frac - fixed_div(4 * FRACUNIT, attackrange)
    x = trace.x + fixed_mul(trace.dx, frac)
    y = trace.y + fixed_mul(trace.dy, frac)
    z = shootz  + fixed_mul(aimslope, fixed_mul(frac, attackrange))
    if li.frontsector.ceilingpic == doomstat.skyflatnum:
        if z > li.frontsector.ceilingheight:
            return
        if li.backsector and li.backsector.ceilingpic == doomstat.skyflatnum:
            return
    P_SpawnPuff(x, y, z)


def P_LineAttack(t1, angle: int, distance: int, slope: int, damage: int):
    global shootthing, la_damage, shootz, attackrange, aimslope
    fine = (angle >> ANGLETOFINESHIFT) & 0x1FFF
    shootthing  = t1
    la_damage   = damage
    x2 = t1.x + (distance >> FRACBITS) * finecosine[fine]
    y2 = t1.y + (distance >> FRACBITS) * finesine[fine]
    shootz      = t1.z + (t1.height >> 1) + 8 * FRACUNIT
    attackrange = distance
    aimslope    = slope
    P_PathTraverse(t1.x, t1.y, x2, y2,
                   PT_ADDLINES | PT_ADDTHINGS,
                   PTR_ShootTraverse)


# ------------------------------------------------------------------
# P_UseLines
# ------------------------------------------------------------------
def _ptr_use_traverse(intercept) -> bool:
    global usething
    import info as info_mod
    li = intercept.d
    if not li.special:
        P_LineOpening(li)
        if openrange <= 0:
            _play_sound_noway(usething)
            return False
        return True
    side = 0
    if P_PointOnLineSide(usething.x, usething.y, li) == 1:
        side = 1
    _use_special_line(usething, li, side)
    return False


def P_UseLines(player):
    global usething
    usething = player.mo
    fine = (player.mo.angle >> ANGLETOFINESHIFT) & 0x1FFF
    USERANGE = 64 * FRACUNIT
    x1 = player.mo.x
    y1 = player.mo.y
    x2 = x1 + (USERANGE >> FRACBITS) * finecosine[fine]
    y2 = y1 + (USERANGE >> FRACBITS) * finesine[fine]
    P_PathTraverse(x1, y1, x2, y2, PT_ADDLINES, _ptr_use_traverse)


# ------------------------------------------------------------------
# PIT_RadiusAttack / P_RadiusAttack
# ------------------------------------------------------------------
def PIT_RadiusAttack(thing) -> bool:
    from p_mobj import P_DamageMobj
    if not (thing.flags & MF_SHOOTABLE):
        return True
    import info as info_mod
    if thing.type in (info_mod.MT_CYBORG, info_mod.MT_SPIDER):
        return True
    dx   = abs(thing.x - bombspot.x)
    dy   = abs(thing.y - bombspot.y)
    dist = (max(dx, dy) - thing.radius) >> FRACBITS
    if dist < 0:
        dist = 0
    if dist >= bombdamage:
        return True
    if P_CheckSight(thing, bombspot):
        P_DamageMobj(thing, bombspot, bombsource, bombdamage - dist)
    return True


def P_RadiusAttack(spot, source, damage: int):
    global bombspot, bombsource, bombdamage
    import p_setup
    bombspot   = spot
    bombsource = source
    bombdamage = damage

    dist = (damage + MAXRADIUS) << FRACBITS
    yh = (spot.y + dist - p_setup.bmaporgy) >> MAPBLOCKSHIFT
    yl = (spot.y - dist - p_setup.bmaporgy) >> MAPBLOCKSHIFT
    xh = (spot.x + dist - p_setup.bmaporgx) >> MAPBLOCKSHIFT
    xl = (spot.x - dist - p_setup.bmaporgx) >> MAPBLOCKSHIFT

    for y in range(yl, yh + 1):
        for x in range(xl, xh + 1):
            P_BlockThingsIterator(x, y, PIT_RadiusAttack)


# ------------------------------------------------------------------
# P_ChangeSector
# ------------------------------------------------------------------
def PIT_ChangeSector(thing) -> bool:
    global nofit
    from p_mobj import P_SetMobjState, P_RemoveMobj, P_DamageMobj, P_SpawnMobj
    import info as info_mod
    from doomdef import GameVersion
    import doomstat

    if P_ThingHeightClip(thing):
        return True

    if thing.health <= 0:
        P_SetMobjState(thing, info_mod.S_GIBS)
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7:
            thing.flags &= ~MF_SOLID
        thing.height = thing.radius = 0
        return True

    if thing.flags & MF_DROPPED:
        P_RemoveMobj(thing)
        return True

    if not (thing.flags & MF_SHOOTABLE):
        return True

    nofit = True
    if crushchange and not (doomstat.leveltime & 3):
        P_DamageMobj(thing, None, None, 10)
        from m_random import P_Random
        mo = P_SpawnMobj(thing.x, thing.y,
                         thing.z + thing.height // 2,
                         info_mod.MT_BLOOD)
        mo.momx = (P_Random() - P_Random()) << 12
        mo.momy = (P_Random() - P_Random()) << 12
    return True


def P_ChangeSector(sector, crunch: bool) -> bool:
    global nofit, crushchange
    import p_setup
    nofit       = False
    crushchange = crunch
    for x in range(sector.blockbox[BOXLEFT], sector.blockbox[BOXRIGHT] + 1):
        for y in range(sector.blockbox[BOXBOTTOM], sector.blockbox[BOXTOP] + 1):
            P_BlockThingsIterator(x, y, PIT_ChangeSector)
    return nofit


# ------------------------------------------------------------------
# P_CheckSight  — simplified LOS (no reject table traversal here,
# real implementation needs p_sight.c which we stub for now)
# ------------------------------------------------------------------
def P_CheckSight(t1, t2) -> bool:
    """Simplified sight check — always returns True for now.
    p_sight.py will override this when implemented."""
    return True


# ------------------------------------------------------------------
# Stub callbacks for specials (filled in by p_spec.py)
# ------------------------------------------------------------------
def _cross_special_line(lineno: int, side: int, thing):
    try:
        import p_spec
        p_spec.P_CrossSpecialLine(lineno, side, thing)
    except (ImportError, AttributeError):
        pass


def _use_special_line(thing, line, side: int):
    try:
        import p_spec
        p_spec.P_UseSpecialLine(thing, line, side)
    except (ImportError, AttributeError):
        pass


def _shoot_special_line(thing, line):
    try:
        import p_spec
        p_spec.P_ShootSpecialLine(thing, line)
    except (ImportError, AttributeError):
        pass


def _play_sound_noway(mobj):
    try:
        from p_mobj import S_StartSound
        import info as info_mod
        S_StartSound(mobj, info_mod.sfx_noway)
    except Exception:
        pass


# ------------------------------------------------------------------
# P_SubRandom  (used in p_mobj for random-direction effects)
# ------------------------------------------------------------------
def P_SubRandom() -> int:
    from m_random import P_Random
    return P_Random() - P_Random()


# ------------------------------------------------------------------
# Patch p_mobj stubs
# ------------------------------------------------------------------
import p_mobj as _pm
_pm.P_TryMove             = P_TryMove
_pm.P_SlideMove           = P_SlideMove
_pm.P_CheckPosition       = P_CheckPosition
_pm.P_AproxDistance       = P_AproxDistance
_pm.P_AimLineAttack       = P_AimLineAttack
_pm.P_SetThingPosition    = P_SetThingPosition
_pm.P_UnsetThingPosition  = P_UnsetThingPosition

from r_main import R_PointInSubsector as _rpi
_pm.R_PointInSubsector    = _rpi
from r_main import R_PointToAngle2 as _rpa
_pm.R_PointToAngle2       = _rpa

# Also expose P_SubRandom through the module for p_mobj use
import p_mobj as _pm2
_pm2.P_SubRandom = P_SubRandom

# expose P_TouchSpecialThing (filled by p_inter)
def _touch_special_stub(special, toucher):
    try:
        import p_inter
        p_inter.P_TouchSpecialThing(special, toucher)
    except (ImportError, AttributeError):
        pass

P_TouchSpecialThing = _touch_special_stub
