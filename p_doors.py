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
# DESCRIPTION: Door animation code (opening/closing)
#

import sys
import doomstat
import doomdef
import deh_str
import i_system
import s_sound
import p_tick
import p_spec
import p_plats
import p_floor
from doomdef import FRACUNIT
from dstrings import *
from sounds import *


#
# VERTICAL DOORS
#

def T_VerticalDoor(door):
    if door.direction == 0:
        # WAITING
        door.topcountdown -= 1
        if door.topcountdown <= 0:
            if door.type == p_spec.vld_blazeRaise:
                door.direction = -1 # time to go back down
                s_sound.S_StartSound(door.sector.soundorg, sfx_bdcls)
            elif door.type == p_spec.vld_normal:
                door.direction = -1 # time to go back down
                s_sound.S_StartSound(door.sector.soundorg, sfx_dorcls)
            elif door.type == p_spec.vld_close30ThenOpen:
                door.direction = 1
                s_sound.S_StartSound(door.sector.soundorg, sfx_doropn)
                
    elif door.direction == 2:
        # INITIAL WAIT
        door.topcountdown -= 1
        if door.topcountdown <= 0:
            if door.type == p_spec.vld_raiseIn5Mins:
                door.direction = 1
                door.type = p_spec.vld_normal
                s_sound.S_StartSound(door.sector.soundorg, sfx_doropn)

    elif door.direction == -1:
        # DOWN
        res = p_floor.T_MovePlane(door.sector, door.speed, door.sector.floorheight, False, 1, door.direction)
        
        if res == p_spec.pastdest:
            if door.type in (p_spec.vld_blazeRaise, p_spec.vld_blazeClose):
                door.sector.specialdata = None
                p_tick.P_RemoveThinker(door)  # unlink and free
                s_sound.S_StartSound(door.sector.soundorg, sfx_bdcls)
            elif door.type in (p_spec.vld_normal, p_spec.vld_close):
                door.sector.specialdata = None
                p_tick.P_RemoveThinker(door)  # unlink and free
            elif door.type == p_spec.vld_close30ThenOpen:
                door.direction = 0
                door.topcountdown = doomdef.TICRATE * 30
                
        elif res == p_spec.crushed:
            if door.type not in (p_spec.vld_blazeClose, p_spec.vld_close):
                # DO NOT GO BACK UP! (for close/blazeClose types)
                door.direction = 1
                s_sound.S_StartSound(door.sector.soundorg, sfx_doropn)

    elif door.direction == 1:
        # UP
        res = p_floor.T_MovePlane(door.sector, door.speed, door.topheight, False, 1, door.direction)
        
        if res == p_spec.pastdest:
            if door.type in (p_spec.vld_blazeRaise, p_spec.vld_normal):
                door.direction = 0 # wait at top
                door.topcountdown = door.topwait
            elif door.type in (p_spec.vld_close30ThenOpen, p_spec.vld_blazeOpen, p_spec.vld_open):
                door.sector.specialdata = None
                p_tick.P_RemoveThinker(door)  # unlink and free


#
# EV_DoLockedDoor
# Move a locked door up/down
#
def EV_DoLockedDoor(line, type, thing):
    p = thing.player
    
    if not p:
        return 0
        
    if line.special in (99, 133): # Blue Lock
        if not p.cards[doomdef.it_bluecard] and not p.cards[doomdef.it_blueskull]:
            p.message = deh_str.DEH_String(PD_BLUEO)
            s_sound.S_StartSound(None, sfx_oof)
            return 0
            
    elif line.special in (134, 135): # Red Lock
        if not p.cards[doomdef.it_redcard] and not p.cards[doomdef.it_redskull]:
            p.message = deh_str.DEH_String(PD_REDO)
            s_sound.S_StartSound(None, sfx_oof)
            return 0
            
    elif line.special in (136, 137): # Yellow Lock
        if not p.cards[doomdef.it_yellowcard] and not p.cards[doomdef.it_yellowskull]:
            p.message = deh_str.DEH_String(PD_YELLOWO)
            s_sound.S_StartSound(None, sfx_oof)
            return 0

    return p_doors.EV_DoDoor(line, type)


def EV_DoDoor(line, type):
    secnum = -1
    rtn = 0
    
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0:
            break
            
        sec = doomstat.sectors[secnum]
        if sec.specialdata:
            continue
            
        # new door thinker
        rtn = 1
        door = p_spec.vldoor_t()
        p_tick.P_AddThinker(door)
        sec.specialdata = door

        door.function = T_VerticalDoor
        door.sector = sec
        door.type = type
        door.topwait = p_spec.VDOORWAIT
        door.speed = p_spec.VDOORSPEED
        
        if type == p_spec.vld_blazeClose:
            door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec)
            door.topheight -= 4 * FRACUNIT
            door.direction = -1
            door.speed = p_spec.VDOORSPEED * 4
            s_sound.S_StartSound(door.sector.soundorg, sfx_bdcls)
            
        elif type == p_spec.vld_close:
            door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec)
            door.topheight -= 4 * FRACUNIT
            door.direction = -1
            s_sound.S_StartSound(door.sector.soundorg, sfx_dorcls)
            
        elif type == p_spec.vld_close30ThenOpen:
            door.topheight = sec.ceilingheight
            door.direction = -1
            s_sound.S_StartSound(door.sector.soundorg, sfx_dorcls)
            
        elif type in (p_spec.vld_blazeRaise, p_spec.vld_blazeOpen):
            door.direction = 1
            door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec)
            door.topheight -= 4 * FRACUNIT
            door.speed = p_spec.VDOORSPEED * 4
            if door.topheight != sec.ceilingheight:
                s_sound.S_StartSound(door.sector.soundorg, sfx_bdopn)
                
        elif type in (p_spec.vld_normal, p_spec.vld_open):
            door.direction = 1
            door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec)
            door.topheight -= 4 * FRACUNIT
            if door.topheight != sec.ceilingheight:
                s_sound.S_StartSound(door.sector.soundorg, sfx_doropn)
                
    return rtn


