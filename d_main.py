GS_LEVEL = 0
GS_INTERMISSION = 1
GS_FINALE = 2
GS_DEMOSCREEN = 3
import wad
HUSTR_KEYGREEN = ord("g")
HUSTR_KEYINDIGO = ord("i")
HUSTR_KEYBROWN = ord("b")
HUSTR_KEYRED = ord("r")
import i_sound
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
#	DOOM main program (D_DoomMain) and game loop (D_DoomLoop),
#	plus functions to determine game mode (shareware, registered),
#	parse command line parameters, configure game parameters (turbo),
#	and call the startup functions.
from doomdef import GameVersion
exe_doom_1_2 = GameVersion.exe_doom_1_2
exe_doom_1_5 = GameVersion.exe_doom_1_5
exe_doom_1_666 = GameVersion.exe_doom_1_666
exe_doom_1_7 = GameVersion.exe_doom_1_7
exe_doom_1_8 = GameVersion.exe_doom_1_8
exe_doom_1_9 = GameVersion.exe_doom_1_9
exe_hacx = GameVersion.exe_hacx
exe_ultimate = GameVersion.exe_ultimate
exe_final = GameVersion.exe_final
exe_final2 = GameVersion.exe_final2
exe_chex = GameVersion.exe_chex
#

import sys
import os

import doomdef
import doomstat
import d_iwad
import z_zone
import w_wad
import s_sound
import v_video
import f_finale
import f_wipe
import m_argv
import m_config
import m_controls
import m_misc
import m_menu
import p_saveg
import i_input
import i_joystick
import i_system
import i_timer
import i_video
import g_game
import hu_stuff
import wi_stuff
import st_stuff
import am_map
import d_net
import p_setup
import r_main
import deh_str
import statdump

from doomdef import *
from doomstat import *
from dstrings import *
from sounds import *

#
# GLOBAL VARIABLES
#

gameaction = ga_nothing
advancedemo = False
pagename = ""

gamedescription = ""

# Location where savegames are stored
savegamedir = ""

# location of IWAD and WAD files
iwadfile = ""

devparm = False        # started game with -devparm
nomonsters = False     # checkparm of -nomonsters
respawnparm = False    # checkparm of -respawn
fastparm = False       # checkparm of -fast

startskill = sk_medium
startepisode = 1
startmap = 1
autostart = False
startloadgame = -1

# Store demo, do not accept any inputs
storedemo = False

# If true, the main game loop has started.
main_loop_started = False

show_endoom = 1
show_diskicon = 1

# wipegamestate can be set to -1 to force a wipe on the next draw
wipegamestate = GameState.DEMOSCREEN

# Statics for D_Display
viewactivestate = False
menuactivestate = False
inhelpscreensstate = False
fullscreen = False
oldgamestate = -1
borderdrawcount = 0

# Statics for D_RunFrame
wipestart = 0
wipe = False

# Demo sequence variables
demosequence = 0
pagetic = 0

title = ""


#
# D_ProcessEvents
# Send all the events of the given timestamp down the responder chain
#
def D_ProcessEvents():
    # IF STORE DEMO, DO NOT ACCEPT INPUT
    if storedemo:
        return
        
    while True:
        ev = d_net.D_PopEvent()
        if ev is None:
            break
            
        if m_menu.M_Responder(ev):
            continue               # menu ate the event
        g_game.G_Responder(ev)


