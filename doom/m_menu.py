# m_menu.py
# Translated DOOM menu system logic

import sys
import os

import doomdef
import doomkeys
import dstrings
import doomstat
import sounds
import m_misc

# In the larger Python port, these dependencies exist to handle engine subsystems:
import i_system
import i_video
import i_timer
import i_joystick
import v_video
import w_wad
import s_sound
import g_game
import r_main
import p_saveg
import m_controls
import deh_main
import hu_stuff

# Defaulted menu configuration values
mouseSensitivity = 5
showMessages = 1
detailLevel = 0
screenblocks = 9
screenSize = 0

quickSaveSlot = -1
messageToPrint = 0
messageString = None
messx = 0
messy = 0
messageLastMenuActive = False
messageNeedsInput = False
messageRoutine = None

GAMMALVL0 = "Gamma correction OFF"
GAMMALVL1 = "Gamma correction level 1"
GAMMALVL2 = "Gamma correction level 2"
GAMMALVL3 = "Gamma correction level 3"
GAMMALVL4 = "Gamma correction level 4"

gammamsg = [
    GAMMALVL0, GAMMALVL1, GAMMALVL2, GAMMALVL3, GAMMALVL4
]

saveStringEnter = 0
saveSlot = 0
saveCharIndex = 0
joypadSave = False
SAVESTRINGSIZE = 24
saveOldString = ""

inhelpscreens = False
menuactive = False

SKULLXOFF = -32
LINEHEIGHT = 16

savegamestrings = ["" for _ in range(10)]
endstring = ""
opldev = False

# MENU TYPEDEFS
class MenuItem:
    def __init__(self, status, name, routine, alphaKey):
        self.status = status
        self.name = name
        self.routine = routine
        self.alphaKey = alphaKey

class MenuDef:
    def __init__(self, numitems, prevMenu, menuitems, routine, x, y, lastOn):
        self.numitems = numitems
        self.prevMenu = prevMenu
        self.menuitems = menuitems
        self.routine = routine
        self.x = x
        self.y = y
        self.lastOn = lastOn

itemOn = 0
skullAnimCounter = 0
whichSkull = 0
skullName = ["M_SKULL1", "M_SKULL2"]
currentMenu = None

epi = 0

# ==================
# MENU LOGIC ROUTINES
# ==================

def M_SetupNextMenu(menudef):
    global currentMenu, itemOn
    currentMenu = menudef
    itemOn = currentMenu.lastOn

def M_ClearMenus():
    global menuactive
    menuactive = False

def M_StartMessage(string_val, routine, input_val):
    global messageLastMenuActive, messageToPrint, messageString, messageRoutine, messageNeedsInput, menuactive
    messageLastMenuActive = menuactive
    messageToPrint = 1
    messageString = string_val
    messageRoutine = routine
    messageNeedsInput = input_val
    menuactive = True

def M_StringWidth(string_val):
    w = 0
    for c in string_val:
        c_val = ord(c.upper()) - hu_stuff.HU_FONTSTART
        if c_val < 0 or c_val >= hu_stuff.HU_FONTSIZE:
            w += 4
        else:
            w += hu_stuff.hu_font[c_val].width
    return w

def M_StringHeight(string_val):
    h = hu_stuff.hu_font[0].height
    for c in string_val:
        if c == '\n':
            h += hu_stuff.hu_font[0].height
    return h

def M_WriteText(x, y, string_val):
    cx, cy = x, y
    for c in string_val:
        if c == '\n':
            cx = x
            cy += 12
            continue
        c_val = ord(c.upper()) - hu_stuff.HU_FONTSTART
        if c_val < 0 or c_val >= hu_stuff.HU_FONTSIZE:
            cx += 4
            continue
        w = hu_stuff.hu_font[c_val].width
        if cx + w > doomdef.SCREENWIDTH:
            break
        v_video.V_DrawPatchDirect(cx, cy, hu_stuff.hu_font[c_val])
        cx += w

def M_DrawThermo(x, y, thermWidth, thermDot):
    xx = x
    v_video.V_DrawPatchDirect(xx, y, w_wad.W_CacheLumpName(deh_main.DEH_String("M_THERML"), doomdef.PU_CACHE))
    xx += 8
    for i in range(thermWidth):
        v_video.V_DrawPatchDirect(xx, y, w_wad.W_CacheLumpName(deh_main.DEH_String("M_THERMM"), doomdef.PU_CACHE))
        xx += 8
    v_video.V_DrawPatchDirect(xx, y, w_wad.W_CacheLumpName(deh_main.DEH_String("M_THERMR"), doomdef.PU_CACHE))
    v_video.V_DrawPatchDirect((x + 8) + thermDot * 8, y, w_wad.W_CacheLumpName(deh_main.DEH_String("M_THERMO"), doomdef.PU_CACHE))

# --- MAIN MENU ---
def M_DrawMainMenu():
    v_video.V_DrawPatchDirect(94, 2, w_wad.W_CacheLumpName(deh_main.DEH_String("M_DOOM"), doomdef.PU_CACHE))