#
# EV_VerticalDoor : open a door manually, no tag value
#
def EV_VerticalDoor(line, thing):
    side = 0  # only front sides can be used
    player = thing.player
    
    # Check for locks
    if line.special in (26, 32): # Blue Lock
        if not player:
            return
        if not player.cards[doomdef.it_bluecard] and not player.cards[doomdef.it_blueskull]:
            player.message = deh_str.DEH_String(PD_BLUEK)
            s_sound.S_StartSound(None, sfx_oof)
            return
            
    elif line.special in (27, 34): # Yellow Lock
        if not player:
            return
        if not player.cards[doomdef.it_yellowcard] and not player.cards[doomdef.it_yellowskull]:
            player.message = deh_str.DEH_String(PD_YELLOWK)
            s_sound.S_StartSound(None, sfx_oof)
            return
            
    elif line.special in (28, 33): # Red Lock
        if not player:
            return
        if not player.cards[doomdef.it_redcard] and not player.cards[doomdef.it_redskull]:
            player.message = deh_str.DEH_String(PD_REDK)
            s_sound.S_StartSound(None, sfx_oof)
            return

    # if the sector has an active thinker, use it
    if line.sidenum[side^1] == -1:
        i_system.I_Error("EV_VerticalDoor: DR special type on 1-sided linedef")

    sec = doomstat.sides[line.sidenum[side^1]].sector

    if sec.specialdata:
        door = sec.specialdata
        if line.special in (1, 26, 27, 28, 117):
            if door.direction == -1:
                door.direction = 1  # go back up
            else:
                if not thing.player:
                    return  # JDC: bad guys never close doors

                # When is a door not a door?
                # In Vanilla, door->direction is set, even though
                # "specialdata" might not actually point at a door.
                if getattr(door, 'function', None) == T_VerticalDoor:
                    door.direction = -1  # start going down immediately
                elif getattr(door, 'function', None) == p_plats.T_PlatRaise:
                    # Erm, this is a plat, not a door.
                    # This notably causes a problem in ep1-0500.lmp where
                    # a plat and a door are cross-referenced
                    door.wait = -1
                else:
                    # This isn't a door OR a plat. Now we're in trouble.
                    sys.stderr.write("EV_VerticalDoor: Tried to close something that wasn't a door.\n")
                    # Try closing it anyway.
                    door.direction = -1
            return
            
    # for proper sound
    if line.special in (117, 118): # BLAZING DOOR RAISE / OPEN
        s_sound.S_StartSound(sec.soundorg, sfx_bdopn)
    elif line.special in (1, 31):  # NORMAL DOOR SOUND
        s_sound.S_StartSound(sec.soundorg, sfx_doropn)
    else:                          # LOCKED DOOR SOUND
        s_sound.S_StartSound(sec.soundorg, sfx_doropn)
        
    # new door thinker
    door = p_spec.vldoor_t()
    p_tick.P_AddThinker(door)
    sec.specialdata = door
    
    door.function = T_VerticalDoor
    door.sector = sec
    door.direction = 1
    door.speed = p_spec.VDOORSPEED
    door.topwait = p_spec.VDOORWAIT

    if line.special in (1, 26, 27, 28):
        door.type = p_spec.vld_normal
    elif line.special in (31, 32, 33, 34):
        door.type = p_spec.vld_open
        line.special = 0
    elif line.special == 117: # blazing door raise
        door.type = p_spec.vld_blazeRaise
        door.speed = p_spec.VDOORSPEED * 4
    elif line.special == 118: # blazing door open
        door.type = p_spec.vld_blazeOpen
        line.special = 0
        door.speed = p_spec.VDOORSPEED * 4
        
    # find the top and bottom of the movement range
    door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec)
    door.topheight -= 4 * FRACUNIT


#
# Spawn a door that closes after 30 seconds
#
def P_SpawnDoorCloseIn30(sec):
    door = p_spec.vldoor_t()
    p_tick.P_AddThinker(door)

    sec.specialdata = door
    sec.special = 0

    door.function = T_VerticalDoor
    door.sector = sec
    door.direction = 0
    door.type = p_spec.vld_normal
    door.speed = p_spec.VDOORSPEED
    door.topcountdown = 30 * doomdef.TICRATE


#
# Spawn a door that opens after 5 minutes
#
def P_SpawnDoorRaiseIn5Mins(sec, secnum):
    door = p_spec.vldoor_t()
    p_tick.P_AddThinker(door)

    sec.specialdata = door
    sec.special = 0

    door.function = T_VerticalDoor
    door.sector = sec
    door.direction = 2
    door.type = p_spec.vld_raiseIn5Mins
    door.speed = p_spec.VDOORSPEED
    door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec)
    door.topheight -= 4 * FRACUNIT
    door.topwait = p_spec.VDOORWAIT
    door.topcountdown = 5 * 60 * doomdef.TICRATE