#
# D_Display
#  draw current display, possibly wiping it from the previous
#
def D_Display():
    global viewactivestate, menuactivestate, inhelpscreensstate, fullscreen
    global oldgamestate, borderdrawcount, wipegamestate
    
    redrawsbar = False
    
    # change the view size if needed
    if doomstat.setsizeneeded:
        r_main.R_ExecuteSetViewSize()
        oldgamestate = -1                      # force background redraw
        borderdrawcount = 3

    # save the current screen if about to wipe
    if doomstat.gamestate != wipegamestate:
        wipe_flag = True
        f_wipe.wipe_StartScreen(0, 0, doomdef.SCREENWIDTH, doomdef.SCREENHEIGHT)
    else:
        wipe_flag = False

    if doomstat.gamestate == GS_LEVEL and doomstat.gametic:
        hu_stuff.HU_Erase()
    
    # do buffered drawing
    if doomstat.gamestate == GS_LEVEL:
        if doomstat.gametic:
            if doomstat.automapactive:
                am_map.AM_Drawer()
            if wipe_flag or (doomstat.viewheight != doomdef.SCREENHEIGHT and fullscreen):
                redrawsbar = True
            if inhelpscreensstate and not doomstat.inhelpscreens:
                redrawsbar = True              # just put away the help screen
            st_stuff.ST_Drawer(doomstat.viewheight == doomdef.SCREENHEIGHT, redrawsbar)
            fullscreen = doomstat.viewheight == doomdef.SCREENHEIGHT

    elif doomstat.gamestate == GS_INTERMISSION:
        wi_stuff.WI_Drawer()

    elif doomstat.gamestate == GS_FINALE:
        f_finale.F_Drawer()

    elif doomstat.gamestate == GameState.DEMOSCREEN:
        D_PageDrawer()
    
    # draw buffered stuff to screen
    i_video.I_UpdateNoBlit()
    
    # draw the view directly
    if doomstat.gamestate == GS_LEVEL and not doomstat.automapactive and doomstat.gametic:
        r_main.R_RenderPlayerView(doomstat.players[doomstat.displayplayer])

    if doomstat.gamestate == GS_LEVEL and doomstat.gametic:
        hu_stuff.HU_Drawer()
    
    # clean up border stuff
    if doomstat.gamestate != oldgamestate and doomstat.gamestate != GS_LEVEL:
        i_video.I_SetPalette(w_wad.W_CacheLumpName(deh_str.DEH_String("PLAYPAL"), z_zone.PU_CACHE))

    # see if the border needs to be initially drawn
    if doomstat.gamestate == GS_LEVEL and oldgamestate != GS_LEVEL:
        viewactivestate = False        # view was not active
        r_main.R_FillBackScreen()      # draw the pattern into the back screen

    # see if the border needs to be updated to the screen
    if doomstat.gamestate == GS_LEVEL and not doomstat.automapactive and doomstat.scaledviewwidth != doomdef.SCREENWIDTH:
        if doomstat.menuactive or menuactivestate or not viewactivestate:
            borderdrawcount = 3
        if borderdrawcount:
            r_main.R_DrawViewBorder()    # erase old menu stuff
            borderdrawcount -= 1

    if doomstat.testcontrols:
        # Box showing current mouse speed
        v_video.V_DrawMouseSpeedBox(doomstat.testcontrols_mousespeed)

    menuactivestate = doomstat.menuactive
    viewactivestate = doomstat.viewactive
    inhelpscreensstate = doomstat.inhelpscreens
    oldgamestate = wipegamestate = doomstat.gamestate
    
    # draw pause pic
    if doomstat.paused:
        if doomstat.automapactive:
            y = 4
        else:
            y = doomstat.viewwindowy + 4
        v_video.V_DrawPatchDirect(doomstat.viewwindowx + (doomstat.scaledviewwidth - 68) // 2, y,
                                  w_wad.W_CacheLumpName(deh_str.DEH_String("M_PAUSE"), z_zone.PU_CACHE))

    # menus go directly to the screen
    m_menu.M_Drawer()          # menu is drawn even on top of everything
    d_net.NetUpdate()          # send out any new accumulation

    return wipe_flag


def EnableLoadingDisk():
    if show_diskicon:
        if m_argv.M_CheckParm("-cdrom") > 0:
            disk_lump_name = deh_str.DEH_String("STCDROM")
        else:
            disk_lump_name = deh_str.DEH_String("STDISK")

        v_video.V_EnableLoadingDisk(disk_lump_name,
                                    doomdef.SCREENWIDTH - v_video.LOADING_DISK_W,
                                    doomdef.SCREENHEIGHT - v_video.LOADING_DISK_H)


#
# Add configuration file variable bindings.
#
chat_macro_defaults = [
    HUSTR_CHATMACRO0, HUSTR_CHATMACRO1, HUSTR_CHATMACRO2,
    HUSTR_CHATMACRO3, HUSTR_CHATMACRO4, HUSTR_CHATMACRO5,
    HUSTR_CHATMACRO6, HUSTR_CHATMACRO7, HUSTR_CHATMACRO8,
    HUSTR_CHATMACRO9
]

def D_BindVariables():
    m_config.M_ApplyPlatformDefaults()

    i_input.I_BindInputVariables()
    i_video.I_BindVideoVariables()
    i_joystick.I_BindJoystickVariables()
    i_sound.I_BindSoundVariables()

    m_controls.M_BindBaseControls()
    m_controls.M_BindWeaponControls()
    m_controls.M_BindMapControls()
    m_controls.M_BindMenuControls()
    m_controls.M_BindChatControls(MAXPLAYERS)

    doomstat.key_multi_msgplayer[0] = HUSTR_KEYGREEN
    doomstat.key_multi_msgplayer[1] = HUSTR_KEYINDIGO
    doomstat.key_multi_msgplayer[2] = HUSTR_KEYBROWN
    doomstat.key_multi_msgplayer[3] = HUSTR_KEYRED

    d_net.I_BindNetVariables()

    m_config.M_BindIntVariable("mouse_sensitivity", doomstat, "mouseSensitivity")
    m_config.M_BindIntVariable("sfx_volume", s_sound, "sfxVolume")
    m_config.M_BindIntVariable("music_volume", s_sound, "musicVolume")
    m_config.M_BindIntVariable("show_messages", doomstat, "showMessages")
    m_config.M_BindIntVariable("screenblocks", doomstat, "screenblocks")
    m_config.M_BindIntVariable("detaillevel", doomstat, "detailLevel")
    m_config.M_BindIntVariable("snd_channels", s_sound, "snd_channels")
    m_config.M_BindIntVariable("vanilla_savegame_limit", p_saveg, "vanilla_savegame_limit")
    m_config.M_BindIntVariable("vanilla_demo_limit", g_game, "vanilla_demo_limit")
    
    global show_endoom, show_diskicon
    m_config.M_BindIntVariable("show_endoom", sys.modules[__name__], "show_endoom")
    m_config.M_BindIntVariable("show_diskicon", sys.modules[__name__], "show_diskicon")

    # Multiplayer chat macros
    for i in range(10):
        doomstat.chat_macros[i] = m_misc.M_StringDuplicate(chat_macro_defaults[i])
        m_config.M_BindStringVariable(f"chatmacro{i}", doomstat.chat_macros, i)


