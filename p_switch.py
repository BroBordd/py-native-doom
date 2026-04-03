import p_tick
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
#
# DESCRIPTION:
#	Switches, buttons. Two-state animation. Exits.
#

import i_system
import deh_str
import doomdef
import doomstat
import s_sound
import g_game
import p_spec
import p_doors
import p_floor
import p_plats
import p_ceilng
import p_lights
import r_data
from sounds import *

MAXSWITCHES = 50
MAXBUTTONS = 16
BUTTONTIME = 35  # 1 second in tics

# bwhere_e enum
top = 0
middle = 1
bottom = 2

class button_t:
    def __init__(self):
        self.line = None
        self.where = 0
        self.btexture = 0
        self.btimer = 0
        self.soundorg = None

#
# CHANGE THE TEXTURE OF A WALL SWITCH TO ITS OPPOSITE
#
alphSwitchList = [
    # Doom shareware episode 1 switches
    ("SW1BRCOM", "SW2BRCOM", 1),
    ("SW1BRN1",  "SW2BRN1",  1),
    ("SW1BRN2",  "SW2BRN2",  1),
    ("SW1BRNGN", "SW2BRNGN", 1),
    ("SW1BROWN", "SW2BROWN", 1),
    ("SW1COMM",  "SW2COMM",  1),
    ("SW1COMP",  "SW2COMP",  1),
    ("SW1DIRT",  "SW2DIRT",  1),
    ("SW1EXIT",  "SW2EXIT",  1),
    ("SW1GRAY",  "SW2GRAY",  1),
    ("SW1GRAY1", "SW2GRAY1", 1),
    ("SW1METAL", "SW2METAL", 1),
    ("SW1PIPE",  "SW2PIPE",  1),
    ("SW1SLAD",  "SW2SLAD",  1),
    ("SW1STARG", "SW2STARG", 1),
    ("SW1STON1", "SW2STON1", 1),
    ("SW1STON2", "SW2STON2", 1),
    ("SW1STONE", "SW2STONE", 1),
    ("SW1STRTN", "SW2STRTN", 1),

    # Doom registered episodes 2&3 switches
    ("SW1BLUE",  "SW2BLUE",  2),
    ("SW1CMT",   "SW2CMT",   2),
    ("SW1GARG",  "SW2GARG",  2),
    ("SW1GSTON", "SW2GSTON", 2),
    ("SW1HOT",   "SW2HOT",   2),
    ("SW1LION",  "SW2LION",  2),
    ("SW1SATYR", "SW2SATYR", 2),
    ("SW1SKIN",  "SW2SKIN",  2),
    ("SW1VINE",  "SW2VINE",  2),
    ("SW1WOOD",  "SW2WOOD",  2),

    # Doom II switches
    ("SW1PANEL", "SW2PANEL", 3),
    ("SW1ROCK",  "SW2ROCK",  3),
    ("SW1MET2",  "SW2MET2",  3),
    ("SW1WDMET", "SW2WDMET", 3),
    ("SW1BRIK",  "SW2BRIK",  3),
    ("SW1MOD1",  "SW2MOD1",  3),
    ("SW1ZIM",   "SW2ZIM",   3),
    ("SW1STON6", "SW2STON6", 3),
    ("SW1TEK",   "SW2TEK",   3),
    ("SW1MARB",  "SW2MARB",  3),
    ("SW1SKULL", "SW2SKULL", 3)
]

switchlist = []
numswitches = 0
buttonlist = [button_t() for _ in range(MAXBUTTONS)]


#
# P_InitSwitchList
# Only called at game initialization.
#
def P_InitSwitchList():
    global switchlist, numswitches

    # Note that this is called "episode" here but it's actually something
    # quite different. As we progress from Shareware->Registered->Doom II
    # we support more switch textures.
    if doomstat.gamemode in (doomstat.registered, doomstat.retail):
        episode = 2
    elif doomstat.gamemode == doomstat.commercial:
        episode = 3
    else:
        episode = 1

    switchlist = []

    for name1, name2, sw_ep in alphSwitchList:
        if sw_ep <= episode:
            switchlist.append(r_data.R_CheckTextureNumForName(deh_str.DEH_String(name1)))
            switchlist.append(r_data.R_CheckTextureNumForName(deh_str.DEH_String(name2)))

    numswitches = len(switchlist) // 2
    switchlist.append(-1)


#
# Start a button counting down till it turns off.
#
def P_StartButton(line, w, texture, time):
    # See if button is already pressed
    for i in range(MAXBUTTONS):
        if buttonlist[i].btimer and buttonlist[i].line == line:
            return

    for i in range(MAXBUTTONS):
        if not buttonlist[i].btimer:
            buttonlist[i].line = line
            buttonlist[i].where = w
            buttonlist[i].btexture = texture
            buttonlist[i].btimer = time
            buttonlist[i].soundorg = line.frontsector.soundorg
            return

    i_system.I_Error("P_StartButton: no button slots left!")


