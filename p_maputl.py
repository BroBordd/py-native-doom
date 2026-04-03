import p_ceilng
import p_floor
import p_tick
import p_spec
#
# Copyright(C) 1993-1996 Id Software, Inc.
# Copyright(C) 2005-2014 Simon Howard
# Copyright(C) 2005, 2006 Andrey Budko
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# DESCRIPTION:
#	Movement/collision utility functions,
#	as used by function in p_map.c. 
#	BLOCKMAP Iterator functions,
#	and some PIT_* functions to use for iteration.
#

import sys
import doomdef
import doomstat
import p_local
import m_bbox

# Helper classes
class divline_t:
    def __init__(self, x=0, y=0, dx=0, dy=0):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy

class intercept_t:
    def __init__(self):
        self.frac = 0
        self.isaline = False
        self.d_line = None
        self.d_thing = None

# Math functions
def FixedMul(a, b):
    # Emulate fixed point multiplication
    return int((a * b) / 65536)

def FixedDiv(a, b):
    if b == 0:
        return 0
    return int((a * 65536) / b)

# Globals
opentop = 0
openbottom = 0
openrange = 0
lowfloor = 0

MAXINTERCEPTS = 128
MAXINTERCEPTS_ORIGINAL = 128
intercepts = [intercept_t() for _ in range(MAXINTERCEPTS)]
intercept_p = 0

trace = divline_t()
earlyout = False
ptflags = 0

FRACBITS = doomdef.FRACBITS
FRACUNIT = doomdef.FRACUNIT


def P_AproxDistance(dx, dy):
    dx = abs(dx)
    dy = abs(dy)
    if dx < dy:
        return dx + dy - (dx >> 1)
    return dx + dy - (dy >> 1)


def P_PointOnLineSide(x, y, line):
    if not line.dx:
        if x <= line.v1.x:
            return 1 if line.dy > 0 else 0
        return 1 if line.dy < 0 else 0
        
    if not line.dy:
        if y <= line.v1.y:
            return 1 if line.dx < 0 else 0
        return 1 if line.dx > 0 else 0
        
    dx = x - line.v1.x
    dy = y - line.v1.y
    
    left = FixedMul(line.dy >> FRACBITS, dx)
    right = FixedMul(dy, line.dx >> FRACBITS)
    
    if right < left:
        return 0    # front side
    return 1        # back side


def P_BoxOnLineSide(tmbox, ld):
    p1 = 0
    p2 = 0
    
    if ld.slopetype == doomdef.ST_HORIZONTAL:
        p1 = 1 if tmbox[m_bbox.BOXTOP] > ld.v1.y else 0
        p2 = 1 if tmbox[m_bbox.BOXBOTTOM] > ld.v1.y else 0
        if ld.dx < 0:
            p1 ^= 1
            p2 ^= 1
            
    elif ld.slopetype == doomdef.ST_VERTICAL:
        p1 = 1 if tmbox[m_bbox.BOXRIGHT] < ld.v1.x else 0
        p2 = 1 if tmbox[m_bbox.BOXLEFT] < ld.v1.x else 0
        if ld.dy < 0:
            p1 ^= 1
            p2 ^= 1
            
    elif ld.slopetype == doomdef.ST_POSITIVE:
        p1 = P_PointOnLineSide(tmbox[m_bbox.BOXLEFT], tmbox[m_bbox.BOXTOP], ld)
        p2 = P_PointOnLineSide(tmbox[m_bbox.BOXRIGHT], tmbox[m_bbox.BOXBOTTOM], ld)
        
    elif ld.slopetype == doomdef.ST_NEGATIVE:
        p1 = P_PointOnLineSide(tmbox[m_bbox.BOXRIGHT], tmbox[m_bbox.BOXTOP], ld)
        p2 = P_PointOnLineSide(tmbox[m_bbox.BOXLEFT], tmbox[m_bbox.BOXBOTTOM], ld)

    if p1 == p2:
        return p1
    return -1