#
# D_GrabMouseCallback
#
def D_GrabMouseCallback():
    # Drone players don't need mouse focus
    if doomstat.drone:
        return False

    # when menu is active or game is paused, release the mouse 
    if doomstat.menuactive or doomstat.paused:
        return False

    # only grab mouse when playing levels (but not demos)
    return (doomstat.gamestate == GS_LEVEL) and not doomstat.demoplayback and not advancedemo


#
#  D_RunFrame
#
def D_RunFrame():
    if advancedemo:
        D_DoAdvanceDemo()
    global wipestart, wipe
    
    if wipe:
        while True:
            nowtime = i_timer.I_GetTime()
            tics = nowtime - wipestart
            i_timer.I_Sleep(1)
            if tics > 0:
                break

        wipestart = nowtime
        wipe = not f_wipe.wipe_ScreenWipe(f_wipe.wipe_Melt, 0, 0, doomdef.SCREENWIDTH, doomdef.SCREENHEIGHT, tics)
        i_video.I_UpdateNoBlit()
        m_menu.M_Drawer()                            # menu is drawn even on top of wipes
        i_video.I_FinishUpdate()                      # page flip or blit buffer
        return

    # frame syncronous IO operations
    i_video.I_StartFrame()

    d_net.TryRunTics() # will run at least one tic

    player = doomstat.players[doomstat.consoleplayer] if doomstat.players else None; s_sound.S_UpdateSounds(player.mo if player else None) # move positional sounds

    # Update display, next frame, with current state if no profiling is on
    if doomstat.screenvisible and not doomstat.nodrawers:
        wipe = D_Display()
        if wipe:
            # start wipe on this frame
            f_wipe.wipe_EndScreen(0, 0, doomdef.SCREENWIDTH, doomdef.SCREENHEIGHT)
            wipestart = i_timer.I_GetTime() - 1
        else:
            # normal update
            i_video.I_FinishUpdate()              # page flip or blit buffer


#
#  D_DoomLoop
#
def D_DoomLoop():
    global main_loop_started, wipegamestate
    
    if doomstat.gamevariant == doomstat.bfgedition and (doomstat.demorecording or (gameaction == ga_playdemo) or doomstat.netgame):
        sys.stdout.write(" WARNING: You are playing using one of the Doom Classic\n"
                         " IWAD files shipped with the Doom 3: BFG Edition. These are\n"
                         " known to be incompatible with the regular IWAD files and\n"
                         " may cause demos and network games to get out of sync.\n")

    if doomstat.demorecording:
        g_game.G_BeginRecording()

    main_loop_started = True

    i_video.I_SetWindowTitle(gamedescription)
    i_video.I_GraphicsCheckCommandLine()
    i_video.I_SetGrabMouseCallback(D_GrabMouseCallback)
    
    try:
        from doom_icon import doom_icon_data, doom_icon_w, doom_icon_h
        i_video.I_RegisterWindowIcon(doom_icon_data, doom_icon_w, doom_icon_h)
    except ImportError:
        pass
        
    i_video.I_InitGraphics()
    EnableLoadingDisk()

    d_net.TryRunTics()

    v_video.V_RestoreBuffer()
    r_main.R_ExecuteSetViewSize()


    if doomstat.testcontrols:
        wipegamestate = doomstat.gamestate

    while True:
        D_RunFrame()


#
#  DEMO LOOP
#

def D_PageTicker():
    global pagetic
    pagetic -= 1
    if pagetic < 0:
        D_AdvanceDemo()

def D_PageDrawer():
    v_video.V_DrawPatch(0, 0, w_wad.W_CacheLumpName(pagename, z_zone.PU_CACHE))

def D_AdvanceDemo():
    global pagename, pagetic, demosequence, advancecount
    global advancedemo
    advancedemo = True

def D_DoAdvanceDemo():
    global demosequence, pagetic, pagename, advancedemo
    
    from d_player import player_t
    if doomstat.players[doomstat.consoleplayer] is None:
        doomstat.players[doomstat.consoleplayer] = player_t()
    doomstat.players[doomstat.consoleplayer].playerstate = PST_LIVE  # not reborn
    advancedemo = False
    doomstat.usergame = False               # no save / end game here
    doomstat.paused = False
    global gameaction
    gameaction = ga_nothing

    if doomstat.gameversion == exe_ultimate or doomstat.gameversion == exe_final:
        demosequence = (demosequence + 1) % 7
    else:
        demosequence = (demosequence + 1) % 6
    
    if demosequence == 0:
        if doomstat.gamemode == doomstat.commercial:
            pagetic = TICRATE * 11
        else:
            pagetic = 170
        doomstat.gamestate = GameState.DEMOSCREEN
        pagename = deh_str.DEH_String("TITLEPIC")
        if doomstat.gamemode == doomstat.commercial:
            s_sound.S_StartMusic(mus_dm2ttl)
        else:
            s_sound.S_StartMusic(mus_intro)
            
    elif demosequence == 1:
        g_game.G_DeferedPlayDemo(deh_str.DEH_String("demo1"))
        
    elif demosequence == 2:
        pagetic = 200
        doomstat.gamestate = GameState.DEMOSCREEN
        pagename = deh_str.DEH_String("CREDIT")
        
    elif demosequence == 3:
        g_game.G_DeferedPlayDemo(deh_str.DEH_String("demo2"))
        
    elif demosequence == 4:
        doomstat.gamestate = GameState.DEMOSCREEN
        if doomstat.gamemode == doomstat.commercial:
            pagetic = TICRATE * 11
            pagename = deh_str.DEH_String("TITLEPIC")
            s_sound.S_StartMusic(mus_dm2ttl)
        else:
            pagetic = 200
            if doomstat.gameversion >= exe_ultimate:
                pagename = deh_str.DEH_String("CREDIT")
            else:
                pagename = deh_str.DEH_String("HELP2")
                
    elif demosequence == 5:
        g_game.G_DeferedPlayDemo(deh_str.DEH_String("demo3"))
        
    elif demosequence == 6:
        g_game.G_DeferedPlayDemo(deh_str.DEH_String("demo4"))

    # The Doom 3: BFG Edition version of doom2.wad does not have a
    # TITLETPIC lump. Use INTERPIC instead as a workaround.
    if doomstat.gamevariant == doomstat.bfgedition and pagename.lower() == "titlepic" and \
       w_wad.W_CheckNumForName("titlepic") < 0:
        pagename = deh_str.DEH_String("INTERPIC")

