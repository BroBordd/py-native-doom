import p_ceilng
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
#	Floor animation: raising stairs.
#

import doomdef
import doomstat
import p_spec
import p_tick
import s_sound
import r_data
from doomdef import FRACUNIT
from sounds import *

# e6y
STAIRS_UNINITIALIZED_CRUSH_FIELD_VALUE = 10

#
# FLOORS
#

#
# Move a plane (floor or ceiling) and check for crushing
#
def T_MovePlane(sector, speed, dest, crush, floorOrCeiling, direction):
    if floorOrCeiling == 0:
        # FLOOR
        if direction == -1:
            # DOWN
            if sector.floorheight - speed < dest:
                lastpos = sector.floorheight
                sector.floorheight = dest
                if p_spec.P_ChangeSector(sector, crush):
                    sector.floorheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    # return p_spec.crushed
                return p_spec.pastdest
            else:
                lastpos = sector.floorheight
                sector.floorheight -= speed
                if p_spec.P_ChangeSector(sector, crush):
                    sector.floorheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    return p_spec.crushed

        elif direction == 1:
            # UP
            if sector.floorheight + speed > dest:
                lastpos = sector.floorheight
                sector.floorheight = dest
                if p_spec.P_ChangeSector(sector, crush):
                    sector.floorheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    # return p_spec.crushed
                return p_spec.pastdest
            else:
                # COULD GET CRUSHED
                lastpos = sector.floorheight
                sector.floorheight += speed
                if p_spec.P_ChangeSector(sector, crush):
                    if crush:
                        return p_spec.crushed
                    sector.floorheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    return p_spec.crushed

    elif floorOrCeiling == 1:
        # CEILING
        if direction == -1:
            # DOWN
            if sector.ceilingheight - speed < dest:
                lastpos = sector.ceilingheight
                sector.ceilingheight = dest
                if p_spec.P_ChangeSector(sector, crush):
                    sector.ceilingheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    # return p_spec.crushed
                return p_spec.pastdest
            else:
                # COULD GET CRUSHED
                lastpos = sector.ceilingheight
                sector.ceilingheight -= speed
                if p_spec.P_ChangeSector(sector, crush):
                    if crush:
                        return p_spec.crushed
                    sector.ceilingheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    return p_spec.crushed

        elif direction == 1:
            # UP
            if sector.ceilingheight + speed > dest:
                lastpos = sector.ceilingheight
                sector.ceilingheight = dest
                if p_spec.P_ChangeSector(sector, crush):
                    sector.ceilingheight = lastpos
                    p_spec.P_ChangeSector(sector, crush)
                    # return p_spec.crushed
                return p_spec.pastdest
            else:
                lastpos = sector.ceilingheight
                sector.ceilingheight += speed
                if p_spec.P_ChangeSector(sector, crush):
                    pass # UNUSED

    return p_spec.ok


#
# MOVE A FLOOR TO IT'S DESTINATION (UP OR DOWN)
#
def T_MoveFloor(floor):
    res = p_floor.T_MovePlane(floor.sector,
                      floor.speed,
                      floor.floordestheight,
                      floor.crush, 0, floor.direction)
    
    if not (doomstat.leveltime & 7):
        s_sound.S_StartSound(floor.sector.soundorg, sfx_stnmov)
    
    if res == p_spec.pastdest:
        floor.sector.specialdata = None

        if floor.direction == 1:
            if floor.type == p_spec.donutRaise:
                floor.sector.special = floor.newspecial
                floor.sector.floorpic = floor.texture
        elif floor.direction == -1:
            if floor.type == p_spec.lowerAndChange:
                floor.sector.special = floor.newspecial
                floor.sector.floorpic = floor.texture
                
        p_tick.P_RemoveThinker(floor)
        s_sound.S_StartSound(floor.sector.soundorg, sfx_pstop)