# --- NEW GAME / EPISODE / SKILL ---
def M_NewGame(choice):
    if doomstat.netgame and not doomstat.demoplayback:
        M_StartMessage(deh_main.DEH_String(dstrings.NEWGAME), None, False)
        return
    if doomstat.gamemode == doomstat.commercial or doomstat.gameversion == doomstat.exe_chex:
        M_SetupNextMenu(NewDef)
    else:
        M_SetupNextMenu(EpiDef)

def M_DrawEpisode():
    v_video.V_DrawPatchDirect(54, 38, w_wad.W_CacheLumpName(deh_main.DEH_String("M_EPISOD"), doomdef.PU_CACHE))

def M_Episode(choice):
    global epi
    if doomstat.gamemode == doomstat.shareware and choice:
        M_StartMessage(deh_main.DEH_String(dstrings.SWSTRING), None, False)
        M_SetupNextMenu(ReadDef1)
        return
    epi = choice
    M_SetupNextMenu(NewDef)

def M_DrawNewGame():
    v_video.V_DrawPatchDirect(96, 14, w_wad.W_CacheLumpName(deh_main.DEH_String("M_NEWG"), doomdef.PU_CACHE))
    v_video.V_DrawPatchDirect(54, 38, w_wad.W_CacheLumpName(deh_main.DEH_String("M_SKILL"), doomdef.PU_CACHE))

def M_VerifyNightmare(key):
    if key != doomkeys.key_menu_confirm:
        return
    g_game.G_DeferedInitNew(4, epi + 1, 1) # 4 = nightmare
    M_ClearMenus()

def M_ChooseSkill(choice):
    if choice == 4: # nightmare
        M_StartMessage(deh_main.DEH_String(dstrings.NIGHTMARE), M_VerifyNightmare, True)
        return
    g_game.G_DeferedInitNew(choice, epi + 1, 1)
    M_ClearMenus()

# --- OPTIONS ---
def M_Options(choice):
    M_SetupNextMenu(OptionsDef)

def M_DrawOptions():
    v_video.V_DrawPatchDirect(108, 15, w_wad.W_CacheLumpName(deh_main.DEH_String("M_OPTTTL"), doomdef.PU_CACHE))
    detailNames = ["M_GDHIGH", "M_GDLOW"]
    msgNames = ["M_MSGOFF", "M_MSGON"]
    v_video.V_DrawPatchDirect(OptionsDef.x + 175, OptionsDef.y + LINEHEIGHT * 2, 
                              w_wad.W_CacheLumpName(deh_main.DEH_String(detailNames[detailLevel]), doomdef.PU_CACHE))
    v_video.V_DrawPatchDirect(OptionsDef.x + 120, OptionsDef.y + LINEHEIGHT * 1, 
                              w_wad.W_CacheLumpName(deh_main.DEH_String(msgNames[showMessages]), doomdef.PU_CACHE))
    M_DrawThermo(OptionsDef.x, OptionsDef.y + LINEHEIGHT * 6, 10, mouseSensitivity)
    M_DrawThermo(OptionsDef.x, OptionsDef.y + LINEHEIGHT * 4, 9, screenSize)

def M_EndGameResponse(key):
    global currentMenu
    if key != doomkeys.key_menu_confirm:
        return
    currentMenu.lastOn = itemOn
    M_ClearMenus()
    # D_StartTitle() would go here but usually triggered through gamestate

def M_EndGame(choice):
    if not doomstat.usergame:
        s_sound.S_StartSound(None, sounds.sfx_oof)
        return
    if doomstat.netgame:
        M_StartMessage(deh_main.DEH_String(dstrings.NETEND), None, False)
        return
    M_StartMessage(deh_main.DEH_String(dstrings.ENDGAME), M_EndGameResponse, True)

def M_ChangeMessages(choice):
    global showMessages
    showMessages = 1 - showMessages
    if not showMessages:
        doomstat.players[doomstat.consoleplayer].message = deh_main.DEH_String(dstrings.MSGOFF)
    else:
        doomstat.players[doomstat.consoleplayer].message = deh_main.DEH_String(dstrings.MSGON)

def M_ChangeDetail(choice):
    global detailLevel
    detailLevel = 1 - detailLevel
    r_main.R_SetViewSize(screenblocks, detailLevel)
    if not detailLevel:
        doomstat.players[doomstat.consoleplayer].message = deh_main.DEH_String(dstrings.DETAILHI)
    else:
        doomstat.players[doomstat.consoleplayer].message = deh_main.DEH_String(dstrings.DETAILLO)

def M_SizeDisplay(choice):
    global screenblocks, screenSize
    if choice == 0:
        if screenSize > 0:
            screenblocks -= 1
            screenSize -= 1
    elif choice == 1:
        if screenSize < 8:
            screenblocks += 1
            screenSize += 1
    r_main.R_SetViewSize(screenblocks, detailLevel)