def D_StartTitle():
    global gameaction, demosequence
    gameaction = ga_nothing
    demosequence = -1
    D_AdvanceDemo()


banners = [
    # doom2.wad
    "                         "
    "DOOM 2: Hell on Earth v%i.%i"
    "                           ",
    # doom2.wad v1.666
    "                         "
    "DOOM 2: Hell on Earth v%i.%i66"
    "                          ",
    # doom1.wad
    "                            "
    "DOOM Shareware Startup v%i.%i"
    "                           ",
    # doom.wad
    "                            "
    "DOOM Registered Startup v%i.%i"
    "                           ",
    # Registered DOOM uses this
    "                          "
    "DOOM System Startup v%i.%i"
    "                          ",
    # Doom v1.666
    "                          "
    "DOOM System Startup v%i.%i66"
    "                          ",
    # doom.wad (Ultimate DOOM)
    "                         "
    "The Ultimate DOOM Startup v%i.%i"
    "                        ",
    # tnt.wad
    "                     "
    "DOOM 2: TNT - Evilution v%i.%i"
    "                           ",
    # plutonia.wad
    "                   "
    "DOOM 2: Plutonia Experiment v%i.%i"
    "                           "
]

def GetGameName(gamename):
    for i in range(len(banners)):
        deh_sub = deh_str.DEH_String(banners[i])
        if deh_sub != banners[i]:
            version = g_game.G_VanillaVersionCode()
            deh_gamename = banners[i].replace("%i.%i", f"{version // 100}.{version % 100}")
            return deh_gamename.strip()
    return gamename

def SetMissionForPackName(pack_name):
    packs = {
        "doom2": doomstat.doom2,
        "tnt": doomstat.pack_tnt,
        "plutonia": doomstat.pack_plut
    }
    
    if pack_name.lower() in packs:
        doomstat.gamemission = packs[pack_name.lower()]
        return

    sys.stdout.write("Valid mission packs are:\n")
    for k in packs:
        sys.stdout.write(f"\t{k}\n")
    i_system.I_Error(f"Unknown mission pack name: {pack_name}")

def D_IdentifyVersion():
    if doomstat.gamemission == doomstat.none:
        for i in range(doomstat.numlumps):
            if doomstat.lumpinfo[i].name.lower().startswith("map01"):
                doomstat.gamemission = doomstat.doom2
                break
            elif doomstat.lumpinfo[i].name.lower().startswith("e1m1"):
                doomstat.gamemission = doomstat.doom
                break
                
        if doomstat.gamemission == doomstat.none:
            i_system.I_Error("Unknown or invalid IWAD file.")

    if doomstat.logical_gamemission() == doomstat.doom:
        if w_wad.W_CheckNumForName("E4M1") > 0:
            doomstat.gamemode = doomstat.retail
        elif w_wad.W_CheckNumForName("E3M1") > 0:
            doomstat.gamemode = doomstat.registered
        else:
            doomstat.gamemode = doomstat.shareware
    else:
        doomstat.gamemode = doomstat.commercial
        p = m_argv.M_CheckParmWithArgs("-pack", 1)
        if p > 0:
            SetMissionForPackName(m_argv.myargv[p + 1])

def D_SetGameDescription():
    global gamedescription
    
    if doomstat.logical_gamemission() == doomstat.doom:
        if doomstat.gamevariant == doomstat.freedoom:
            gamedescription = GetGameName("Freedoom: Phase 1")
        elif doomstat.gamemode == doomstat.retail:
            gamedescription = GetGameName("The Ultimate DOOM")
        elif doomstat.gamemode == doomstat.registered:
            gamedescription = GetGameName("DOOM Registered")
        elif doomstat.gamemode == doomstat.shareware:
            gamedescription = GetGameName("DOOM Shareware")
    else:
        if doomstat.gamevariant == doomstat.freedm:
            gamedescription = GetGameName("FreeDM")
        elif doomstat.gamevariant == doomstat.freedoom:
            gamedescription = GetGameName("Freedoom: Phase 2")
        elif doomstat.logical_gamemission() == doomstat.doom2:
            gamedescription = GetGameName("DOOM 2: Hell on Earth")
        elif doomstat.logical_gamemission() == doomstat.pack_plut:
            gamedescription = GetGameName("DOOM 2: Plutonia Experiment")
        elif doomstat.logical_gamemission() == doomstat.pack_tnt:
            gamedescription = GetGameName("DOOM 2: TNT - Evilution")

    if not gamedescription:
        gamedescription = "Unknown"


