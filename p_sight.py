import p_ceilng
import p_floor
import p_tick
import p_spec
#
# Copyright(C) 1993-1996 Id Software, Inc.
# Copyright(C) 2005-2014 Simon Howard
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
#	LineOfSight/Visibility checks, uses REJECT Lookup Table.
#

import doomdef
import doomstat
import p_local
import i_system

try:
    from m_fixed import FixedMul, FixedDiv
except ImportError:
    def FixedMul(a, b):
        return (a * b) >> 16
    def FixedDiv(a, b):
        if b == 0:
            return 0
        return int((a * 65536.0) / b)

class divline_t:
    def __init__(self, x=0, y=0, dx=0, dy=0):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy

#
# P_CheckSight variables
#
sightzstart = 0         # eye z of looker
topslope = 0
bottomslope = 0         # slopes to top and bottom of target

strace = divline_t()    # from t1 to t2
t2x = 0
t2y = 0

sightcounts = [0, 0]


# PTR_SightTraverse() for Doom 1.2 sight calculations
# taken from prboom-plus/src/p_sight.c:69-102
def PTR_SightTraverse(in_intercept):
    global topslope, bottomslope, sightzstart
    li = in_intercept.d.line

    # crosses a two sided line
    p_local.P_LineOpening(li)

    if p_local.openbottom >= p_local.opentop: # quick test for totally closed doors
        return False                          # stop

    if li.frontsector.floorheight != li.backsector.floorheight:
        slope = FixedDiv(p_local.openbottom - sightzstart, in_intercept.frac)
        if slope > bottomslope:
            bottomslope = slope

    if li.frontsector.ceilingheight != li.backsector.ceilingheight:
        slope = FixedDiv(p_local.opentop - sightzstart, in_intercept.frac)
        if slope < topslope:
            topslope = slope

    if topslope <= bottomslope:
        return False # stop

    return True # keep going


#
# P_DivlineSide
# Returns side 0 (front), 1 (back), or 2 (on).
#
def P_DivlineSide(x, y, node):
    if not node.dx:
        if x == node.x:
            return 2
        
        if x <= node.x:
            return 1 if node.dy > 0 else 0

        return 1 if node.dy < 0 else 0
    
    if not node.dy:
        if x == node.y:
            return 2

        if y <= node.y:
            return 1 if node.dx < 0 else 0

        return 1 if node.dx > 0 else 0
        
    dx = x - node.x
    dy = y - node.y

    left = (node.dy >> doomdef.FRACBITS) * (dx >> doomdef.FRACBITS)
    right = (dy >> doomdef.FRACBITS) * (node.dx >> doomdef.FRACBITS)
        
    if right < left:
        return 0    # front side
    
    if left == right:
        return 2
    return 1        # back side


#
# P_InterceptVector2
# Returns the fractional intercept point
# along the first divline.
# This is only called by the addthings and addlines traversers.
#
def P_InterceptVector2(v2, v1):
    den = FixedMul(v1.dy >> 8, v2.dx) - FixedMul(v1.dx >> 8, v2.dy)

    if den == 0:
        return 0
    #   I_Error ("P_InterceptVector: parallel")
    
    num = FixedMul((v1.x - v2.x) >> 8, v1.dy) + FixedMul((v2.y - v1.y) >> 8, v1.dx)
    frac = FixedDiv(num, den)

    return frac