def M_ChangeSensitivity(choice):
    global mouseSensitivity
    if choice == 0:
        if mouseSensitivity > 0: mouseSensitivity -= 1
    elif choice == 1:
        if mouseSensitivity < 9: mouseSensitivity += 1

def M_Sound(choice):
    M_SetupNextMenu(SoundDef)

def M_DrawSound():
    v_video.V_DrawPatchDirect(60, 38, w_wad.W_CacheLumpName(deh_main.DEH_String("M_SVOL"), doomdef.PU_CACHE))
    M_DrawThermo(SoundDef.x, SoundDef.y + LINEHEIGHT * 1, 16, s_sound.sfxVolume)
    M_DrawThermo(SoundDef.x, SoundDef.y + LINEHEIGHT * 3, 16, s_sound.musicVolume)

def M_SfxVol(choice):
    if choice == 0:
        if s_sound.sfxVolume > 0: s_sound.sfxVolume -= 1
    elif choice == 1:
        if s_sound.sfxVolume < 15: s_sound.sfxVolume += 1
    s_sound.S_SetSfxVolume(s_sound.sfxVolume * 8)

def M_MusicVol(choice):
    if choice == 0:
        if s_sound.musicVolume > 0: s_sound.musicVolume -= 1
    elif choice == 1:
        if s_sound.musicVolume < 15: s_sound.musicVolume += 1
    s_sound.S_SetMusicVolume(s_sound.musicVolume * 8)

# --- SAVE / LOAD ---
def M_ReadSaveStrings():
    global savegamestrings
    for i in range(6):
        name = p_saveg.P_SaveGameFile(i)
        if m_misc.M_FileExists(name):
            data = m_misc.M_ReadFile(name)
            if data and len(data) >= SAVESTRINGSIZE:
                savegamestrings[i] = data[:SAVESTRINGSIZE].decode('ascii', errors='replace').rstrip('\x00')
                LoadMenu[i].status = 1
            else:
                savegamestrings[i] = ""
                LoadMenu[i].status = 0
        else:
            savegamestrings[i] = ""
            LoadMenu[i].status = 0

def M_DrawSaveLoadBorder(x, y):
    v_video.V_DrawPatchDirect(x - 8, y + 7, w_wad.W_CacheLumpName(deh_main.DEH_String("M_LSLEFT"), doomdef.PU_CACHE))
    cx = x
    for i in range(24):
        v_video.V_DrawPatchDirect(cx, y + 7, w_wad.W_CacheLumpName(deh_main.DEH_String("M_LSCNTR"), doomdef.PU_CACHE))
        cx += 8
    v_video.V_DrawPatchDirect(cx, y + 7, w_wad.W_CacheLumpName(deh_main.DEH_String("M_LSRGHT"), doomdef.PU_CACHE))

def M_DrawLoad():
    v_video.V_DrawPatchDirect(72, 28, w_wad.W_CacheLumpName(deh_main.DEH_String("M_LOADG"), doomdef.PU_CACHE))
    for i in range(6):
        M_DrawSaveLoadBorder(LoadDef.x, LoadDef.y + LINEHEIGHT * i)
        M_WriteText(LoadDef.x, LoadDef.y + LINEHEIGHT * i, savegamestrings[i])

def M_LoadGame(choice):
    if doomstat.netgame:
        M_StartMessage(deh_main.DEH_String(dstrings.LOADNET), None, False)
        return
    M_SetupNextMenu(LoadDef)
    M_ReadSaveStrings()

def M_LoadSelect(choice):
    name = p_saveg.P_SaveGameFile(choice)
    g_game.G_LoadGame(name)
    M_ClearMenus()

def M_DrawSave():
    v_video.V_DrawPatchDirect(72, 28, w_wad.W_CacheLumpName(deh_main.DEH_String("M_SAVEG"), doomdef.PU_CACHE))
    for i in range(6):
        M_DrawSaveLoadBorder(SaveDef.x, SaveDef.y + LINEHEIGHT * i)
        M_WriteText(SaveDef.x, SaveDef.y + LINEHEIGHT * i, savegamestrings[i])
    if saveStringEnter:
        w = M_StringWidth(savegamestrings[saveSlot])
        M_WriteText(SaveDef.x + w, SaveDef.y + LINEHEIGHT * saveSlot, "_")

def M_DoSave(slot):
    global quickSaveSlot
    g_game.G_SaveGame(slot, savegamestrings[slot])
    M_ClearMenus()
    if quickSaveSlot == -2:
        quickSaveSlot = slot

def SetDefaultSaveName(slot):
    global savegamestrings, joypadSave
    savegamestrings[itemOn] = ("MAP" + str(slot)).upper()
    joypadSave = False