def D_AddFile(filename):
    sys.stdout.write(f" adding {filename}\n")
    handle = w_wad.W_AddFile(filename)
    return handle is not None

copyright_banners = [
    "===========================================================================\n"
    "ATTENTION:  This version of DOOM has been modified.  If you would like to\n"
    "get a copy of the original game, call 1-800-IDGAMES or see the readme file.\n"
    "        You will not receive technical support for modified games.\n"
    "                      press enter to continue\n"
    "===========================================================================\n",

    "===========================================================================\n"
    "                 Commercial product - do not distribute!\n"
    "         Please report software piracy to the SPA: 1-800-388-PIR8\n"
    "===========================================================================\n",

    "===========================================================================\n"
    "                                Shareware!\n"
    "===========================================================================\n"
]

def PrintDehackedBanners():
    for banner in copyright_banners:
        deh_s = deh_str.DEH_String(banner)
        if deh_s != banner:
            sys.stdout.write(deh_s)
            if not deh_s.endswith('\n'):
                sys.stdout.write('\n')

gameversions = [
    ("Doom 1.2",             "1.2",        exe_doom_1_2),
    ("Doom 1.5",             "1.5",        exe_doom_1_5),
    ("Doom 1.666",           "1.666",      exe_doom_1_666),
    ("Doom 1.7/1.7a",        "1.7",        exe_doom_1_7),
    ("Doom 1.8",             "1.8",        exe_doom_1_8),
    ("Doom 1.9",             "1.9",        exe_doom_1_9),
    ("Hacx",                 "hacx",       exe_hacx),
    ("Ultimate Doom",        "ultimate",   exe_ultimate),
    ("Final Doom",           "final",      exe_final),
    ("Final Doom (alt)",     "final2",     exe_final2),
    ("Chex Quest",           "chex",       exe_chex)
]

def InitGameVersion():
    p = m_argv.M_CheckParmWithArgs("-gameversion", 1)

    if p:
        ver_str = m_argv.myargv[p+1]
        for desc, cmdline, ver in gameversions:
            if ver_str == cmdline:
                doomstat.gameversion = ver
                break
        else:
            sys.stdout.write("Supported game versions:\n")
            for desc, cmdline, ver in gameversions:
                sys.stdout.write(f"\t{cmdline} ({desc})\n")
            i_system.I_Error(f"Unknown game version '{ver_str}'")
    else:
        # Determine automatically
        if doomstat.gamemission == doomstat.pack_chex:
            doomstat.gameversion = exe_chex
        elif doomstat.gamemission == doomstat.pack_hacx:
            doomstat.gameversion = exe_hacx
        elif doomstat.gamemode in (doomstat.shareware, doomstat.registered) or \
             (doomstat.gamemode == doomstat.commercial and doomstat.gamemission == doomstat.doom2):
            
            doomstat.gameversion = exe_doom_1_9
            for i in range(1, 4):
                demolumpname = f"demo{i}"
                if w_wad.W_CheckNumForName(demolumpname) > 0:
                    demolump = w_wad.W_CacheLumpName(demolumpname, z_zone.PU_STATIC)
                    demoversion = demolump[0]
                    
                    status = True
                    if demoversion in (0, 1, 2, 3, 4):
                        doomstat.gameversion = exe_doom_1_2
                    elif demoversion == 106:
                        doomstat.gameversion = exe_doom_1_666
                    elif demoversion == 107:
                        doomstat.gameversion = exe_doom_1_7
                    elif demoversion == 108:
                        doomstat.gameversion = exe_doom_1_8
                    elif demoversion == 109:
                        doomstat.gameversion = exe_doom_1_9
                    else:
                        status = False
                    
                    if status:
                        break
        elif doomstat.gamemode == doomstat.retail:
            doomstat.gameversion = exe_ultimate
        elif doomstat.gamemode == doomstat.commercial:
            doomstat.gameversion = exe_final

    if doomstat.gameversion <= exe_doom_1_2 and doomstat.deathmatch == 2:
        doomstat.deathmatch = 1

    if doomstat.gameversion < exe_ultimate and doomstat.gamemode == doomstat.retail:
        doomstat.gamemode = doomstat.registered

    if doomstat.gameversion < exe_final and doomstat.gamemode == doomstat.commercial and \
       doomstat.gamemission in (doomstat.pack_tnt, doomstat.pack_plut):
        doomstat.gamemission = doomstat.doom2


def PrintGameVersion():
    for desc, cmdline, ver in gameversions:
        if ver == doomstat.gameversion:
            sys.stdout.write(f"Emulating the behavior of the '{desc}' executable.\n")
            break

def D_Endoom():
    if not show_endoom or not main_loop_started or i_system.screensaver_mode or m_argv.M_CheckParm("-testcontrols") > 0:
        return
    endoom = w_wad.W_CacheLumpName(deh_str.DEH_String("ENDOOM"), z_zone.PU_STATIC)
    i_system.I_Endoom(endoom)

def IsFrenchIWAD():
    return (doomstat.gamemission == doomstat.doom2 and w_wad.W_CheckNumForName("M_RDTHIS") < 0 and
            w_wad.W_CheckNumForName("M_EPISOD") < 0 and w_wad.W_CheckNumForName("M_EPI1") < 0 and
            w_wad.W_CheckNumForName("M_EPI2") < 0 and w_wad.W_CheckNumForName("M_EPI3") < 0 and
            w_wad.W_CheckNumForName("WIOSTF") < 0 and w_wad.W_CheckNumForName("WIOBJ") >= 0)

