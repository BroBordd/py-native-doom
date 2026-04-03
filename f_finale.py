# f_finale.py
# Ported from f_finale.c

import struct
import sys

# Engine imports (assumes standard python doom port naming)
import doomstat
import d_main
import d_iwad
import w_wad
import z_zone
import v_video
import s_sound
import r_state
import hu_stuff
import info
import sounds
import dstrings
import deh_str

# -----------------------------------------------------------------------------
# CONSTANTS & ENUMS
# -----------------------------------------------------------------------------

F_STAGE_TEXT = 0
F_STAGE_ARTSCREEN = 1
F_STAGE_CAST = 2

TEXTSPEED = 3
TEXTWAIT = 250

# -----------------------------------------------------------------------------
# GLOBAL STATE VARIABLES
# -----------------------------------------------------------------------------

finalestage = F_STAGE_TEXT
finalecount = 0
finaletext = ""
finaleflat = ""

# Cast variables
castnum = 0
casttics = 0
caststate = None
castdeath = False
castframes = 0
castonmelee = 0
castattacking = False
laststage = 0

# -----------------------------------------------------------------------------
# DATA STRUCTURES
# -----------------------------------------------------------------------------

class TextScreen:
    def __init__(self, mission, episode, level, background, text):
        self.mission = mission
        self.episode = episode
        self.level = level
        self.background = background
        self.text = text

textscreens = [
    TextScreen(d_iwad.GameMission_t.doom,      1, 8,  "FLOOR4_8",  dstrings.E1TEXT),
    TextScreen(d_iwad.GameMission_t.doom,      2, 8,  "SFLR6_1",   dstrings.E2TEXT),
    TextScreen(d_iwad.GameMission_t.doom,      3, 8,  "MFLR8_4",   dstrings.E3TEXT),
    TextScreen(d_iwad.GameMission_t.doom,      4, 8,  "MFLR8_3",   dstrings.E4TEXT),

    TextScreen(d_iwad.GameMission_t.doom2,     1, 6,  "SLIME16",   dstrings.C1TEXT),
    TextScreen(d_iwad.GameMission_t.doom2,     1, 11, "RROCK14",   dstrings.C2TEXT),
    TextScreen(d_iwad.GameMission_t.doom2,     1, 20, "RROCK07",   dstrings.C3TEXT),
    TextScreen(d_iwad.GameMission_t.doom2,     1, 30, "RROCK17",   dstrings.C4TEXT),
    TextScreen(d_iwad.GameMission_t.doom2,     1, 15, "RROCK13",   dstrings.C5TEXT),
    TextScreen(d_iwad.GameMission_t.doom2,     1, 31, "RROCK19",   dstrings.C6TEXT),

    TextScreen(d_iwad.GameMission_t.pack_tnt,  1, 6,  "SLIME16",   dstrings.T1TEXT),
    TextScreen(d_iwad.GameMission_t.pack_tnt,  1, 11, "RROCK14",   dstrings.T2TEXT),
    TextScreen(d_iwad.GameMission_t.pack_tnt,  1, 20, "RROCK07",   dstrings.T3TEXT),
    TextScreen(d_iwad.GameMission_t.pack_tnt,  1, 30, "RROCK17",   dstrings.T4TEXT),
    TextScreen(d_iwad.GameMission_t.pack_tnt,  1, 15, "RROCK13",   dstrings.T5TEXT),
    TextScreen(d_iwad.GameMission_t.pack_tnt,  1, 31, "RROCK19",   dstrings.T6TEXT),

    TextScreen(d_iwad.GameMission_t.pack_plut, 1, 6,  "SLIME16",   dstrings.P1TEXT),
    TextScreen(d_iwad.GameMission_t.pack_plut, 1, 11, "RROCK14",   dstrings.P2TEXT),
    TextScreen(d_iwad.GameMission_t.pack_plut, 1, 20, "RROCK07",   dstrings.P3TEXT),
    TextScreen(d_iwad.GameMission_t.pack_plut, 1, 30, "RROCK17",   dstrings.P4TEXT),
    TextScreen(d_iwad.GameMission_t.pack_plut, 1, 15, "RROCK13",   dstrings.P5TEXT),
    TextScreen(d_iwad.GameMission_t.pack_plut, 1, 31, "RROCK19",   dstrings.P6TEXT),
]