def M_SaveSelect(choice):
    global saveStringEnter, saveSlot, saveOldString, saveCharIndex, joypadSave
    saveStringEnter = 1
    x = SaveDef.x - 11
    y = SaveDef.y + choice * LINEHEIGHT - 4
    i_video.I_StartTextInput(x, y, x + 8 + 24 * 8 + 8, y + LINEHEIGHT - 2)

    saveSlot = choice
    saveOldString = savegamestrings[choice]
    if not savegamestrings[choice]:
        savegamestrings[choice] = ""
        if joypadSave:
            SetDefaultSaveName(choice)
    saveCharIndex = len(savegamestrings[choice])

def M_SaveGame(choice):
    if not doomstat.usergame:
        M_StartMessage(deh_main.DEH_String(dstrings.SAVEDEAD), None, False)
        return
    if doomstat.gamestate != doomstat.GS_LEVEL:
        return
    M_SetupNextMenu(SaveDef)
    M_ReadSaveStrings()

def M_QuickSaveResponse(key):
    if key == doomkeys.key_menu_confirm:
        M_DoSave(quickSaveSlot)
        s_sound.S_StartSound(None, sounds.sfx_swtchx)

def M_QuickSave():
    global quickSaveSlot
    if not doomstat.usergame:
        s_sound.S_StartSound(None, sounds.sfx_oof)
        return
    if doomstat.gamestate != doomstat.GS_LEVEL:
        return
    if quickSaveSlot < 0:
        M_StartControlPanel()
        M_ReadSaveStrings()
        M_SetupNextMenu(SaveDef)
        quickSaveSlot = -2
        return
    tempstring = deh_main.DEH_snprintf(dstrings.QSPROMPT, savegamestrings[quickSaveSlot])
    M_StartMessage(tempstring, M_QuickSaveResponse, True)

def M_QuickLoadResponse(key):
    if key == doomkeys.key_menu_confirm:
        M_LoadSelect(quickSaveSlot)
        s_sound.S_StartSound(None, sounds.sfx_swtchx)

def M_QuickLoad():
    if doomstat.netgame:
        M_StartMessage(deh_main.DEH_String(dstrings.QLOADNET), None, False)
        return
    if quickSaveSlot < 0:
        M_StartMessage(deh_main.DEH_String(dstrings.QSAVESPOT), None, False)
        return
    tempstring = deh_main.DEH_snprintf(dstrings.QLPROMPT, savegamestrings[quickSaveSlot])
    M_StartMessage(tempstring, M_QuickLoadResponse, True)

# --- READ THIS ---
def M_ReadThis(choice): M_SetupNextMenu(ReadDef1)
def M_ReadThis2(choice): M_SetupNextMenu(ReadDef2)
def M_FinishReadThis(choice): M_SetupNextMenu(MainDef)

def M_DrawReadThis1():
    global inhelpscreens
    inhelpscreens = True
    v_video.V_DrawPatchDirect(0, 0, w_wad.W_CacheLumpName(deh_main.DEH_String("HELP2"), doomdef.PU_CACHE))

def M_DrawReadThis2():
    global inhelpscreens
    inhelpscreens = True
    v_video.V_DrawPatchDirect(0, 0, w_wad.W_CacheLumpName(deh_main.DEH_String("HELP1"), doomdef.PU_CACHE))

def M_DrawReadThisCommercial():
    global inhelpscreens
    inhelpscreens = True
    v_video.V_DrawPatchDirect(0, 0, w_wad.W_CacheLumpName(deh_main.DEH_String("HELP"), doomdef.PU_CACHE))

# --- QUIT ---
quitsounds = [
    sounds.sfx_pldeth, sounds.sfx_dmpain, sounds.sfx_popain, sounds.sfx_slop,
    sounds.sfx_telept, sounds.sfx_posit1, sounds.sfx_posit3, sounds.sfx_sgtatk
]

quitsounds2 = [
    sounds.sfx_vilact, sounds.sfx_getpow, sounds.sfx_boscub, sounds.sfx_slop,
    sounds.sfx_skeswg, sounds.sfx_kntdth, sounds.sfx_bspact, sounds.sfx_sgtatk
]

def M_QuitResponse(key):
    if key != doomkeys.key_menu_confirm:
        return
    if not doomstat.netgame:
        if doomstat.gamemode == doomstat.commercial:
            s_sound.S_StartSound(None, quitsounds2[(doomstat.gametic >> 2) & 7])
        else:
            s_sound.S_StartSound(None, quitsounds[(doomstat.gametic >> 2) & 7])
        i_video.I_WaitVBL(105)
    i_system.I_Quit()

def M_SelectEndMessage():
    if doomstat.logical_gamemission == doomstat.doom:
        return dstrings.doom1_endmsg[doomstat.gametic % dstrings.NUM_QUITMESSAGES]
    return dstrings.doom2_endmsg[doomstat.gametic % dstrings.NUM_QUITMESSAGES]

def M_QuitDOOM(choice):
    global endstring
    endstring = f"{deh_main.DEH_String(M_SelectEndMessage())}\n\n{dstrings.DOSY}"
    M_StartMessage(endstring, M_QuitResponse, True)