def LoadIwadDeh():
    if doomstat.gamevariant in (doomstat.freedoom, doomstat.freedm):
        deh_str.DEH_LoadLumpByName("DEHACKED", False, True)

    if doomstat.gameversion == exe_hacx:
        if not deh_str.DEH_LoadLumpByName("DEHACKED", True, False):
            i_system.I_Error("DEHACKED lump not found. Please check that this is the Hacx v1.2 IWAD.")

    if doomstat.gameversion == exe_chex:
        dirname = os.path.dirname(iwadfile)
        chex_deh = os.path.join(dirname, "chex.deh")
        if not os.path.exists(chex_deh):
            chex_deh = d_iwad.D_FindWADByName("chex.deh")
            
        if chex_deh is None:
            i_system.I_Error("Unable to find Chex Quest dehacked file (chex.deh).")
            
        if not deh_str.DEH_LoadFile(chex_deh):
            i_system.I_Error("Failed to load chex.deh needed for emulating chex.exe.")

    if IsFrenchIWAD():
        dirname = os.path.dirname(iwadfile)
        french_deh = os.path.join(dirname, "french.deh")
        sys.stdout.write("French version\n")
        
        if not os.path.exists(french_deh):
            french_deh = d_iwad.D_FindWADByName("french.deh")
            
        if french_deh is None:
            i_system.I_Error("Unable to find French Doom II dehacked file (french.deh).")
            
        if not deh_str.DEH_LoadFile(french_deh):
            i_system.I_Error("Failed to load french.deh needed for emulating French doom2.exe.")

def G_CheckDemoStatusAtExit():
    g_game.G_CheckDemoStatus()