castorder = [
    (dstrings.CC_ZOMBIE, info.MT_POSSESSED),
    (dstrings.CC_SHOTGUN, info.MT_SHOTGUY),
    (dstrings.CC_HEAVY, info.MT_CHAINGUY),
    (dstrings.CC_IMP, info.MT_TROOP),
    (dstrings.CC_DEMON, info.MT_SERGEANT),
    (dstrings.CC_LOST, info.MT_SKULL),
    (dstrings.CC_CACO, info.MT_HEAD),
    (dstrings.CC_HELL, info.MT_KNIGHT),
    (dstrings.CC_BARON, info.MT_BRUISER),
    (dstrings.CC_ARACH, info.MT_BABY),
    (dstrings.CC_PAIN, info.MT_PAIN),
    (dstrings.CC_REVEN, info.MT_UNDEAD),
    (dstrings.CC_MANCU, info.MT_FATSO),
    (dstrings.CC_ARCH, info.MT_VILE),
    (dstrings.CC_SPIDER, info.MT_SPIDER),
    (dstrings.CC_CYBER, info.MT_CYBORG),
    (dstrings.CC_HERO, info.MT_PLAYER),
    (None, 0)
]

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_patch_width(patch):
    """Safely gets width of a patch, whether it's an object or raw bytes."""
    if hasattr(patch, 'width'):
        return patch.width
    return struct.unpack("<h", patch[0:2])[0]

# -----------------------------------------------------------------------------
# MAIN LOGIC
# -----------------------------------------------------------------------------

def F_StartFinale():
    global finalestage, finalecount, finaletext, finaleflat
    
    doomstat.gameaction = doomstat.ga_nothing
    doomstat.gamestate = doomstat.GS_FINALE
    doomstat.viewactive = False
    doomstat.automapactive = False

    if doomstat.logical_gamemission == d_iwad.GameMission_t.doom:
        s_sound.S_ChangeMusic(sounds.mus_victor, True)
    else:
        s_sound.S_ChangeMusic(sounds.mus_read_m, True)

    for screen in textscreens:
        # Hack for Chex Quest check (usually handled by d_main.gameversion)
        lvl = screen.level
        if getattr(d_main, 'gameversion', -1) == getattr(d_main, 'exe_chex', -2) and screen.mission == d_iwad.GameMission_t.doom:
            lvl = 5

        if (doomstat.logical_gamemission == screen.mission and
            (doomstat.logical_gamemission != d_iwad.GameMission_t.doom or doomstat.gameepisode == screen.episode) and
            doomstat.gamemap == lvl):
            finaletext = screen.text
            finaleflat = screen.background

    finaletext = deh_str.DEH_String(finaletext)
    finaleflat = deh_str.DEH_String(finaleflat)
    
    finalestage = F_STAGE_TEXT
    finalecount = 0


def F_Responder(event):
    if finalestage == F_STAGE_CAST:
        return F_CastResponder(event)
    return False


def F_Ticker():
    global finalecount, finalestage
    
    # Check for skipping in Doom 2
    if doomstat.gamemode == d_iwad.GameMode_t.commercial and finalecount > 50:
        skip = False
        for i in range(doomstat.MAXPLAYERS):
            if doomstat.players[i].cmd.buttons:
                skip = True
                break
                
        if skip:
            if doomstat.gamemap == 30:
                F_StartCast()
            else:
                doomstat.gameaction = doomstat.ga_worlddone

    finalecount += 1

    if finalestage == F_STAGE_CAST:
        F_CastTicker()
        return

    if doomstat.gamemode == d_iwad.GameMode_t.commercial:
        return

    if finalestage == F_STAGE_TEXT and finalecount > len(finaletext) * TEXTSPEED + TEXTWAIT:
        finalecount = 0
        finalestage = F_STAGE_ARTSCREEN
        doomstat.wipegamestate = -1  # force a wipe
        if doomstat.gameepisode == 3:
            s_sound.S_StartMusic(sounds.mus_bunny)