# --- INTERNAL HELPERS ---
def IsNullKey(key):
    return key in [doomkeys.KEY_PAUSE, doomkeys.KEY_CAPSLOCK, doomkeys.KEY_SCRLCK, doomkeys.KEY_NUMLOCK]

def M_StartControlPanel():
    global menuactive, currentMenu, itemOn
    if menuactive:
        return
    menuactive = 1
    currentMenu = MainDef
    itemOn = currentMenu.lastOn

# ==================
# EVENT LOOP ROUTINES
# ==================

def M_Responder(ev):
    global menuactive, messageToPrint, messageNeedsInput, messageRoutine, messageLastMenuActive
    global saveStringEnter, saveSlot, saveOldString, saveCharIndex, savegamestrings
    global itemOn, currentMenu, joypadSave
    
    if not hasattr(M_Responder, "mousewait"):
        M_Responder.mousewait = 0
        M_Responder.mousey = 0; M_Responder.lasty = 0
        M_Responder.mousex = 0; M_Responder.lastx = 0

    if doomstat.testcontrols:
        if ev.type == doomdef.ev_quit or (ev.type == doomdef.ev_keydown and ev.data1 in (doomkeys.key_menu_activate, doomkeys.key_menu_quit)):
            i_system.I_Quit()
            return True
        return False

    if ev.type == doomdef.ev_quit:
        if menuactive and messageToPrint and messageRoutine == M_QuitResponse:
            M_QuitResponse(doomkeys.key_menu_confirm)
        else:
            s_sound.S_StartSound(None, sounds.sfx_swtchn)
            M_QuitDOOM(0)
        return True

    ch = 0
    key = -1

    if ev.type == doomdef.ev_joystick:
        if menuactive:
            dir = i_joystick.JOY_GET_DPAD(ev.data6)
            if dir == i_joystick.JOY_DIR_NONE: dir = i_joystick.JOY_GET_LSTICK(ev.data6)
            if dir == i_joystick.JOY_DIR_NONE: dir = i_joystick.JOY_GET_RSTICK(ev.data6)

            if dir & i_joystick.JOY_DIR_UP: key = doomkeys.key_menu_up; doomstat.joywait = i_timer.I_GetTime() + 5
            elif dir & i_joystick.JOY_DIR_DOWN: key = doomkeys.key_menu_down; doomstat.joywait = i_timer.I_GetTime() + 5
            if dir & i_joystick.JOY_DIR_LEFT: key = doomkeys.key_menu_left; doomstat.joywait = i_timer.I_GetTime() + 5
            elif dir & i_joystick.JOY_DIR_RIGHT: key = doomkeys.key_menu_right; doomstat.joywait = i_timer.I_GetTime() + 5

            if i_joystick.JOY_BUTTON_PRESSED(ev, m_controls.joybfire):
                if messageToPrint and messageNeedsInput: key = doomkeys.key_menu_confirm
                elif saveStringEnter: key = doomkeys.KEY_ENTER
                else:
                    if currentMenu == SaveDef: joypadSave = True
                    key = doomkeys.key_menu_forward
                doomstat.joywait = i_timer.I_GetTime() + 5

            if i_joystick.JOY_BUTTON_PRESSED(ev, m_controls.joybuse):
                if messageToPrint and messageNeedsInput: key = doomkeys.key_menu_abort
                elif saveStringEnter: key = doomkeys.KEY_ESCAPE
                else: key = doomkeys.key_menu_back
                doomstat.joywait = i_timer.I_GetTime() + 5

        if i_joystick.JOY_BUTTON_PRESSED(ev, m_controls.joybmenu):
            key = doomkeys.key_menu_activate
            doomstat.joywait = i_timer.I_GetTime() + 5

    else:
        if ev.type == doomdef.ev_mouse and M_Responder.mousewait < i_timer.I_GetTime() and menuactive:
            M_Responder.mousey += ev.data3
            if M_Responder.mousey < M_Responder.lasty - 30:
                key = doomkeys.key_menu_down; M_Responder.mousewait = i_timer.I_GetTime() + 5; M_Responder.lasty -= 30; M_Responder.mousey = M_Responder.lasty
            elif M_Responder.mousey > M_Responder.lasty + 30:
                key = doomkeys.key_menu_up; M_Responder.mousewait = i_timer.I_GetTime() + 5; M_Responder.lasty += 30; M_Responder.mousey = M_Responder.lasty

            M_Responder.mousex += ev.data2
            if M_Responder.mousex < M_Responder.lastx - 30:
                key = doomkeys.key_menu_left; M_Responder.mousewait = i_timer.I_GetTime() + 5; M_Responder.lastx -= 30; M_Responder.mousex = M_Responder.lastx
            elif M_Responder.mousex > M_Responder.lastx + 30:
                key = doomkeys.key_menu_right; M_Responder.mousewait = i_timer.I_GetTime() + 5; M_Responder.lastx += 30; M_Responder.mousex = M_Responder.lastx

            if ev.data1 & 1: key = doomkeys.key_menu_forward; M_Responder.mousewait = i_timer.I_GetTime() + 15
            if ev.data1 & 2: key = doomkeys.key_menu_back; M_Responder.mousewait = i_timer.I_GetTime() + 15
        else:
            if ev.type == doomdef.ev_keydown:
                key = ev.data1
                ch = ev.data2

    if key == -1: return False

    if saveStringEnter:
        if key == doomkeys.KEY_BACKSPACE:
            if saveCharIndex > 0:
                saveCharIndex -= 1
                savegamestrings[saveSlot] = savegamestrings[saveSlot][:saveCharIndex]
        elif key == doomkeys.KEY_ESCAPE:
            saveStringEnter = 0
            i_video.I_StopTextInput()
            savegamestrings[saveSlot] = saveOldString
        elif key == doomkeys.KEY_ENTER:
            saveStringEnter = 0
            i_video.I_StopTextInput()
            if savegamestrings[saveSlot]: M_DoSave(saveSlot)
        else:
            if ev.type == doomdef.ev_keydown:
                ch = ev.data1 if m_controls.vanilla_keyboard_mapping else getattr(ev, 'data3', ch)
                ch_str = str(chr(ch)).upper() if isinstance(ch, int) else str(ch).upper()
                c_val = ord(ch_str) if ch_str else 0
                
                if ch_str == ' ' or (0 <= c_val - hu_stuff.HU_FONTSTART < hu_stuff.HU_FONTSIZE):
                    if 32 <= c_val <= 127 and saveCharIndex < SAVESTRINGSIZE - 1 and M_StringWidth(savegamestrings[saveSlot]) < (SAVESTRINGSIZE - 2) * 8:
                        savegamestrings[saveSlot] += ch_str
                        saveCharIndex += 1
        return True

    if messageToPrint:
        if messageNeedsInput and key not in (ord(' '), doomkeys.KEY_ESCAPE, doomkeys.key_menu_confirm, doomkeys.key_menu_abort):
            return False
        menuactive = messageLastMenuActive
        messageToPrint = 0
        if messageRoutine: messageRoutine(key)
        menuactive = False
        s_sound.S_StartSound(None, sounds.sfx_swtchx)
        return True

    if (doomstat.devparm and key == doomkeys.key_menu_help) or (key != 0 and key == doomkeys.key_menu_screenshot):
        g_game.G_ScreenShot()
        return True

    if not menuactive:
        if key == doomkeys.key_menu_decscreen:
            if doomstat.automapactive or doomstat.chat_on: return False
            M_SizeDisplay(0); s_sound.S_StartSound(None, sounds.sfx_stnmov); return True
        elif key == doomkeys.key_menu_incscreen:
            if doomstat.automapactive or doomstat.chat_on: return False
            M_SizeDisplay(1); s_sound.S_StartSound(None, sounds.sfx_stnmov); return True
        elif key == doomkeys.key_menu_help:
            M_StartControlPanel()
            currentMenu = ReadDef2 if doomstat.gameversion >= doomstat.exe_ultimate else ReadDef1
            itemOn = 0
            s_sound.S_StartSound(None, sounds.sfx_swtchn)
            return True
        elif key == doomkeys.key_menu_save: M_StartControlPanel(); s_sound.S_StartSound(None, sounds.sfx_swtchn); M_SaveGame(0); return True
        elif key == doomkeys.key_menu_load: M_StartControlPanel(); s_sound.S_StartSound(None, sounds.sfx_swtchn); M_LoadGame(0); return True
        elif key == doomkeys.key_menu_volume: M_StartControlPanel(); currentMenu = SoundDef; itemOn = 0; s_sound.S_StartSound(None, sounds.sfx_swtchn); return True
        elif key == doomkeys.key_menu_detail: M_ChangeDetail(0); s_sound.S_StartSound(None, sounds.sfx_swtchn); return True
        elif key == doomkeys.key_menu_qsave: s_sound.S_StartSound(None, sounds.sfx_swtchn); M_QuickSave(); return True
        elif key == doomkeys.key_menu_endgame: s_sound.S_StartSound(None, sounds.sfx_swtchn); M_EndGame(0); return True
        elif key == doomkeys.key_menu_messages: M_ChangeMessages(0); s_sound.S_StartSound(None, sounds.sfx_swtchn); return True
        elif key == doomkeys.key_menu_qload: s_sound.S_StartSound(None, sounds.sfx_swtchn); M_QuickLoad(); return True
        elif key == doomkeys.key_menu_quit: s_sound.S_StartSound(None, sounds.sfx_swtchn); M_QuitDOOM(0); return True
        elif key == doomkeys.key_menu_gamma:
            doomstat.usegamma = (doomstat.usegamma + 1) % 5
            doomstat.players[doomstat.consoleplayer].message = deh_main.DEH_String(gammamsg[doomstat.usegamma])
            i_video.I_SetPalette(w_wad.W_CacheLumpName(deh_main.DEH_String("PLAYPAL"), doomdef.PU_CACHE))
            return True
        elif key == doomkeys.key_menu_activate:
            M_StartControlPanel(); s_sound.S_StartSound(None, sounds.sfx_swtchn); return True
        return False

    if key == doomkeys.key_menu_down:
        while True:
            itemOn = 0 if itemOn + 1 >= currentMenu.numitems else itemOn + 1
            s_sound.S_StartSound(None, sounds.sfx_pstop)
            if currentMenu.menuitems[itemOn].status != -1: break
        return True
    elif key == doomkeys.key_menu_up:
        while True:
            itemOn = currentMenu.numitems - 1 if itemOn == 0 else itemOn - 1
            s_sound.S_StartSound(None, sounds.sfx_pstop)
            if currentMenu.menuitems[itemOn].status != -1: break
        return True
    elif key == doomkeys.key_menu_left:
        if currentMenu.menuitems[itemOn].routine and currentMenu.menuitems[itemOn].status == 2:
            s_sound.S_StartSound(None, sounds.sfx_stnmov)
            currentMenu.menuitems[itemOn].routine(0)
        return True
    elif key == doomkeys.key_menu_right:
        if currentMenu.menuitems[itemOn].routine and currentMenu.menuitems[itemOn].status == 2:
            s_sound.S_StartSound(None, sounds.sfx_stnmov)
            currentMenu.menuitems[itemOn].routine(1)
        return True
    elif key == doomkeys.key_menu_forward:
        if currentMenu.menuitems[itemOn].routine and currentMenu.menuitems[itemOn].status:
            currentMenu.lastOn = itemOn
            if currentMenu.menuitems[itemOn].status == 2:
                currentMenu.menuitems[itemOn].routine(1)
                s_sound.S_StartSound(None, sounds.sfx_stnmov)
            else:
                currentMenu.menuitems[itemOn].routine(itemOn)
                s_sound.S_StartSound(None, sounds.sfx_pistol)
        return True
    elif key == doomkeys.key_menu_activate:
        currentMenu.lastOn = itemOn
        M_ClearMenus()
        s_sound.S_StartSound(None, sounds.sfx_swtchx)
        return True
    elif key == doomkeys.key_menu_back:
        currentMenu.lastOn = itemOn
        if currentMenu.prevMenu:
            currentMenu = currentMenu.prevMenu
            itemOn = currentMenu.lastOn
            s_sound.S_StartSound(None, sounds.sfx_swtchn)
        return True
    elif ch != 0 or IsNullKey(key):
        ch_str = chr(ch).lower() if isinstance(ch, int) else str(ch).lower()
        for i in range(itemOn + 1, currentMenu.numitems):
            if currentMenu.menuitems[i].alphaKey == ch_str:
                itemOn = i; s_sound.S_StartSound(None, sounds.sfx_pstop); return True
        for i in range(0, itemOn + 1):
            if currentMenu.menuitems[i].alphaKey == ch_str:
                itemOn = i; s_sound.S_StartSound(None, sounds.sfx_pstop); return True

    return False