def P_PointOnDivlineSide(x, y, line):
    if not line.dx:
        if x <= line.x:
            return 1 if line.dy > 0 else 0
        return 1 if line.dy < 0 else 0
        
    if not line.dy:
        if y <= line.y:
            return 1 if line.dx < 0 else 0
        return 1 if line.dx > 0 else 0
        
    dx = x - line.x
    dy = y - line.y
    
    # try to quickly decide by looking at sign bits
    if (line.dy ^ line.dx ^ dx ^ dy) & 0x80000000:
        if (line.dy ^ dx) & 0x80000000:
            return 1        # (left is negative)
        return 0
        
    left = FixedMul(line.dy >> 8, dx >> 8)
    right = FixedMul(dy >> 8, line.dx >> 8)
    
    if right < left:
        return 0        # front side
    return 1            # back side


def P_MakeDivline(li, dl):
    dl.x = li.v1.x
    dl.y = li.v1.y
    dl.dx = li.dx
    dl.dy = li.dy


def P_InterceptVector(v2, v1):
    den = FixedMul(v1.dy >> 8, v2.dx) - FixedMul(v1.dx >> 8, v2.dy)

    if den == 0:
        return 0
    
    num = FixedMul((v1.x - v2.x) >> 8, v1.dy) + FixedMul((v2.y - v1.y) >> 8, v1.dx)
    frac = FixedDiv(num, den)

    return frac


def P_LineOpening(linedef):
    global opentop, openbottom, openrange, lowfloor
    
    if linedef.sidenum[1] == -1:
        # single sided line
        openrange = 0
        return
        
    front = linedef.frontsector
    back = linedef.backsector
    
    if front.ceilingheight < back.ceilingheight:
        opentop = front.ceilingheight
    else:
        opentop = back.ceilingheight

    if front.floorheight > back.floorheight:
        openbottom = front.floorheight
        lowfloor = back.floorheight
    else:
        openbottom = back.floorheight
        lowfloor = front.floorheight
        
    openrange = opentop - openbottom


def P_UnsetThingPosition(thing):
    if not (thing.flags & doomdef.MF_NOSECTOR):
        # inert things don't need to be in blockmap?
        # unlink from subsector
        if thing.snext:
            thing.snext.sprev = thing.sprev

        if thing.sprev:
            thing.sprev.snext = thing.snext
        else:
            thing.subsector.sector.thinglist = thing.snext
            
    if not (thing.flags & doomdef.MF_NOBLOCKMAP):
        # inert things don't need to be in blockmap
        # unlink from block map
        if thing.bnext:
            thing.bnext.bprev = thing.bprev
        
        if thing.bprev:
            thing.bprev.bnext = thing.bnext
        else:
            blockx = (thing.x - doomstat.bmaporgx) >> doomdef.MAPBLOCKSHIFT
            blocky = (thing.y - doomstat.bmaporgy) >> doomdef.MAPBLOCKSHIFT

            if 0 <= blockx < doomstat.bmapwidth and 0 <= blocky < doomstat.bmapheight:
                doomstat.blocklinks[blocky * doomstat.bmapwidth + blockx] = thing.bnext


def P_SetThingPosition(thing):
    import r_main
    
    # link into subsector
    ss = r_main.R_PointInSubsector(thing.x, thing.y)
    thing.subsector = ss
    
    if not (thing.flags & doomdef.MF_NOSECTOR):
        # invisible things don't go into the sector links
        sec = ss.sector
        
        thing.sprev = None
        thing.snext = sec.thinglist

        if sec.thinglist:
            sec.thinglist.sprev = thing

        sec.thinglist = thing
        
    # link into blockmap
    if not (thing.flags & doomdef.MF_NOBLOCKMAP):
        # inert things don't need to be in blockmap		
        blockx = (thing.x - doomstat.bmaporgx) >> doomdef.MAPBLOCKSHIFT
        blocky = (thing.y - doomstat.bmaporgy) >> doomdef.MAPBLOCKSHIFT

        if 0 <= blockx < doomstat.bmapwidth and 0 <= blocky < doomstat.bmapheight:
            idx = blocky * doomstat.bmapwidth + blockx
            link = doomstat.blocklinks[idx]
            
            thing.bprev = None
            thing.bnext = link
            
            if link:
                link.bprev = thing

            doomstat.blocklinks[idx] = thing
        else:
            # thing is off the map
            thing.bnext = None
            thing.bprev = None