def F_TextWrite():
    # Draw 64x64 flat tiled
    src = w_wad.W_CacheLumpName(finaleflat, z_zone.PU_CACHE)
    
    # Write flat directly to v_video.I_VideoBuffer bytearray
    for y in range(v_video.SCREENHEIGHT):
        src_row = (y & 63) * 64
        dest_row = y * v_video.SCREENWIDTH
        for x in range(v_video.SCREENWIDTH // 64):
            v_video.I_VideoBuffer[dest_row + x*64 : dest_row + x*64 + 64] = src[src_row : src_row + 64]
        rem = v_video.SCREENWIDTH & 63
        if rem:
            x_ofs = (v_video.SCREENWIDTH // 64) * 64
            v_video.I_VideoBuffer[dest_row + x_ofs : dest_row + x_ofs + rem] = src[src_row : src_row + rem]

    v_video.V_MarkRect(0, 0, v_video.SCREENWIDTH, v_video.SCREENHEIGHT)

    cx = 10
    cy = 10
    
    count = (finalecount - 10) // TEXTSPEED
    if count < 0:
        count = 0
        
    for i in range(min(count, len(finaletext))):
        c = finaletext[i]
        if c == '\n':
            cx = 10
            cy += 11
            continue
            
        char_idx = ord(c.upper()) - hu_stuff.HU_FONTSTART
        if char_idx < 0 or char_idx >= hu_stuff.HU_FONTSIZE:
            cx += 4
            continue
            
        patch = hu_stuff.hu_font[char_idx]
        w = get_patch_width(patch)
        if cx + w > v_video.SCREENWIDTH:
            break
            
        v_video.V_DrawPatch(cx, cy, patch)
        cx += w


def F_StartCast():
    global castnum, caststate, casttics, castdeath, finalestage
    global castframes, castonmelee, castattacking
    
    doomstat.wipegamestate = -1
    castnum = 0
    mobj_type = castorder[castnum][1]
    caststate = info.states[info.mobjinfo[mobj_type].seestate]
    casttics = caststate.tics
    castdeath = False
    finalestage = F_STAGE_CAST
    castframes = 0
    castonmelee = 0
    castattacking = False
    s_sound.S_ChangeMusic(sounds.mus_evil, True)


def F_CastTicker():
    global casttics, castnum, castdeath, caststate, castframes
    global castattacking, castonmelee
    
    casttics -= 1
    if casttics > 0:
        return
        
    if caststate.tics == -1 or caststate.nextstate == info.S_NULL:
        # switch to next monster
        castnum += 1
        castdeath = False
        if castorder[castnum][0] is None:
            castnum = 0
            
        mobj_type = castorder[castnum][1]
        if info.mobjinfo[mobj_type].seesound:
            s_sound.S_StartSound(None, info.mobjinfo[mobj_type].seesound)
            
        caststate = info.states[info.mobjinfo[mobj_type].seestate]
        castframes = 0
    else:
        # gross hack!
        if caststate == info.states[info.S_PLAY_ATK1]:
            castattacking = False
            castframes = 0
            caststate = info.states[info.mobjinfo[castorder[castnum][1]].seestate]
        else:
            st = caststate.nextstate
            caststate = info.states[st]
            castframes += 1
            
            # Sound hacks
            sfx = 0
            if st == info.S_PLAY_ATK1: sfx = sounds.sfx_dshtgn
            elif st == info.S_POSS_ATK2: sfx = sounds.sfx_pistol
            elif st == info.S_SPOS_ATK2: sfx = sounds.sfx_shotgn
            elif st == info.S_VILE_ATK2: sfx = sounds.sfx_vilatk
            elif st == info.S_SKEL_FIST2: sfx = sounds.sfx_skeswg
            elif st == info.S_SKEL_FIST4: sfx = sounds.sfx_skepch
            elif st == info.S_SKEL_MISS2: sfx = sounds.sfx_skeatk
            elif st in (info.S_FATT_ATK8, info.S_FATT_ATK5, info.S_FATT_ATK2): sfx = sounds.sfx_firsht
            elif st in (info.S_CPOS_ATK2, info.S_CPOS_ATK3, info.S_CPOS_ATK4): sfx = sounds.sfx_shotgn
            elif st == info.S_TROO_ATK3: sfx = sounds.sfx_claw
            elif st == info.S_SARG_ATK2: sfx = sounds.sfx_sgtatk
            elif st in (info.S_BOSS_ATK2, info.S_BOS2_ATK2, info.S_HEAD_ATK2): sfx = sounds.sfx_firsht
            elif st == info.S_SKULL_ATK2: sfx = sounds.sfx_sklatk
            elif st in (info.S_SPID_ATK2, info.S_SPID_ATK3): sfx = sounds.sfx_shotgn
            elif st == info.S_BSPI_ATK2: sfx = sounds.sfx_plasma
            elif st in (info.S_CYBER_ATK2, info.S_CYBER_ATK4, info.S_CYBER_ATK6): sfx = sounds.sfx_rlaunc
            elif st == info.S_PAIN_ATK3: sfx = sounds.sfx_sklatk
            
            if sfx:
                s_sound.S_StartSound(None, sfx)

    if castframes == 12:
        castattacking = True
        mobj_type = castorder[castnum][1]
        if castonmelee:
            caststate = info.states[info.mobjinfo[mobj_type].meleestate]
        else:
            caststate = info.states[info.mobjinfo[mobj_type].missilestate]
            
        castonmelee ^= 1
        
        if caststate == info.states[info.S_NULL]:
            if castonmelee:
                caststate = info.states[info.mobjinfo[mobj_type].meleestate]
            else:
                caststate = info.states[info.mobjinfo[mobj_type].missilestate]

    if castattacking:
        mobj_type = castorder[castnum][1]
        if castframes == 24 or caststate == info.states[info.mobjinfo[mobj_type].seestate]:
            castattacking = False
            castframes = 0
            caststate = info.states[info.mobjinfo[mobj_type].seestate]

    casttics = caststate.tics
    if casttics == -1:
        casttics = 15


def F_CastResponder(ev):
    global castdeath, caststate, casttics, castframes, castattacking
    
    # Needs a dummy 'ev_keydown' equivalent if using a dict or object
    ev_type = getattr(ev, 'type', None)
    if ev_type != getattr(doomstat, 'ev_keydown', 0): # Assuming 0/ev_keydown from d_event.py
        return False
        
    if castdeath:
        return True
        
    castdeath = True
    mobj_type = castorder[castnum][1]
    caststate = info.states[info.mobjinfo[mobj_type].deathstate]
    casttics = caststate.tics
    castframes = 0
    castattacking = False
    
    if info.mobjinfo[mobj_type].deathsound:
        s_sound.S_StartSound(None, info.mobjinfo[mobj_type].deathsound)
        
    return True


def F_CastPrint(text):
    width = 0
    for c in text:
        char_idx = ord(c.upper()) - hu_stuff.HU_FONTSTART
        if char_idx < 0 or char_idx >= hu_stuff.HU_FONTSIZE:
            width += 4
            continue
        width += get_patch_width(hu_stuff.hu_font[char_idx])
        
    cx = v_video.SCREENWIDTH // 2 - width // 2
    
    for c in text:
        char_idx = ord(c.upper()) - hu_stuff.HU_FONTSTART
        if char_idx < 0 or char_idx >= hu_stuff.HU_FONTSIZE:
            cx += 4
            continue
        patch = hu_stuff.hu_font[char_idx]
        v_video.V_DrawPatch(cx, 180, patch)
        cx += get_patch_width(patch)


def F_CastDrawer():
    v_video.V_DrawPatch(0, 0, w_wad.W_CacheLumpName(deh_str.DEH_String("BOSSBACK"), z_zone.PU_CACHE))
    F_CastPrint(deh_str.DEH_String(castorder[castnum][0]))
    
    sprdef = info.sprites[caststate.sprite]
    # mask 0x7F or FF_FRAMEMASK
    sprframe = sprdef.spriteframes[caststate.frame & 0x7F] 
    
    lump = sprframe.lump[0]
    flip = bool(sprframe.flip[0])
    
    patch = w_wad.W_CacheLumpNum(lump + doomstat.firstspritelump, z_zone.PU_CACHE)
    if flip:
        if hasattr(v_video, 'V_DrawPatchFlipped'):
            v_video.V_DrawPatchFlipped(v_video.SCREENWIDTH // 2, 170, patch)
    else:
        v_video.V_DrawPatch(v_video.SCREENWIDTH // 2, 170, patch)


def F_DrawPatchCol(x, patch_bytes, col):
    """Draws a single column from a standard Doom Picture Format."""
    col_ofs_data = patch_bytes[8 + col*4 : 12 + col*4]
    if len(col_ofs_data) < 4: return
    pos = struct.unpack("<I", col_ofs_data)[0]
    
    while pos < len(patch_bytes) and patch_bytes[pos] != 255:
        topdelta = patch_bytes[pos]
        length = patch_bytes[pos+1]
        
        source_pos = pos + 3
        dest = x + topdelta * v_video.SCREENWIDTH
        
        for _ in range(length):
            if dest < len(v_video.I_VideoBuffer) and source_pos < len(patch_bytes):
                v_video.I_VideoBuffer[dest] = patch_bytes[source_pos]
            source_pos += 1
            dest += v_video.SCREENWIDTH
            
        pos += length + 4


def F_BunnyScroll():
    global laststage
    
    p1 = w_wad.W_CacheLumpName(deh_str.DEH_String("PFUB2"), z_zone.PU_LEVEL)
    p2 = w_wad.W_CacheLumpName(deh_str.DEH_String("PFUB1"), z_zone.PU_LEVEL)

    v_video.V_MarkRect(0, 0, v_video.SCREENWIDTH, v_video.SCREENHEIGHT)
    
    scrolled = v_video.SCREENWIDTH - (finalecount - 230) // 2
    if scrolled > v_video.SCREENWIDTH: scrolled = v_video.SCREENWIDTH
    if scrolled < 0: scrolled = 0
    
    for x in range(v_video.SCREENWIDTH):
        if x + scrolled < v_video.SCREENWIDTH:
            F_DrawPatchCol(x, p1, x + scrolled)
        else:
            F_DrawPatchCol(x, p2, x + scrolled - v_video.SCREENWIDTH)
            
    if finalecount < 1130:
        return
        
    if finalecount < 1180:
        v_video.V_DrawPatch((v_video.SCREENWIDTH - 13*8) // 2,
                            (v_video.SCREENHEIGHT - 8*8) // 2,
                            w_wad.W_CacheLumpName(deh_str.DEH_String("END0"), z_zone.PU_CACHE))
        laststage = 0
        return
        
    stage = (finalecount - 1180) // 5
    if stage > 6: stage = 6
    if stage > laststage:
        s_sound.S_StartSound(None, sounds.sfx_pistol)
        laststage = stage
        
    name = f"END{stage}"
    v_video.V_DrawPatch((v_video.SCREENWIDTH - 13*8) // 2,
                        (v_video.SCREENHEIGHT - 8*8) // 2,
                        w_wad.W_CacheLumpName(deh_str.DEH_String(name), z_zone.PU_CACHE))


def F_ArtScreenDrawer():
    if doomstat.gameepisode == 3:
        F_BunnyScroll()
    else:
        lumpname = ""
        if doomstat.gameepisode == 1:
            if getattr(d_main, 'gameversion', 0) >= getattr(d_main, 'exe_ultimate', 1):
                lumpname = "CREDIT"
            else:
                lumpname = "HELP2"
        elif doomstat.gameepisode == 2:
            lumpname = "VICTORY2"
        elif doomstat.gameepisode == 4:
            lumpname = "ENDPIC"
        else:
            return
            
        lumpname = deh_str.DEH_String(lumpname)
        v_video.V_DrawPatch(0, 0, w_wad.W_CacheLumpName(lumpname, z_zone.PU_CACHE))


def F_Drawer():
    if finalestage == F_STAGE_CAST:
        F_CastDrawer()
    elif finalestage == F_STAGE_TEXT:
        F_TextWrite()
    elif finalestage == F_STAGE_ARTSCREEN:
        F_ArtScreenDrawer()