def M_Drawer():
    global messageToPrint, messageString, inhelpscreens, menuactive
    inhelpscreens = False
    
    if messageToPrint:
        y = doomdef.SCREENHEIGHT // 2 - M_StringHeight(messageString) // 2
        lines = messageString.split('\n')
        for line in lines:
            if not line and line == lines[-1]: break
            x = doomdef.SCREENWIDTH // 2 - M_StringWidth(line) // 2
            M_WriteText(x, y, line)
            y += hu_stuff.hu_font[0].height
        return
        
    if not menuactive: return
    if currentMenu.routine: currentMenu.routine()

    x = currentMenu.x
    y = currentMenu.y
    for i in range(currentMenu.numitems):
        name = deh_main.DEH_String(currentMenu.menuitems[i].name)
        if name and w_wad.W_CheckNumForName(name) > 0:
            v_video.V_DrawPatchDirect(x, y, w_wad.W_CacheLumpName(name, doomdef.PU_CACHE))
        y += LINEHEIGHT

    v_video.V_DrawPatchDirect(x + SKULLXOFF, currentMenu.y - 5 + itemOn * LINEHEIGHT, 
                              w_wad.W_CacheLumpName(deh_main.DEH_String(skullName[whichSkull]), doomdef.PU_CACHE))

def M_Ticker():
    global skullAnimCounter, whichSkull
    skullAnimCounter -= 1
    if skullAnimCounter <= 0:
        whichSkull ^= 1
        skullAnimCounter = 8