def P_BlockLinesIterator(x, y, func):
    if x < 0 or y < 0 or x >= doomstat.bmapwidth or y >= doomstat.bmapheight:
        return True
    
    offset = y * doomstat.bmapwidth + x
    offset = doomstat.blockmap[offset]

    list_idx = offset
    
    while True:
        val = doomstat.blockmaplump[list_idx]
        if val == -1 or val == 65535: # End of list
            break
            
        ld = doomstat.lines[val]

        if ld.validcount == doomstat.validcount:
            list_idx += 1
            continue     # line has already been checked

        ld.validcount = doomstat.validcount
        
        if not func(ld):
            return False
            
        list_idx += 1
            
    return True


def P_BlockThingsIterator(x, y, func):
    if x < 0 or y < 0 or x >= doomstat.bmapwidth or y >= doomstat.bmapheight:
        return True

    mobj = doomstat.blocklinks[y * doomstat.bmapwidth + x]
    
    while mobj:
        if not func(mobj):
            return False
        mobj = mobj.bnext
        
    return True


def InterceptsOverrun(num_intercepts, intercept):
    # In pure Python, we naturally let the list grow instead of intentionally 
    # crashing or corrupting specific globals like Vanilla Doom did, to guarantee 
    # engine stability while playing. Emulating actual C memory bounds crossing
    # is unnecessary as long as logic loops bounds properly.
    pass


def PIT_AddLineIntercepts(ld):
    global intercept_p
    
    # avoid precision problems with two routines
    if trace.dx > FRACUNIT * 16 or trace.dy > FRACUNIT * 16 or \
       trace.dx < -FRACUNIT * 16 or trace.dy < -FRACUNIT * 16:
        s1 = P_PointOnDivlineSide(ld.v1.x, ld.v1.y, trace)
        s2 = P_PointOnDivlineSide(ld.v2.x, ld.v2.y, trace)
    else:
        s1 = P_PointOnLineSide(trace.x, trace.y, ld)
        s2 = P_PointOnLineSide(trace.x + trace.dx, trace.y + trace.dy, ld)
    
    if s1 == s2:
        return True    # line isn't crossed
    
    # hit the line
    dl = divline_t()
    P_MakeDivline(ld, dl)
    frac = P_InterceptVector(trace, dl)

    if frac < 0:
        return True    # behind source
        
    # try to early out the check
    if earlyout and frac < FRACUNIT and not ld.backsector:
        return False    # stop checking
    
    if intercept_p >= len(intercepts):
        intercepts.append(intercept_t())
        
    intercepts[intercept_p].frac = frac
    intercepts[intercept_p].isaline = True
    intercepts[intercept_p].d_line = ld
    
    InterceptsOverrun(intercept_p, intercepts[intercept_p])
    intercept_p += 1

    return True        # continue


def PIT_AddThingIntercepts(thing):
    global intercept_p
    
    tracepositive = (trace.dx ^ trace.dy) > 0
        
    # check a corner to corner crossection for hit
    if tracepositive:
        x1 = thing.x - thing.radius
        y1 = thing.y + thing.radius
        
        x2 = thing.x + thing.radius
        y2 = thing.y - thing.radius            
    else:
        x1 = thing.x - thing.radius
        y1 = thing.y - thing.radius
        
        x2 = thing.x + thing.radius
        y2 = thing.y + thing.radius            
    
    s1 = P_PointOnDivlineSide(x1, y1, trace)
    s2 = P_PointOnDivlineSide(x2, y2, trace)

    if s1 == s2:
        return True        # line isn't crossed
        
    dl = divline_t()
    dl.x = x1
    dl.y = y1
    dl.dx = x2 - x1
    dl.dy = y2 - y1
    
    frac = P_InterceptVector(trace, dl)

    if frac < 0:
        return True        # behind source

    if intercept_p >= len(intercepts):
        intercepts.append(intercept_t())

    intercepts[intercept_p].frac = frac
    intercepts[intercept_p].isaline = False
    intercepts[intercept_p].d_thing = thing
    
    InterceptsOverrun(intercept_p, intercepts[intercept_p])
    intercept_p += 1

    return True        # keep going