#
# Function that changes wall texture.
# Tell it if switch is ok to use again (1=yes, it's a button).
#
def P_ChangeSwitchTexture(line, useAgain):
    if not useAgain:
        line.special = 0

    sidenum0 = line.sidenum[0]
    texTop = doomstat.sides[sidenum0].toptexture
    texMid = doomstat.sides[sidenum0].midtexture
    texBot = doomstat.sides[sidenum0].bottomtexture
    
    sound = sfx_swtchn

    # EXIT SWITCH?
    if line.special == 11:
        sound = sfx_swtchx
        
    for i in range(numswitches * 2):
        if switchlist[i] == texTop:
            # Replicating a bug in vanilla doom where it plays the sound
            # using the 0th button's soundorg.
            s_sound.S_StartSound(buttonlist[0].soundorg, sound)
            doomstat.sides[sidenum0].toptexture = switchlist[i^1]

            if useAgain:
                P_StartButton(line, top, switchlist[i], BUTTONTIME)

            return
            
        elif switchlist[i] == texMid:
            s_sound.S_StartSound(buttonlist[0].soundorg, sound)
            doomstat.sides[sidenum0].midtexture = switchlist[i^1]

            if useAgain:
                P_StartButton(line, middle, switchlist[i], BUTTONTIME)

            return
            
        elif switchlist[i] == texBot:
            s_sound.S_StartSound(buttonlist[0].soundorg, sound)
            doomstat.sides[sidenum0].bottomtexture = switchlist[i^1]

            if useAgain:
                P_StartButton(line, bottom, switchlist[i], BUTTONTIME)

            return