# ==================
# MENU DEFINITIONS
# ==================

MainMenu = [
    MenuItem(1, "M_NGAME", M_NewGame, 'n'),
    MenuItem(1, "M_OPTION", M_Options, 'o'),
    MenuItem(1, "M_LOADG", M_LoadGame, 'l'),
    MenuItem(1, "M_SAVEG", M_SaveGame, 's'),
    MenuItem(1, "M_RDTHIS", M_ReadThis, 'r'),
    MenuItem(1, "M_QUITG", M_QuitDOOM, 'q')
]
MainDef = MenuDef(6, None, MainMenu, M_DrawMainMenu, 97, 64, 0)

EpisodeMenu = [
    MenuItem(1, "M_EPI1", M_Episode, 'k'),
    MenuItem(1, "M_EPI2", M_Episode, 't'),
    MenuItem(1, "M_EPI3", M_Episode, 'i'),
    MenuItem(1, "M_EPI4", M_Episode, 't')
]
EpiDef = MenuDef(4, MainDef, EpisodeMenu, M_DrawEpisode, 48, 63, 0)

NewGameMenu = [
    MenuItem(1, "M_JKILL", M_ChooseSkill, 'i'),
    MenuItem(1, "M_ROUGH", M_ChooseSkill, 'h'),
    MenuItem(1, "M_HURT", M_ChooseSkill, 'h'),
    MenuItem(1, "M_ULTRA", M_ChooseSkill, 'u'),
    MenuItem(1, "M_NMARE", M_ChooseSkill, 'n')
]
NewDef = MenuDef(5, EpiDef, NewGameMenu, M_DrawNewGame, 48, 63, 2)

