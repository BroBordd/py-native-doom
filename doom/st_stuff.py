PU_STATIC = 1
# st_stuff.py
#
# DESCRIPTION:
#   Status bar code.
#   Does the face/direction indicator animation.
#   Does palette indicators as well (red pain/berserk, bright pickup)

import math

# Use localized/delayed imports for engine state to prevent circular dependencies
from doomdef import *
import v_video
import i_video
import w_wad
from m_random import M_Random
from s_sound import S_ChangeMusic

# Constants from st_stuff.h
ST_HEIGHT = 32
ST_WIDTH = SCREENWIDTH
ST_Y = (SCREENHEIGHT - ST_HEIGHT)

# Palette indices.
STARTREDPALS = 1
STARTBONUSPALS = 9
NUMREDPALS = 8
NUMBONUSPALS = 4
RADIATIONPAL = 13

# Location of status bar
ST_X = 0
ST_X2 = 104
ST_FX = 143
ST_FY = 169

# Number of status faces.
ST_NUMPAINFACES = 5
ST_NUMSTRAIGHTFACES = 3
ST_NUMTURNFACES = 2
ST_NUMSPECIALFACES = 3

ST_FACESTRIDE = (ST_NUMSTRAIGHTFACES + ST_NUMTURNFACES + ST_NUMSPECIALFACES)
ST_NUMEXTRAFACES = 2
ST_NUMFACES = (ST_FACESTRIDE * ST_NUMPAINFACES + ST_NUMEXTRAFACES)

ST_TURNOFFSET = ST_NUMSTRAIGHTFACES
ST_OUCHOFFSET = ST_TURNOFFSET + ST_NUMTURNFACES
ST_EVILGRINOFFSET = ST_OUCHOFFSET + 1
ST_RAMPAGEOFFSET = ST_EVILGRINOFFSET + 1
ST_GODFACE = (ST_NUMPAINFACES * ST_FACESTRIDE)
ST_DEADFACE = (ST_GODFACE + 1)

ST_FACESX = 143
ST_FACESY = 168