#
# HANDLE FLOOR TYPES
#
def EV_DoFloor(line, floortype):
    secnum = -1
    rtn = 0
    
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0:
            break
            
        sec = doomstat.sectors[secnum]
        
        # ALREADY MOVING?  IF SO, KEEP GOING...
        if sec.specialdata:
            continue
        
        # new floor thinker
        rtn = 1
        floor = p_spec.floormove_t()
        p_tick.P_AddThinker(floor)
        sec.specialdata = floor
        floor.function = T_MoveFloor
        floor.type = floortype
        floor.crush = False

        if floortype == p_spec.lowerFloor:
            floor.direction = -1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = p_spec.P_FindHighestFloorSurrounding(sec)

        elif floortype == p_spec.lowerFloorToLowest:
            floor.direction = -1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = p_spec.P_FindLowestFloorSurrounding(sec)

        elif floortype == p_spec.turboLower:
            floor.direction = -1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED * 4
            floor.floordestheight = p_spec.P_FindHighestFloorSurrounding(sec)
            if doomstat.gameversion <= doomstat.exe_doom_1_2 or floor.floordestheight != sec.floorheight:
                floor.floordestheight += 8 * FRACUNIT

        elif floortype in (p_spec.raiseFloorCrush, p_spec.raiseFloor):
            floor.crush = (floortype == p_spec.raiseFloorCrush)
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = p_spec.P_FindLowestCeilingSurrounding(sec)
            if floor.floordestheight > sec.ceilingheight:
                floor.floordestheight = sec.ceilingheight
            if floortype == p_spec.raiseFloorCrush:
                floor.floordestheight -= 8 * FRACUNIT

        elif floortype == p_spec.raiseFloorTurbo:
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED * 4
            floor.floordestheight = p_spec.P_FindNextHighestFloor(sec, sec.floorheight)

        elif floortype == p_spec.raiseFloorToNearest:
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = p_spec.P_FindNextHighestFloor(sec, sec.floorheight)

        elif floortype == p_spec.raiseFloor24:
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = floor.sector.floorheight + 24 * FRACUNIT
            
        elif floortype == p_spec.raiseFloor512:
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = floor.sector.floorheight + 512 * FRACUNIT

        elif floortype == p_spec.raiseFloor24AndChange:
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = floor.sector.floorheight + 24 * FRACUNIT
            sec.floorpic = line.frontsector.floorpic
            sec.special = line.frontsector.special

        elif floortype == p_spec.raiseToTexture:
            minsize = 2**31 - 1
            floor.direction = 1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            for i in range(sec.linecount):
                line_i = sec.lines[i]
                if line_i.flags & doomdef.ML_TWOSIDED:
                    sidenum0 = line_i.sidenum[0]
                    if sidenum0 > -1:
                        side0 = doomstat.sides[sidenum0]
                        if side0.bottomtexture >= 0:
                            if r_data.textureheight[side0.bottomtexture] < minsize:
                                minsize = r_data.textureheight[side0.bottomtexture]
                    sidenum1 = line_i.sidenum[1]
                    if sidenum1 > -1:
                        side1 = doomstat.sides[sidenum1]
                        if side1.bottomtexture >= 0:
                            if r_data.textureheight[side1.bottomtexture] < minsize:
                                minsize = r_data.textureheight[side1.bottomtexture]
            floor.floordestheight = floor.sector.floorheight + minsize
            
        elif floortype == p_spec.lowerAndChange:
            floor.direction = -1
            floor.sector = sec
            floor.speed = p_spec.FLOORSPEED
            floor.floordestheight = p_spec.P_FindLowestFloorSurrounding(sec)
            floor.texture = sec.floorpic

            for i in range(sec.linecount):
                line_i = sec.lines[i]
                if line_i.flags & doomdef.ML_TWOSIDED:
                    sidenum0 = line_i.sidenum[0]
                    sidenum1 = line_i.sidenum[1]
                    if sidenum0 > -1 and doomstat.sides[sidenum0].sector == sec:
                        if sidenum1 > -1:
                            adj_sec = doomstat.sides[sidenum1].sector
                            if adj_sec.floorheight == floor.floordestheight:
                                floor.texture = adj_sec.floorpic
                                floor.newspecial = adj_sec.special
                                break
                    elif sidenum1 > -1 and doomstat.sides[sidenum1].sector == sec:
                        if sidenum0 > -1:
                            adj_sec = doomstat.sides[sidenum0].sector
                            if adj_sec.floorheight == floor.floordestheight:
                                floor.texture = adj_sec.floorpic
                                floor.newspecial = adj_sec.special
                                break

    return rtn


#
# BUILD A STAIRCASE!
#
def EV_BuildStairs(line, type):
    secnum = -1
    rtn = 0
    
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0:
            break
            
        sec = doomstat.sectors[secnum]
        
        # ALREADY MOVING?  IF SO, KEEP GOING...
        if sec.specialdata:
            continue
        
        # new floor thinker
        rtn = 1
        floor = p_spec.floormove_t()
        p_tick.P_AddThinker(floor)
        sec.specialdata = floor
        floor.function = T_MoveFloor
        floor.direction = 1
        floor.sector = sec
        
        speed = 0
        stairsize = 0
        if type == p_spec.build8:
            speed = p_spec.FLOORSPEED // 4
            stairsize = 8 * FRACUNIT
        elif type == p_spec.turbo16:
            speed = p_spec.FLOORSPEED * 4
            stairsize = 16 * FRACUNIT
            
        floor.speed = speed
        height = sec.floorheight + stairsize
        floor.floordestheight = height
        
        # Initialize
        floor.type = p_spec.lowerFloor
        # e6y
        # Uninitialized crush field will not be equal to 0 or 1 (true)
        # with high probability. So, initialize it with any other value
        floor.crush = STAIRS_UNINITIALIZED_CRUSH_FIELD_VALUE
        
        texture = sec.floorpic
        
        # Find next sector to raise
        # 1.    Find 2-sided line with same sector side[0]
        # 2.    Other side is the next sector to raise
        ok_flag = True
        while ok_flag:
            ok_flag = False
            for i in range(sec.linecount):
                line_i = sec.lines[i]
                if not (line_i.flags & doomdef.ML_TWOSIDED):
                    continue
                    
                tsec = line_i.frontsector
                if sec != tsec:
                    continue

                tsec = line_i.backsector
                newsecnum = doomstat.sectors.index(tsec)

                if tsec.floorpic != texture:
                    continue
                    
                height += stairsize

                if tsec.specialdata:
                    continue
                    
                sec = tsec
                secnum = newsecnum
                
                floor = p_spec.floormove_t()
                p_tick.P_AddThinker(floor)
                sec.specialdata = floor
                
                floor.function = T_MoveFloor
                floor.direction = 1
                floor.sector = sec
                floor.speed = speed
                floor.floordestheight = height
                # Initialize
                floor.type = p_spec.lowerFloor
                # e6y
                floor.crush = STAIRS_UNINITIALIZED_CRUSH_FIELD_VALUE
                ok_flag = True
                break

    return rtn