OptionsMenu = [
    MenuItem(1, "M_ENDGAM", M_EndGame, 'e'),
    MenuItem(1, "M_MESSG", M_ChangeMessages, 'm'),
    MenuItem(1, "M_DETAIL", M_ChangeDetail, 'g'),
    MenuItem(2, "M_SCRNSZ", M_SizeDisplay, 's'),
    MenuItem(-1, "", None, '\0'),
    MenuItem(2, "M_MSENS", M_ChangeSensitivity, 'm'),
    MenuItem(-1, "", None, '\0'),
    MenuItem(1, "M_SVOL", M_Sound, 's')
]
OptionsDef = MenuDef(8, MainDef, OptionsMenu, M_DrawOptions, 60, 37, 0)

ReadMenu1 = [MenuItem(1, "", M_ReadThis2, '\0')]
ReadDef1 = MenuDef(1, MainDef, ReadMenu1, M_DrawReadThis1, 280, 185, 0)

ReadMenu2 = [MenuItem(1, "", M_FinishReadThis, '\0')]
ReadDef2 = MenuDef(1, ReadDef1, ReadMenu2, M_DrawReadThis2, 330, 175, 0)

SoundMenu = [
    MenuItem(2, "M_SFXVOL", M_SfxVol, 's'), MenuItem(-1, "", None, '\0'),
    MenuItem(2, "M_MUSVOL", M_MusicVol, 'm'), MenuItem(-1, "", None, '\0')
]
SoundDef = MenuDef(4, OptionsDef, SoundMenu, M_DrawSound, 80, 64, 0)

LoadMenu = [MenuItem(1, "", M_LoadSelect, str(i+1)) for i in range(6)]
LoadDef = MenuDef(6, MainDef, LoadMenu, M_DrawLoad, 80, 54, 0)

SaveMenu = [MenuItem(1, "", M_SaveSelect, str(i+1)) for i in range(6)]
SaveDef = MenuDef(6, MainDef, SaveMenu, M_DrawSave, 80, 54, 0)

def M_Init():
    global currentMenu, menuactive, itemOn, whichSkull, skullAnimCounter
    global screenSize, screenblocks, messageToPrint, messageString, messageLastMenuActive
    global quickSaveSlot, opldev

    currentMenu = MainDef
    menuactive = False
    itemOn = currentMenu.lastOn
    whichSkull = 0
    skullAnimCounter = 10
    screenSize = screenblocks - 3
    messageToPrint = 0
    messageString = None
    messageLastMenuActive = menuactive
    quickSaveSlot = -1

    if doomstat.gameversion >= doomstat.exe_ultimate:
        MainMenu[4].routine = M_ReadThis2
        ReadDef2.prevMenu = None

    if doomstat.gameversion >= doomstat.exe_final and doomstat.gameversion <= doomstat.exe_final2:
        ReadDef2.routine = M_DrawReadThisCommercial

    if doomstat.gamemode == doomstat.commercial:
        MainMenu[4] = MainMenu[5]
        MainDef.numitems -= 1
        MainDef.y += 8
        NewDef.prevMenu = MainDef
        ReadDef1.routine = M_DrawReadThisCommercial
        ReadDef1.x, ReadDef1.y = 330, 165
        ReadMenu1[0].routine = M_FinishReadThis

    if doomstat.gameversion < doomstat.exe_ultimate:
        EpiDef.numitems -= 1
    elif doomstat.gameversion == doomstat.exe_chex:
        EpiDef.numitems = 1

    opldev = m_misc.M_CheckParm("-opldev") > 0