#
# P_CrossSubsector
# Returns true
#  if strace crosses the given subsector successfully.
#
def P_CrossSubsector(num):
    global sightzstart, topslope, bottomslope, strace, t2x, t2y

    sub = doomstat.subsectors[num]
    
    # check lines
    count = sub.numlines
    seg_idx = sub.firstline

    for i in range(count):
        seg = doomstat.segs[seg_idx + i]
        line = seg.linedef

        # allready checked other side?
        if line.validcount == doomstat.validcount:
            continue
        
        line.validcount = doomstat.validcount

        v1 = line.v1
        v2 = line.v2
        s1 = P_DivlineSide(v1.x, v1.y, strace)
        s2 = P_DivlineSide(v2.x, v2.y, strace)

        # line isn't crossed?
        if s1 == s2:
            continue
        
        divl = divline_t(v1.x, v1.y, v2.x - v1.x, v2.y - v1.y)
        s1 = P_DivlineSide(strace.x, strace.y, divl)
        s2 = P_DivlineSide(t2x, t2y, divl)

        # line isn't crossed?
        if s1 == s2:
            continue    

        # Backsector may be NULL if this is an "impassible
        # glass" hack line.
        if line.backsector is None:
            return False

        # stop because it is not two sided anyway
        # might do this after updating validcount?
        if not (line.flags & doomdef.ML_TWOSIDED):
            return False
        
        # crosses a two sided line
        front = seg.frontsector
        back = seg.backsector

        # no wall to block sight with?
        if front.floorheight == back.floorheight and front.ceilingheight == back.ceilingheight:
            continue    

        # possible occluder
        # because of ceiling height differences
        if front.ceilingheight < back.ceilingheight:
            opentop = front.ceilingheight
        else:
            opentop = back.ceilingheight

        # because of ceiling height differences
        if front.floorheight > back.floorheight:
            openbottom = front.floorheight
        else:
            openbottom = back.floorheight
            
        # quick test for totally closed doors
        if openbottom >= opentop:    
            return False        # stop
        
        frac = P_InterceptVector2(strace, divl)
            
        if front.floorheight != back.floorheight:
            slope = FixedDiv(openbottom - sightzstart, frac)
            if slope > bottomslope:
                bottomslope = slope
                
        if front.ceilingheight != back.ceilingheight:
            slope = FixedDiv(opentop - sightzstart, frac)
            if slope < topslope:
                topslope = slope
                
        if topslope <= bottomslope:
            return False        # stop                
            
    # passed the subsector ok
    return True        


#
# P_CrossBSPNode
# Returns true
#  if strace crosses the given node successfully.
#
def P_CrossBSPNode(bspnum):
    if bspnum & doomstat.NF_SUBSECTOR:
        if bspnum == -1:
            return P_CrossSubsector(0)
        else:
            return P_CrossSubsector(bspnum & (~doomstat.NF_SUBSECTOR))
            
    bsp = doomstat.nodes[bspnum]
    
    # decide which side the start point is on
    side = P_DivlineSide(strace.x, strace.y, bsp)
    if side == 2:
        side = 0    # an "on" should cross both sides

    # cross the starting side
    if not P_CrossBSPNode(bsp.children[side]):
        return False
        
    # the partition plane is crossed here
    if side == P_DivlineSide(t2x, t2y, bsp):
        # the line doesn't touch the other side
        return True
    
    # cross the ending side        
    return P_CrossBSPNode(bsp.children[side^1])


#
# P_CheckSight
# Returns true
#  if a straight line between t1 and t2 is unobstructed.
# Uses REJECT.
#
def P_CheckSight(t1, t2):
    global sightcounts, sightzstart, topslope, bottomslope, strace, t2x, t2y
    
    # First check for trivial rejection.

    # Determine subsector entries in REJECT table.
    s1 = doomstat.sectors.index(t1.subsector.sector)
    s2 = doomstat.sectors.index(t2.subsector.sector)
    pnum = s1 * doomstat.numsectors + s2
    bytenum = pnum >> 3
    bitnum = 1 << (pnum & 7)

    # Check in REJECT table.
    if doomstat.rejectmatrix[bytenum] & bitnum:
        sightcounts[0] += 1
        # can't possibly be connected
        return False    

    # An unobstructed LOS is possible.
    # Now look from eyes of t1 to any part of t2.
    sightcounts[1] += 1
    doomstat.validcount += 1
        
    sightzstart = t1.z + t1.height - (t1.height >> 2)
    topslope = (t2.z + t2.height) - sightzstart
    bottomslope = t2.z - sightzstart
        
    if doomstat.gameversion <= doomstat.exe_doom_1_2:
        return p_local.P_PathTraverse(t1.x, t1.y, t2.x, t2.y,
                                      p_local.PT_EARLYOUT | p_local.PT_ADDLINES, PTR_SightTraverse)

    strace.x = t1.x
    strace.y = t1.y
    t2x = t2.x
    t2y = t2.y
    strace.dx = t2.x - t1.x
    strace.dy = t2.y - t1.y

    # the head node is the last node output
    return P_CrossBSPNode(doomstat.numnodes - 1)