#
# P_UseSpecialLine
# Called when a thing uses a special line.
# Only the front sides of lines are usable.
#
def P_UseSpecialLine(thing, line, side):
    
    # Err...
    # Use the back sides of VERY SPECIAL lines...
    if side != 0:
        if line.special == 124:
            # Sliding door open&close
            # UNUSED?
            pass
        else:
            return False

    # Switches that other things can activate.
    if not thing.player:
        # never open secret doors
        if line.flags & doomdef.ML_SECRET:
            return False
        
        if line.special not in (1, 32, 33, 34):
            return False

    # do something  
    # MANUALS
    if line.special in (1, 26, 27, 28, 31, 32, 33, 34, 117, 118):
        p_doors.EV_VerticalDoor(line, thing)
        
    # SWITCHES
    elif line.special == 7: # Build Stairs
        if p_floor.EV_BuildStairs(line, p_spec.build8):
            P_ChangeSwitchTexture(line, 0)

    elif line.special == 9: # Change Donut
        if p_plats.EV_DoDonut(line):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 11: # Exit level
        P_ChangeSwitchTexture(line, 0)
        g_game.G_ExitLevel()
        
    elif line.special == 14: # Raise Floor 32 and change texture
        if p_plats.EV_DoPlat(line, p_spec.raiseAndChange, 32):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 15: # Raise Floor 24 and change texture
        if p_plats.EV_DoPlat(line, p_spec.raiseAndChange, 24):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 18: # Raise Floor to next highest floor
        if p_floor.EV_DoFloor(line, p_spec.raiseFloorToNearest):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 20: # Raise Plat next highest floor and change texture
        if p_plats.EV_DoPlat(line, p_spec.raiseToNearestAndChange, 0):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 21: # PlatDownWaitUpStay
        if p_plats.EV_DoPlat(line, p_spec.downWaitUpStay, 0):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 23: # Lower Floor to Lowest
        if p_floor.EV_DoFloor(line, p_spec.lowerFloorToLowest):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 29: # Raise Door
        if p_doors.EV_DoDoor(line, p_spec.vld_normal):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 41: # Lower Ceiling to Floor
        if p_ceilng.EV_DoCeiling(line, p_spec.lowerToFloor):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 71: # Turbo Lower Floor
        if p_floor.EV_DoFloor(line, p_spec.turboLower):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 49: # Ceiling Crush And Raise
        if p_ceilng.EV_DoCeiling(line, p_spec.crushAndRaise):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 50: # Close Door
        if p_doors.EV_DoDoor(line, p_spec.vld_close):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 51: # Secret EXIT
        P_ChangeSwitchTexture(line, 0)
        g_game.G_SecretExitLevel()
        
    elif line.special == 55: # Raise Floor Crush
        if p_floor.EV_DoFloor(line, p_spec.raiseFloorCrush):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 101: # Raise Floor
        if p_floor.EV_DoFloor(line, p_spec.raiseFloor):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 102: # Lower Floor to Surrounding floor height
        if p_floor.EV_DoFloor(line, p_spec.lowerFloor):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 103: # Open Door
        if p_doors.EV_DoDoor(line, p_spec.vld_open):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 111: # Blazing Door Raise (faster than TURBO!)
        if p_doors.EV_DoDoor(line, p_spec.vld_blazeRaise):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 112: # Blazing Door Open (faster than TURBO!)
        if p_doors.EV_DoDoor(line, p_spec.vld_blazeOpen):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 113: # Blazing Door Close (faster than TURBO!)
        if p_doors.EV_DoDoor(line, p_spec.vld_blazeClose):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 122: # Blazing PlatDownWaitUpStay
        if p_plats.EV_DoPlat(line, p_spec.blazeDWUS, 0):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 127: # Build Stairs Turbo 16
        if p_floor.EV_BuildStairs(line, p_spec.turbo16):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 131: # Raise Floor Turbo
        if p_floor.EV_DoFloor(line, p_spec.raiseFloorTurbo):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special in (133, 135, 137): # BlzOpenDoor BLUE / RED / YELLOW
        if p_doors.EV_DoLockedDoor(line, p_spec.vld_blazeOpen, thing):
            P_ChangeSwitchTexture(line, 0)
            
    elif line.special == 140: # Raise Floor 512
        if p_floor.EV_DoFloor(line, p_spec.raiseFloor512):
            P_ChangeSwitchTexture(line, 0)
            
    # BUTTONS
    elif line.special == 42: # Close Door
        if p_doors.EV_DoDoor(line, p_spec.vld_close):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 43: # Lower Ceiling to Floor
        if p_ceilng.EV_DoCeiling(line, p_spec.lowerToFloor):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 45: # Lower Floor to Surrounding floor height
        if p_floor.EV_DoFloor(line, p_spec.lowerFloor):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 60: # Lower Floor to Lowest
        if p_floor.EV_DoFloor(line, p_spec.lowerFloorToLowest):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 61: # Open Door
        if p_doors.EV_DoDoor(line, p_spec.vld_open):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 62: # PlatDownWaitUpStay
        if p_plats.EV_DoPlat(line, p_spec.downWaitUpStay, 1):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 63: # Raise Door
        if p_doors.EV_DoDoor(line, p_spec.vld_normal):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 64: # Raise Floor to ceiling
        if p_floor.EV_DoFloor(line, p_spec.raiseFloor):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 66: # Raise Floor 24 and change texture
        if p_plats.EV_DoPlat(line, p_spec.raiseAndChange, 24):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 67: # Raise Floor 32 and change texture
        if p_plats.EV_DoPlat(line, p_spec.raiseAndChange, 32):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 65: # Raise Floor Crush
        if p_floor.EV_DoFloor(line, p_spec.raiseFloorCrush):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 68: # Raise Plat to next highest floor and change texture
        if p_plats.EV_DoPlat(line, p_spec.raiseToNearestAndChange, 0):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 69: # Raise Floor to next highest floor
        if p_floor.EV_DoFloor(line, p_spec.raiseFloorToNearest):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 70: # Turbo Lower Floor
        if p_floor.EV_DoFloor(line, p_spec.turboLower):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 114: # Blazing Door Raise (faster than TURBO!)
        if p_doors.EV_DoDoor(line, p_spec.vld_blazeRaise):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 115: # Blazing Door Open (faster than TURBO!)
        if p_doors.EV_DoDoor(line, p_spec.vld_blazeOpen):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 116: # Blazing Door Close (faster than TURBO!)
        if p_doors.EV_DoDoor(line, p_spec.vld_blazeClose):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 123: # Blazing PlatDownWaitUpStay
        if p_plats.EV_DoPlat(line, p_spec.blazeDWUS, 0):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 132: # Raise Floor Turbo
        if p_floor.EV_DoFloor(line, p_spec.raiseFloorTurbo):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special in (99, 134, 136): # BlzOpenDoor BLUE / RED / YELLOW
        if p_doors.EV_DoLockedDoor(line, p_spec.vld_blazeOpen, thing):
            P_ChangeSwitchTexture(line, 1)
            
    elif line.special == 138: # Light Turn On
        p_lights.EV_LightTurnOn(line, 255)
        P_ChangeSwitchTexture(line, 1)
        
    elif line.special == 139: # Light Turn Off
        p_lights.EV_LightTurnOn(line, 35)
        P_ChangeSwitchTexture(line, 1)
            
    return True