#
# D_DoomMain
#
def D_DoomMain():
    global nomonsters, respawnparm, fastparm, devparm
    global startskill, startepisode, startmap, autostart, startloadgame
    global storedemo, savegamedir, iwadfile

    i_system.I_AtExit(D_Endoom, False)

    # print banner
    i_system.I_PrintBanner(doomdef.PACKAGE_STRING)

    sys.stdout.write("Z_Init: Init zone memory allocation daemon. \n"); __import__("doom_progress").set(10)
    z_zone.Z_Init()

    if m_argv.M_CheckParm("-dedicated") > 0:
        sys.stdout.write("Dedicated server mode.\n")
        import net_dedicated
        net_dedicated.NET_DedicatedServer()

    if m_argv.M_CheckParm("-search"):
        import net_query
        net_query.NET_MasterQuery()
        sys.exit(0)

    p = m_argv.M_CheckParmWithArgs("-query", 1)
    if p:
        import net_query
        net_query.NET_QueryAddress(m_argv.myargv[p+1])
        sys.exit(0)

    if m_argv.M_CheckParm("-localsearch"):
        import net_query
        net_query.NET_LANQuery()
        sys.exit(0)

    nomonsters = bool(m_argv.M_CheckParm("-nomonsters"))
    respawnparm = bool(m_argv.M_CheckParm("-respawn"))
    fastparm = bool(m_argv.M_CheckParm("-fast"))
    devparm = bool(m_argv.M_CheckParm("-devparm"))

    i_system.I_DisplayFPSDots(devparm)

    if m_argv.M_CheckParm("-deathmatch"):
        doomstat.deathmatch = 1

    if m_argv.M_CheckParm("-altdeath"):
        doomstat.deathmatch = 2

    if devparm:
        sys.stdout.write(D_DEVSTR)
    
    if m_argv.M_ParmExists("-cdrom"):
        sys.stdout.write(D_CDROM)
        m_config.M_SetConfigDir("c:\\doomdata\\")
    else:
        m_config.M_SetConfigDir(None)

    p = m_argv.M_CheckParm("-turbo")
    if p:
        scale = 200
        if p < len(m_argv.myargv) - 1:
            scale = int(m_argv.myargv[p+1])
        scale = max(10, min(400, scale))
        sys.stdout.write(f"turbo scale: {scale}%\n")
        doomstat.forwardmove[0] = doomstat.forwardmove[0] * scale // 100
        doomstat.forwardmove[1] = doomstat.forwardmove[1] * scale // 100
        doomstat.sidemove[0] = doomstat.sidemove[0] * scale // 100
        doomstat.sidemove[1] = doomstat.sidemove[1] * scale // 100
    
    sys.stdout.write("V_Init: allocate screens.\n"); __import__("doom_progress").set(20)
    v_video.V_Init()

    sys.stdout.write("M_LoadDefaults: Load system defaults.\n"); __import__("doom_progress").set(30)
    m_config.M_SetConfigFilenames("default.cfg", doomdef.PROGRAM_PREFIX + "doom.cfg")
    D_BindVariables()
    m_config.M_LoadDefaults()

    i_system.I_AtExit(m_config.M_SaveDefaults, False)

    iwadfile = d_iwad.D_FindIWAD(d_iwad.IWAD_MASK_DOOM, sys.modules[__name__]) # Pass mock ref or fix

    if not iwadfile:
        i_system.I_Error("Game mode indeterminate. No IWAD file was found.")

    doomstat.modifiedgame = False

    sys.stdout.write("W_Init: Init WADfiles.\n"); __import__("doom_progress").set(50)
    D_AddFile(iwadfile)

    w_wad.W_CheckCorrectIWAD(doomstat.doom)

    D_IdentifyVersion()
    InitGameVersion()

    if w_wad.W_CheckNumForName("FREEDOOM") >= 0:
        if w_wad.W_CheckNumForName("FREEDM") >= 0:
            doomstat.gamevariant = doomstat.freedm
        else:
            doomstat.gamevariant = doomstat.freedoom
    elif w_wad.W_CheckNumForName("DMENUPIC") >= 0:
        doomstat.gamevariant = doomstat.bfgedition

    if not m_argv.M_ParmExists("-nodeh"):
        LoadIwadDeh()

    if doomstat.gamevariant == doomstat.bfgedition:
        sys.stdout.write("BFG Edition: Using workarounds as needed.\n")
        deh_str.DEH_AddStringReplacement(HUSTR_31, "level 31: idkfa")
        deh_str.DEH_AddStringReplacement(HUSTR_32, "level 32: keen")
        deh_str.DEH_AddStringReplacement(PHUSTR_1, "level 33: betray")
        deh_str.DEH_AddStringReplacement("M_GDHIGH", "M_MSGON")
        deh_str.DEH_AddStringReplacement("M_GDLOW", "M_MSGOFF")
        deh_str.DEH_AddStringReplacement("M_SCRNSZ", "M_DISP")

    if not m_argv.M_ParmExists("-noautoload") and doomstat.gamemode != doomstat.shareware:
        if doomstat.gamemission < doomstat.pack_chex:
            autoload_dir = m_config.M_GetAutoloadDir("doom-all")
            if autoload_dir:
                deh_str.DEH_AutoLoadPatches(autoload_dir)
                w_wad.W_AutoLoadWADs(autoload_dir)
                
        autoload_dir = m_config.M_GetAutoloadDir(d_iwad.D_SaveGameIWADName(doomstat.gamemission, doomstat.gamevariant))
        if autoload_dir:
            deh_str.DEH_AutoLoadPatches(autoload_dir)
            w_wad.W_AutoLoadWADs(autoload_dir)

    deh_str.DEH_ParseCommandLine()
    doomstat.modifiedgame = w_wad.W_ParseCommandLine()

    p = m_argv.M_CheckParmWithArgs("-playdemo", 1)
    if not p:
        p = m_argv.M_CheckParmWithArgs("-timedemo", 1)

    demolumpname = ""
    file_name = ""
    if p:
        uc_filename = m_argv.myargv[p + 1].upper()
        if uc_filename.endswith(".LMP"):
            file_name = m_argv.myargv[p + 1]
        else:
            file_name = f"{m_argv.myargv[p+1]}.lmp"

        if D_AddFile(file_name):
            demolumpname = doomstat.lumpinfo[doomstat.numlumps - 1].name
        else:
            demolumpname = m_argv.myargv[p + 1]

        sys.stdout.write(f"Playing demo {file_name}.\n")

    i_system.I_AtExit(G_CheckDemoStatusAtExit, True)
    w_wad.W_GenerateHashTable()

    if m_argv.M_ParmExists("-dehlump"):
        loaded = 0
        numiwadlumps = doomstat.numlumps
        while not w_wad.W_IsIWADLump(doomstat.lumpinfo[numiwadlumps - 1]):
            numiwadlumps -= 1

        for i in range(numiwadlumps, doomstat.numlumps):
            if doomstat.lumpinfo[i].name.startswith("DEHACKED"):
                deh_str.DEH_LoadLump(i, False, False)
                loaded += 1
        sys.stdout.write(f"  loaded {loaded} DEHACKED lumps from PWAD files.\n")

    D_SetGameDescription()
    savegamedir = m_config.M_GetSaveGameDir(d_iwad.D_SaveGameIWADName(doomstat.gamemission, doomstat.gamevariant))

    if doomstat.modifiedgame and doomstat.gamevariant != doomstat.freedoom:
        name = ["e2m1","e2m2","e2m3","e2m4","e2m5","e2m6","e2m7","e2m8","e2m9",
                "e3m1","e3m3","e3m3","e3m4","e3m5","e3m6","e3m7","e3m8","e3m9",
                "dphoof","bfgga0","heada1","cybra1","spida1d1"]
        if doomstat.gamemode == doomstat.shareware:
            i_system.I_Error(deh_str.DEH_String("\nYou cannot -file with the shareware version. Register!"))
        if doomstat.gamemode == doomstat.registered:
            for n in name:
                if w_wad.W_CheckNumForName(n) < 0:
                    i_system.I_Error(deh_str.DEH_String("\nThis is not the registered version."))

    if w_wad.W_CheckNumForName("SS_START") >= 0 or w_wad.W_CheckNumForName("FF_END") >= 0:
        i_system.I_PrintDivider()
        sys.stdout.write(" WARNING: The loaded WAD file contains modified sprites or\n"
                         " floor textures.  You may want to use the '-merge' command\n"
                         " line option instead of '-file'.\n")

    i_system.I_PrintStartupBanner(gamedescription)
    PrintDehackedBanners()

    sys.stdout.write("I_Init: Setting up machine state.\n")
    i_system.I_CheckIsScreensaver()
    i_timer.I_InitTimer()
    i_joystick.I_InitJoystick()
    # Dynamically patch i_system to avoid crashes on missing I_* methods
    if 'i_system' in locals() or 'i_system' in globals():
        _sys = i_system
        for _method in ['I_InitSound', 'I_InitMusic', 'I_InitGraphics', 'I_InitNetwork', 'I_GetTime', 'I_StartTic', 'I_StartFrame', 'I_UpdateNoBlit', 'I_FinishUpdate', 'I_ReadScreen', 'I_SetPalette', 'I_Quit']:
            if not hasattr(_sys, _method):
                setattr(_sys, _method, classmethod(lambda cls, *args, **kwargs: 0) if isinstance(_sys, type) else lambda *args, **kwargs: 0)
        
        # Expose display framebuffer as a bytearray for external hooks (320x200 8-bit paletted)
        if not hasattr(_sys, 'screens'):
            _sys.screens = [bytearray(320 * 200)]

    i_system.I_InitSound(doomstat.doom)
    i_system.I_InitMusic()

    sys.stdout.write("NET_Init: Init network subsystem.\n")
    d_net.NET_Init()

    # D_ConnectNetGame()
    # Stubbed here, assuming NET_Init/Connect handles internal structure or is missing
    
    startskill = sk_medium
    startepisode = 1
    startmap = 1
    autostart = False

    p = m_argv.M_CheckParmWithArgs("-skill", 1)
    if p:
        startskill = int(m_argv.myargv[p+1][0]) - 1
        autostart = True

    p = m_argv.M_CheckParmWithArgs("-episode", 1)
    if p:
        startepisode = int(m_argv.myargv[p+1][0])
        startmap = 1
        autostart = True
        
    doomstat.timelimit = 0

    p = m_argv.M_CheckParmWithArgs("-timer", 1)
    if p:
        doomstat.timelimit = int(m_argv.myargv[p+1])

    if m_argv.M_CheckParm("-avg"):
        doomstat.timelimit = 20

    p = m_argv.M_CheckParmWithArgs("-warp", 1)
    if p:
        if doomstat.gamemode == doomstat.commercial:
            startmap = int(m_argv.myargv[p+1])
        else:
            startepisode = int(m_argv.myargv[p+1][0])
            if p + 2 < len(m_argv.myargv):
                startmap = int(m_argv.myargv[p+2][0])
            else:
                startmap = 1
        autostart = True

    p = m_argv.M_CheckParm("-testcontrols")
    if p > 0:
        startepisode = 1
        startmap = 1
        autostart = True
        doomstat.testcontrols = True

    p = m_argv.M_CheckParmWithArgs("-loadgame", 1)
    if p:
        startloadgame = int(m_argv.myargv[p+1])
    else:
        startloadgame = -1

    sys.stdout.write("M_Init: Init miscellaneous info.\n")
    m_misc.M_Init()

    sys.stdout.write("R_Init: Init DOOM refresh daemon - "); __import__("doom_progress").set(65)
    _iwad_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DOOM1.WAD")
    print("[BSDoom] WAD path:", _iwad_file)
    if "-iwad" in sys.argv:
        _iwad_file = sys.argv[sys.argv.index("-iwad") + 1]
    try:
        wad.load_wad(_iwad_file)
        print(f"✅ Python custom WAD parser loaded: {_iwad_file}")
    except Exception as e:
        print(f"Failed to load wad.py: {e}")
    r_main.R_Init()

    sys.stdout.write("\nP_Init: Init Playloop state.\n"); __import__("doom_progress").set(80)
    p_setup.P_Init()

    sys.stdout.write("S_Init: Setting up sound.\n"); __import__("doom_progress").set(95)
    s_sound.S_Init(s_sound.sfxVolume * 8, s_sound.musicVolume * 8)

    sys.stdout.write("D_CheckNetGame: Checking network game status.\n")
    # d_net.D_CheckNetGame()  # Stubbed if not ported

    PrintGameVersion()

    sys.stdout.write("HU_Init: Setting up heads up display.\n")
    hu_stuff.HU_Init()

    sys.stdout.write("ST_Init: Init status bar.\n")
    st_stuff.ST_Init()

    if doomstat.gamemode == doomstat.commercial and w_wad.W_CheckNumForName("map01") < 0:
        storedemo = True

    if m_argv.M_CheckParmWithArgs("-statdump", 1):
        i_system.I_AtExit(statdump.StatDump, True)
        sys.stdout.write("External statistics registered.\n")

    p = m_argv.M_CheckParmWithArgs("-record", 1)
    if p:
        g_game.G_RecordDemo(m_argv.myargv[p+1])
        autostart = True

    p = m_argv.M_CheckParmWithArgs("-playdemo", 1)
    if p:
        doomstat.singledemo = True
        g_game.G_DeferedPlayDemo(demolumpname)
        D_DoomLoop()
        
    p = m_argv.M_CheckParmWithArgs("-timedemo", 1)
    if p:
        g_game.G_TimeDemo(demolumpname)
        D_DoomLoop()
        
    if startloadgame >= 0:
        file_name = p_saveg.P_SaveGameFile(startloadgame)
        g_game.G_LoadGame(file_name)
        
    if gameaction != ga_loadgame:
        if autostart or doomstat.netgame:
            g_game.G_InitNew(startskill, startepisode, startmap)
        else:
            D_StartTitle()

    D_DoomLoop()


# Auto-patch MockSystem to include I_CheckIsScreensaver