def P_TraverseIntercepts(func, maxfrac):
    global intercept_p
    
    count = intercept_p
    
    while count > 0:
        dist = 2147483647 # INT_MAX
        in_obj = None
        
        for scan in range(intercept_p):
            if intercepts[scan].frac < dist:
                dist = intercepts[scan].frac
                in_obj = intercepts[scan]
        
        if dist > maxfrac:
            return True    # checked everything in range        

        if in_obj is not None:
            if not func(in_obj):
                return False    # don't bother going farther

            in_obj.frac = 2147483647
            
        count -= 1
        
    return True        # everything was traversed


def P_PathTraverse(x1, y1, x2, y2, flags, trav):
    global earlyout, intercept_p, trace
    
    earlyout = (flags & p_local.PT_EARLYOUT) != 0
        
    doomstat.validcount += 1
    intercept_p = 0
    
    if ((x1 - doomstat.bmaporgx) & (doomdef.MAPBLOCKSIZE - 1)) == 0:
        x1 += FRACUNIT    # don't side exactly on a line
    
    if ((y1 - doomstat.bmaporgy) & (doomdef.MAPBLOCKSIZE - 1)) == 0:
        y1 += FRACUNIT    # don't side exactly on a line

    trace.x = x1
    trace.y = y1
    trace.dx = x2 - x1
    trace.dy = y2 - y1

    x1 -= doomstat.bmaporgx
    y1 -= doomstat.bmaporgy
    xt1 = x1 >> doomdef.MAPBLOCKSHIFT
    yt1 = y1 >> doomdef.MAPBLOCKSHIFT

    x2 -= doomstat.bmaporgx
    y2 -= doomstat.bmaporgy
    xt2 = x2 >> doomdef.MAPBLOCKSHIFT
    yt2 = y2 >> doomdef.MAPBLOCKSHIFT

    if xt2 > xt1:
        mapxstep = 1
        partial = FRACUNIT - ((x1 >> doomdef.MAPBTOFRAC) & (FRACUNIT - 1))
        ystep = FixedDiv(y2 - y1, abs(x2 - x1))
    elif xt2 < xt1:
        mapxstep = -1
        partial = (x1 >> doomdef.MAPBTOFRAC) & (FRACUNIT - 1)
        ystep = FixedDiv(y2 - y1, abs(x2 - x1))
    else:
        mapxstep = 0
        partial = FRACUNIT
        ystep = 256 * FRACUNIT

    yintercept = (y1 >> doomdef.MAPBTOFRAC) + FixedMul(partial, ystep)
    
    if yt2 > yt1:
        mapystep = 1
        partial = FRACUNIT - ((y1 >> doomdef.MAPBTOFRAC) & (FRACUNIT - 1))
        xstep = FixedDiv(x2 - x1, abs(y2 - y1))
    elif yt2 < yt1:
        mapystep = -1
        partial = (y1 >> doomdef.MAPBTOFRAC) & (FRACUNIT - 1)
        xstep = FixedDiv(x2 - x1, abs(y2 - y1))
    else:
        mapystep = 0
        partial = FRACUNIT
        xstep = 256 * FRACUNIT

    xintercept = (x1 >> doomdef.MAPBTOFRAC) + FixedMul(partial, xstep)
    
    # Step through map blocks.
    # Count is present to prevent a round off error
    # from skipping the break.
    mapx = xt1
    mapy = yt1
    
    for count in range(64):
        if flags & p_local.PT_ADDLINES:
            if not P_BlockLinesIterator(mapx, mapy, PIT_AddLineIntercepts):
                return False    # early out
        
        if flags & p_local.PT_ADDTHINGS:
            if not P_BlockThingsIterator(mapx, mapy, PIT_AddThingIntercepts):
                return False    # early out
                
        if mapx == xt2 and mapy == yt2:
            break
        
        if (yintercept >> FRACBITS) == mapy:
            yintercept += ystep
            mapx += mapxstep
        elif (xintercept >> FRACBITS) == mapx:
            xintercept += xstep
            mapy += mapystep
            
    # go through the sorted list
    return P_TraverseIntercepts(trav, FRACUNIT)