ST_EVILGRINCOUNT = (2 * TICRATE)
ST_STRAIGHTFACECOUNT = (TICRATE // 2)
ST_TURNCOUNT = (1 * TICRATE)
ST_OUCHCOUNT = (1 * TICRATE)
ST_RAMPAGEDELAY = (2 * TICRATE)
ST_MUCHPAIN = 20

# AMMO pos
ST_AMMOWIDTH = 3    
ST_AMMOX = 44
ST_AMMOY = 171

# HEALTH pos
ST_HEALTHWIDTH = 3  
ST_HEALTHX = 90
ST_HEALTHY = 171

# Weapon pos
ST_ARMSX = 111
ST_ARMSY = 172
ST_ARMSBGX = 104
ST_ARMSBGY = 168
ST_ARMSXSPACE = 12
ST_ARMSYSPACE = 10

# Frags pos
ST_FRAGSX = 138
ST_FRAGSY = 171 
ST_FRAGSWIDTH = 2

# ARMOR pos
ST_ARMORWIDTH = 3
ST_ARMORX = 221
ST_ARMORY = 171

# Key icon pos
ST_KEY0WIDTH = 8
ST_KEY0HEIGHT = 5
ST_KEY0X = 239
ST_KEY0Y = 171
ST_KEY1WIDTH = ST_KEY0WIDTH
ST_KEY1X = 239
ST_KEY1Y = 181
ST_KEY2WIDTH = ST_KEY0WIDTH
ST_KEY2X = 239
ST_KEY2Y = 191

# Ammunition counter pos
ST_AMMO0WIDTH = 3
ST_AMMO0HEIGHT = 6
ST_AMMO0X = 288
ST_AMMO0Y = 173
ST_AMMO1WIDTH = ST_AMMO0WIDTH
ST_AMMO1X = 288
ST_AMMO1Y = 179
ST_AMMO2WIDTH = ST_AMMO0WIDTH
ST_AMMO2X = 288
ST_AMMO2Y = 191
ST_AMMO3WIDTH = ST_AMMO0WIDTH
ST_AMMO3X = 288
ST_AMMO3Y = 185

# Indicate maximum ammunition pos
ST_MAXAMMO0WIDTH = 3
ST_MAXAMMO0HEIGHT = 5
ST_MAXAMMO0X = 314
ST_MAXAMMO0Y = 173
ST_MAXAMMO1WIDTH = ST_MAXAMMO0WIDTH
ST_MAXAMMO1X = 314
ST_MAXAMMO1Y = 179
ST_MAXAMMO2WIDTH = ST_MAXAMMO0WIDTH
ST_MAXAMMO2X = 314
ST_MAXAMMO2Y = 191
ST_MAXAMMO3WIDTH = ST_MAXAMMO0WIDTH
ST_MAXAMMO3X = 314
ST_MAXAMMO3Y = 185

ST_MSGWIDTH = 52

# --- Global State Variables ---

st_backing_screen = bytearray(ST_WIDTH * ST_HEIGHT)

plyr = None
st_firsttime = False
lu_palette = 0
st_msgcounter = 0
st_statusbaron = False
st_chat = False
st_oldchat = False
st_notdeathmatch = False
st_armson = False
st_fragson = False

sbar = None
sbarr = None
tallnum = [None] * 10
tallpercent = None
shortnum = [None] * 10
keys_patches = [None] * NUMCARDS
faces = [None] * ST_NUMFACES
faceback = None
armsbg = None
arms = [[None, None] for _ in range(6)]

# Widgets (Assume st_lib provides these classes/structures)
import st_lib

w_ready = st_lib.st_number_t()
w_frags = st_lib.st_number_t()
w_health = st_lib.st_percent_t()
w_armsbg = st_lib.st_binicon_t()
w_arms = [st_lib.st_multicon_t() for _ in range(6)]
w_faces = st_lib.st_multicon_t()
w_keyboxes = [st_lib.st_multicon_t() for _ in range(3)]
w_armor = st_lib.st_percent_t()
w_ammo = [st_lib.st_number_t() for _ in range(4)]
w_maxammo = [st_lib.st_number_t() for _ in range(4)]

st_fragscount = 0
st_oldhealth = -1
oldweaponsowned = [False] * NUMWEAPONS
st_facecount = 0
st_faceindex = 0
keyboxes = [-1] * 3
st_randomnumber = 0
st_palette = 0
st_stopped = True

# --- Functions ---

def ST_refreshBackground():
    import doomstat
    if st_statusbaron:
        v_video.V_UseBuffer(st_backing_screen)
        
        v_video.V_DrawPatch(ST_X, 0, sbar)
        if sbarr:
            v_video.V_DrawPatch(ST_ARMSBGX, 0, sbarr)
            
        if doomstat.netgame:
            v_video.V_DrawPatch(ST_FX, 0, faceback)
            
        v_video.V_RestoreBuffer()
        
        # Copy st_backing_screen to real screen
        # Depending on v_video implementation, this blits bytearray to screens[0]
        v_video.V_CopyRect(ST_X, 0, st_backing_screen, ST_WIDTH, ST_HEIGHT, ST_X, ST_Y)

def ST_Responder(ev):
    global st_firsttime
    import doomstat
    from d_event import ev_keydown, ev_keyup
    import m_cheat
    import g_game
    import p_inter

    # Note: Event AM_MSGHEADER and automap check logic omitted for minimal boot
    # but regular cheats included.

    if ev.type == ev_keydown:
        if not doomstat.netgame and doomstat.gameskill != sk_nightmare:
            # God Mode cheat
            if m_cheat.cht_CheckCheat("iddqd", ev.data2):
                plyr.cheats ^= CF_GODMODE
                if (plyr.cheats & CF_GODMODE):
                    if plyr.mo:
                        plyr.mo.health = 1000
                    plyr.health = 1000
                    plyr.message = "Degreelessness mode On"
                else:
                    plyr.message = "Degreelessness mode Off"

            # Ammo no key cheat
            elif m_cheat.cht_CheckCheat("idfa", ev.data2):
                plyr.armorpoints = 200
                plyr.armortype = 2
                for i in range(NUMWEAPONS):
                    plyr.weaponowned[i] = True
                for i in range(NUMAMMO):
                    plyr.ammo[i] = plyr.maxammo[i]
                plyr.message = "Added Weapons & Ammo"

            # Key full ammo cheat
            elif m_cheat.cht_CheckCheat("idkfa", ev.data2):
                plyr.armorpoints = 200
                plyr.armortype = 2
                for i in range(NUMWEAPONS):
                    plyr.weaponowned[i] = True
                for i in range(NUMAMMO):
                    plyr.ammo[i] = plyr.maxammo[i]
                for i in range(NUMCARDS):
                    plyr.cards[i] = True
                plyr.message = "Very Happy Ammo Added"

    return False

def ST_calcPainOffset():
    global oldhealth_calc, lastcalc
    if 'oldhealth_calc' not in globals():
        global oldhealth_calc, lastcalc
        oldhealth_calc = -1
        lastcalc = 0
        
    health = 100 if plyr.health > 100 else plyr.health
    
    if health != oldhealth_calc:
        lastcalc = ST_FACESTRIDE * (((100 - health) * ST_NUMPAINFACES) // 101)
        oldhealth_calc = health
        
    return lastcalc

lastattackdown = -1
priority = 0

def ST_updateFaceWidget():
    global lastattackdown, priority, st_faceindex, st_facecount
    from r_local import R_PointToAngle2

    if priority < 10:
        if not plyr.health:
            priority = 9
            st_faceindex = ST_DEADFACE
            st_facecount = 1

    if priority < 9:
        if plyr.bonuscount:
            doevilgrin = False
            for i in range(NUMWEAPONS):
                if oldweaponsowned[i] != plyr.weaponowned[i]:
                    doevilgrin = True
                    oldweaponsowned[i] = plyr.weaponowned[i]
            if doevilgrin:
                priority = 8
                st_facecount = ST_EVILGRINCOUNT
                st_faceindex = ST_calcPainOffset() + ST_EVILGRINOFFSET

    if priority < 8:
        if plyr.damagecount and plyr.attacker and plyr.attacker != plyr.mo:
            priority = 7
            if plyr.health - st_oldhealth > ST_MUCHPAIN:
                st_facecount = ST_TURNCOUNT
                st_faceindex = ST_calcPainOffset() + ST_OUCHOFFSET
            else:
                badguyangle = R_PointToAngle2(plyr.mo.x, plyr.mo.y, plyr.attacker.x, plyr.attacker.y)
                if badguyangle > plyr.mo.angle:
                    diffang = badguyangle - plyr.mo.angle
                    i = (diffang > ANG180)
                else:
                    diffang = plyr.mo.angle - badguyangle
                    i = (diffang <= ANG180)
                
                st_facecount = ST_TURNCOUNT
                st_faceindex = ST_calcPainOffset()
                
                if diffang < ANG45:
                    st_faceindex += ST_RAMPAGEOFFSET
                elif i:
                    st_faceindex += ST_TURNOFFSET
                else:
                    st_faceindex += ST_TURNOFFSET + 1

    if priority < 7:
        if plyr.damagecount:
            if plyr.health - st_oldhealth > ST_MUCHPAIN:
                priority = 7
                st_facecount = ST_TURNCOUNT
                st_faceindex = ST_calcPainOffset() + ST_OUCHOFFSET
            else:
                priority = 6
                st_facecount = ST_TURNCOUNT
                st_faceindex = ST_calcPainOffset() + ST_RAMPAGEOFFSET

    if priority < 6:
        if plyr.attackdown:
            if lastattackdown == -1:
                lastattackdown = ST_RAMPAGEDELAY
            else:
                lastattackdown -= 1
                if not lastattackdown:
                    priority = 5
                    st_faceindex = ST_calcPainOffset() + ST_RAMPAGEOFFSET
                    st_facecount = 1
                    lastattackdown = 1
        else:
            lastattackdown = -1

    if priority < 5:
        if (plyr.cheats & CF_GODMODE) or plyr.powers[pw_invulnerability]:
            priority = 4
            st_faceindex = ST_GODFACE
            st_facecount = 1

    if not st_facecount:
        st_faceindex = ST_calcPainOffset() + (st_randomnumber % 3)
        st_facecount = ST_STRAIGHTFACECOUNT
        priority = 0

    st_facecount -= 1

def ST_updateWidgets():
    global st_notdeathmatch, st_armson, st_fragson, st_fragscount, st_chat
    import doomstat
    
    # Ready weapon handling logic (omitted complex pointer logic, use lambda in createWidgets)
    w_ready.data = plyr.readyweapon
    
    for i in range(3):
        keyboxes[i] = i if plyr.cards[i] else -1
        if plyr.cards[i+3]:
            keyboxes[i] = i+3
            
    ST_updateFaceWidget()
    
    st_notdeathmatch = not doomstat.deathmatch
    st_armson = st_statusbaron and not doomstat.deathmatch
    st_fragson = doomstat.deathmatch and st_statusbaron
    
    st_fragscount = 0
    for i in range(MAXPLAYERS):
        if i != doomstat.consoleplayer:
            st_fragscount += doomstat.players[i].frags[i]
        else:
            st_fragscount -= doomstat.players[i].frags[i]
            
    global st_msgcounter
    if st_msgcounter > 0:
        st_msgcounter -= 1
        if not st_msgcounter:
            st_chat = st_oldchat

def ST_Ticker():
    global st_randomnumber, st_oldhealth
    st_randomnumber = M_Random()
    ST_updateWidgets()
    st_oldhealth = plyr.health

def ST_doPaletteStuff():
    global st_palette
    
    cnt = plyr.damagecount
    if plyr.powers[pw_strength]:
        bzc = 12 - (plyr.powers[pw_strength] >> 6)
        if bzc > cnt:
            cnt = bzc
            
    if cnt:
        palette = (cnt + 7) >> 3
        if palette >= NUMREDPALS:
            palette = NUMREDPALS - 1
        palette += STARTREDPALS
    elif plyr.bonuscount:
        palette = (plyr.bonuscount + 7) >> 3
        if palette >= NUMBONUSPALS:
            palette = NUMBONUSPALS - 1
        palette += STARTBONUSPALS
    elif plyr.powers[pw_ironfeet] > 4 * 32 or (plyr.powers[pw_ironfeet] & 8):
        palette = RADIATIONPAL
    else:
        palette = 0
        
    if palette != st_palette:
        st_palette = palette
        # Pass raw palette bytes to the exposed video interface hook
        pal_data = w_wad.W_CacheLumpNum(lu_palette, PU_CACHE)[palette*768 : (palette+1)*768]
        i_video.I_SetPalette(pal_data)

def ST_drawWidgets(refresh):
    global st_armson, st_fragson
    import doomstat
    
    st_armson = st_statusbaron and not doomstat.deathmatch
    st_fragson = doomstat.deathmatch and st_statusbaron
    
    st_lib.STlib_updateNum(w_ready, refresh)
    for i in range(4):
        st_lib.STlib_updateNum(w_ammo[i], refresh)
        st_lib.STlib_updateNum(w_maxammo[i], refresh)
        
    st_lib.STlib_updatePercent(w_health, refresh)
    st_lib.STlib_updatePercent(w_armor, refresh)
    st_lib.STlib_updateBinIcon(w_armsbg, refresh)
    
    for i in range(6):
        st_lib.STlib_updateMultIcon(w_arms[i], refresh)
        
    st_lib.STlib_updateMultIcon(w_faces, refresh)
    
    for i in range(3):
        st_lib.STlib_updateMultIcon(w_keyboxes[i], refresh)
        
    st_lib.STlib_updateNum(w_frags, refresh)

def ST_doRefresh():
    global st_firsttime
    st_firsttime = False
    ST_refreshBackground()
    ST_drawWidgets(True)

def ST_diffDraw():
    ST_drawWidgets(False)

def ST_Drawer(fullscreen, refresh):
    global st_statusbaron, st_firsttime
    import am_map # Assuming automap exists or stubbed
    # st_statusbaron = (not fullscreen) or am_map.automapactive
    st_statusbaron = True # Hardcoded to True for boot to show UI
    st_firsttime = st_firsttime or refresh
    
    ST_doPaletteStuff()
    if st_firsttime:
        ST_doRefresh()
    else:
        ST_diffDraw()

def ST_loadCallback(lumpname):
    return w_wad.W_CacheLumpName(lumpname, PU_STATIC)

def ST_loadGraphics():
    global tallnum, shortnum, tallpercent, keys_patches, armsbg, arms, faceback, sbar, sbarr, faces
    import doomstat
    
    for i in range(10):
        tallnum[i] = ST_loadCallback(f"STTNUM{i}")
        shortnum[i] = ST_loadCallback(f"STYSNUM{i}")
        
    tallpercent = ST_loadCallback("STTPRCNT")
    
    for i in range(NUMCARDS):
        keys_patches[i] = ST_loadCallback(f"STKEYS{i}")
        
    armsbg = ST_loadCallback("STARMS")
    
    for i in range(6):
        arms[i][0] = ST_loadCallback(f"STGNUM{i+2}")
        arms[i][1] = shortnum[i+2]
        
    faceback = ST_loadCallback(f"STFB{doomstat.consoleplayer}")
    
    if w_wad.W_CheckNumForName("STBAR") >= 0:
        sbar = ST_loadCallback("STBAR")
        sbarr = None
    else:
        sbar = ST_loadCallback("STMBARL")
        sbarr = ST_loadCallback("STMBARR")
        
    facenum = 0
    for i in range(ST_NUMPAINFACES):
        for j in range(ST_NUMSTRAIGHTFACES):
            faces[facenum] = ST_loadCallback(f"STFST{i}{j}")
            facenum += 1
        faces[facenum] = ST_loadCallback(f"STFTR{i}0")
        facenum += 1
        faces[facenum] = ST_loadCallback(f"STFTL{i}0")
        facenum += 1
        faces[facenum] = ST_loadCallback(f"STFOUCH{i}")
        facenum += 1
        faces[facenum] = ST_loadCallback(f"STFEVL{i}")
        facenum += 1
        faces[facenum] = ST_loadCallback(f"STFKILL{i}")
        facenum += 1
        
    faces[facenum] = ST_loadCallback("STFGOD0")
    facenum += 1
    faces[facenum] = ST_loadCallback("STFDEAD0")

def ST_loadData():
    global lu_palette
    lu_palette = w_wad.W_GetNumForName("PLAYPAL")
    ST_loadGraphics()

def ST_initData():
    global st_firsttime, plyr, st_statusbaron, st_oldchat, st_chat, st_faceindex, st_palette, st_oldhealth
    import doomstat
    
    st_firsttime = True
    plyr = doomstat.players[doomstat.consoleplayer]
    st_statusbaron = True
    st_oldchat = st_chat = False
    st_faceindex = 0
    st_palette = -1
    st_oldhealth = -1
    
    for i in range(NUMWEAPONS):
        oldweaponsowned[i] = plyr.weaponowned[i]
    for i in range(3):
        keyboxes[i] = -1
        
    st_lib.STlib_init()

def ST_createWidgets():
    # Helper to resolve ammo pointers dynamically
    def get_ready_ammo():
        from info import weaponinfo
        am_type = weaponinfo[plyr.readyweapon].ammo
        return 1994 if am_type == am_noammo else plyr.ammo[am_type]

    st_lib.STlib_initNum(w_ready, ST_AMMOX, ST_AMMOY, tallnum, 
                         get_ready_ammo, lambda: st_statusbaron, ST_AMMOWIDTH)
    w_ready.data = plyr.readyweapon
    
    st_lib.STlib_initPercent(w_health, ST_HEALTHX, ST_HEALTHY, tallnum, 
                             lambda: plyr.health, lambda: st_statusbaron, tallpercent)
                             
    st_lib.STlib_initBinIcon(w_armsbg, ST_ARMSBGX, ST_ARMSBGY, armsbg, 
                             lambda: st_notdeathmatch, lambda: st_statusbaron)
                             
    for i in range(6):
        st_lib.STlib_initMultIcon(w_arms[i], ST_ARMSX + (i % 3) * ST_ARMSXSPACE, 
                                  ST_ARMSY + (i // 3) * ST_ARMSYSPACE, arms[i], 
                                  lambda idx=i: plyr.weaponowned[idx+1], lambda: st_armson)
                                  
    st_lib.STlib_initNum(w_frags, ST_FRAGSX, ST_FRAGSY, tallnum, 
                         lambda: st_fragscount, lambda: st_fragson, ST_FRAGSWIDTH)
                         
    st_lib.STlib_initMultIcon(w_faces, ST_FACESX, ST_FACESY, faces, 
                              lambda: st_faceindex, lambda: st_statusbaron)
                              
    st_lib.STlib_initPercent(w_armor, ST_ARMORX, ST_ARMORY, tallnum, 
                             lambda: plyr.armorpoints, lambda: st_statusbaron, tallpercent)
                             
    for i in range(3):
        st_lib.STlib_initMultIcon(w_keyboxes[i], 
                                  [ST_KEY0X, ST_KEY1X, ST_KEY2X][i], 
                                  [ST_KEY0Y, ST_KEY1Y, ST_KEY2Y][i], 
                                  keys_patches, lambda idx=i: keyboxes[idx], lambda: st_statusbaron)
                                  
    for i in range(4):
        st_lib.STlib_initNum(w_ammo[i], 
                             [ST_AMMO0X, ST_AMMO1X, ST_AMMO2X, ST_AMMO3X][i], 
                             [ST_AMMO0Y, ST_AMMO1Y, ST_AMMO2Y, ST_AMMO3Y][i], 
                             shortnum, lambda idx=i: plyr.ammo[idx], lambda: st_statusbaron, ST_AMMO0WIDTH)
                             
    for i in range(4):
        st_lib.STlib_initNum(w_maxammo[i], 
                             [ST_MAXAMMO0X, ST_MAXAMMO1X, ST_MAXAMMO2X, ST_MAXAMMO3X][i], 
                             [ST_MAXAMMO0Y, ST_MAXAMMO1Y, ST_MAXAMMO2Y, ST_MAXAMMO3Y][i], 
                             shortnum, lambda idx=i: plyr.maxammo[idx], lambda: st_statusbaron, ST_MAXAMMO0WIDTH)

def ST_Start():
    global st_stopped
    if not st_stopped:
        ST_Stop()
    ST_initData()
    ST_createWidgets()
    st_stopped = False

def ST_Stop():
    global st_stopped
    if st_stopped: return
    i_video.I_SetPalette(w_wad.W_CacheLumpNum(lu_palette, PU_CACHE)[:768])
    st_stopped = True

def ST_Init():
    ST_loadData()
    # st_backing_screen pre-allocated globally
