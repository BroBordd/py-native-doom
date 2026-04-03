import p_spec
# p_saveg.py
# Translated DOOM savegame I/O and persistence

import os
import sys

import doomdef
import doomstat
import dstrings
import m_misc
import i_system
import info

# We import the game logic modules to instantiate objects during unarchiving
import g_game
import p_local
import p_tick
import p_mobj
import p_ceilng
import p_doors
import p_floor
import p_plats
import p_lights

SAVEGAME_EOF = 0x1d
VERSIONSIZE = 16
SAVESTRINGSIZE = 24

save_stream = None
savegame_error = False
savegamelength = 0

def P_TempSaveGameFile():
    savegamedir = getattr(m_misc, 'savegamedir', "")
    return os.path.join(savegamedir, "temp.dsg")

def P_SaveGameFile(slot):
    savegamedir = getattr(m_misc, 'savegamedir', "")
    return os.path.join(savegamedir, f"{doomdef.SAVEGAMENAME}{slot}.dsg")

# ==============================================================================
# Endian-safe integer read/write functions
# ==============================================================================

def saveg_read8():
    global savegame_error, save_stream
    b = save_stream.read(1)
    if not b:
        if not savegame_error:
            sys.stderr.write("saveg_read8: Unexpected end of file while reading save game\n")
            savegame_error = True
        return 0
    return b[0]

def saveg_write8(value):
    global savegame_error, save_stream
    try:
        save_stream.write(bytes([value & 0xFF]))
    except Exception:
        if not savegame_error:
            sys.stderr.write("saveg_write8: Error while writing save game\n")
            savegame_error = True

def saveg_read16():
    result = saveg_read8()
    result |= (saveg_read8() << 8)
    if result & 0x8000:
        result -= 0x10000
    return result

def saveg_write16(value):
    saveg_write8(value & 0xFF)
    saveg_write8((value >> 8) & 0xFF)

def saveg_read32():
    result = saveg_read8()
    result |= (saveg_read8() << 8)
    result |= (saveg_read8() << 16)
    result |= (saveg_read8() << 24)
    if result & 0x80000000:
        result -= 0x100000000
    return result

def saveg_write32(value):
    saveg_write8(value & 0xFF)
    saveg_write8((value >> 8) & 0xFF)
    saveg_write8((value >> 16) & 0xFF)
    saveg_write8((value >> 24) & 0xFF)

def saveg_read_pad():
    global save_stream
    pos = save_stream.tell()
    padding = (4 - (pos & 3)) & 3
    for _ in range(padding):
        saveg_read8()

def saveg_write_pad():
    global save_stream
    pos = save_stream.tell()
    padding = (4 - (pos & 3)) & 3
    for _ in range(padding):
        saveg_write8(0)

def saveg_readp():
    return saveg_read32()

def saveg_writep(p):
    val = (id(p) & 0xFFFFFFFF) if p is not None else 0
    saveg_write32(val)

def saveg_read_enum():
    return saveg_read32()

def saveg_write_enum(value):
    saveg_write32(value)

# ==============================================================================
# Structure read/write functions
# ==============================================================================

def saveg_read_mapthing_t(obj):
    obj.x = saveg_read16()
    obj.y = saveg_read16()
    obj.angle = saveg_read16()
    obj.type = saveg_read16()
    obj.options = saveg_read16()

def saveg_write_mapthing_t(obj):
    saveg_write16(obj.x)
    saveg_write16(obj.y)
    saveg_write16(obj.angle)
    saveg_write16(obj.type)
    saveg_write16(obj.options)

def saveg_read_actionf_t(obj):
    obj.acp1 = saveg_readp()

def saveg_write_actionf_t(obj):
    saveg_writep(obj.acp1)

def saveg_read_thinker_t(obj):
    obj.prev = saveg_readp()
    obj.next = saveg_readp()
    if not hasattr(obj, 'function'):
        class DummyAction: pass
        obj.function = DummyAction()
    saveg_read_actionf_t(obj.function)

def saveg_write_thinker_t(obj):
    saveg_writep(obj.prev)
    saveg_writep(obj.next)
    saveg_write_actionf_t(obj.function)

def saveg_read_mobj_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    obj.x = saveg_read32()
    obj.y = saveg_read32()
    obj.z = saveg_read32()
    obj.snext = saveg_readp()
    obj.sprev = saveg_readp()
    obj.angle = saveg_read32()
    obj.sprite = saveg_read_enum()
    obj.frame = saveg_read32()
    obj.bnext = saveg_readp()
    obj.bprev = saveg_readp()
    obj.subsector = saveg_readp()
    obj.floorz = saveg_read32()
    obj.ceilingz = saveg_read32()
    obj.radius = saveg_read32()
    obj.height = saveg_read32()
    obj.momx = saveg_read32()
    obj.momy = saveg_read32()
    obj.momz = saveg_read32()
    obj.validcount = saveg_read32()
    obj.type = saveg_read_enum()
    obj.info = saveg_readp()
    obj.tics = saveg_read32()
    state_idx = saveg_read32()
    obj.state = info.states[state_idx] if 0 <= state_idx < len(info.states) else None
    obj.flags = saveg_read32()
    obj.health = saveg_read32()
    obj.movedir = saveg_read32()
    obj.movecount = saveg_read32()
    obj.target = saveg_readp()
    obj.reactiontime = saveg_read32()
    obj.threshold = saveg_read32()
    
    pl = saveg_read32()
    if pl > 0 and pl - 1 < len(doomstat.players):
        obj.player = doomstat.players[pl - 1]
        obj.player.mo = obj
    else:
        obj.player = None
        
    obj.lastlook = saveg_read32()
    if not hasattr(obj, 'spawnpoint'):
        class DummySpawnPoint: pass
        obj.spawnpoint = DummySpawnPoint()
    saveg_read_mapthing_t(obj.spawnpoint)
    obj.tracer = saveg_readp()

def saveg_write_mobj_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write32(obj.x)
    saveg_write32(obj.y)
    saveg_write32(obj.z)
    saveg_writep(obj.snext)
    saveg_writep(obj.sprev)
    saveg_write32(obj.angle)
    saveg_write_enum(obj.sprite)
    saveg_write32(obj.frame)
    saveg_writep(obj.bnext)
    saveg_writep(obj.bprev)
    saveg_writep(obj.subsector)
    saveg_write32(obj.floorz)
    saveg_write32(obj.ceilingz)
    saveg_write32(obj.radius)
    saveg_write32(obj.height)
    saveg_write32(obj.momx)
    saveg_write32(obj.momy)
    saveg_write32(obj.momz)
    saveg_write32(obj.validcount)
    saveg_write_enum(obj.type)
    saveg_writep(obj.info)
    saveg_write32(obj.tics)
    saveg_write32(info.states.index(obj.state) if obj.state in info.states else 0)
    saveg_write32(obj.flags)
    saveg_write32(obj.health)
    saveg_write32(obj.movedir)
    saveg_write32(obj.movecount)
    saveg_writep(obj.target)
    saveg_write32(obj.reactiontime)
    saveg_write32(obj.threshold)
    
    if obj.player and obj.player in doomstat.players:
        saveg_write32(doomstat.players.index(obj.player) + 1)
    else:
        saveg_write32(0)
        
    saveg_write32(obj.lastlook)
    saveg_write_mapthing_t(obj.spawnpoint)
    saveg_writep(obj.tracer)

def saveg_read_ticcmd_t(obj):
    obj.forwardmove = saveg_read8()
    if obj.forwardmove & 0x80: obj.forwardmove -= 0x100 # signed char
    obj.sidemove = saveg_read8()
    if obj.sidemove & 0x80: obj.sidemove -= 0x100
    obj.angleturn = saveg_read16()
    obj.consistancy = saveg_read16()
    obj.chatchar = saveg_read8()
    obj.buttons = saveg_read8()

def saveg_write_ticcmd_t(obj):
    saveg_write8(obj.forwardmove)
    saveg_write8(obj.sidemove)
    saveg_write16(obj.angleturn)
    saveg_write16(obj.consistancy)
    saveg_write8(obj.chatchar)
    saveg_write8(obj.buttons)

def saveg_read_pspdef_t(obj):
    state_idx = saveg_read32()
    obj.state = info.states[state_idx] if 0 < state_idx < len(info.states) else None
    obj.tics = saveg_read32()
    obj.sx = saveg_read32()
    obj.sy = saveg_read32()

def saveg_write_pspdef_t(obj):
    saveg_write32(info.states.index(obj.state) if obj.state in info.states else 0)
    saveg_write32(obj.tics)
    saveg_write32(obj.sx)
    saveg_write32(obj.sy)

def saveg_read_player_t(obj):
    obj.mo = saveg_readp()
    obj.playerstate = saveg_read_enum()
    saveg_read_ticcmd_t(obj.cmd)
    obj.viewz = saveg_read32()
    obj.viewheight = saveg_read32()
    obj.deltaviewheight = saveg_read32()
    obj.bob = saveg_read32()
    obj.health = saveg_read32()
    obj.armorpoints = saveg_read32()
    obj.armortype = saveg_read32()
    obj.powers = [saveg_read32() for _ in range(doomdef.NUMPOWERS)]
    obj.cards = [bool(saveg_read32()) for _ in range(doomdef.NUMCARDS)]
    obj.backpack = bool(saveg_read32())
    obj.frags = [saveg_read32() for _ in range(doomdef.MAXPLAYERS)]
    obj.readyweapon = saveg_read_enum()
    obj.pendingweapon = saveg_read_enum()
    obj.weaponowned = [bool(saveg_read32()) for _ in range(doomdef.NUMWEAPONS)]
    obj.ammo = [saveg_read32() for _ in range(doomdef.NUMAMMO)]
    obj.maxammo = [saveg_read32() for _ in range(doomdef.NUMAMMO)]
    obj.attackdown = saveg_read32()
    obj.usedown = saveg_read32()
    obj.cheats = saveg_read32()
    obj.refire = saveg_read32()
    obj.killcount = saveg_read32()
    obj.itemcount = saveg_read32()
    obj.secretcount = saveg_read32()
    obj.message = saveg_readp()
    obj.damagecount = saveg_read32()
    obj.bonuscount = saveg_read32()
    obj.attacker = saveg_readp()
    obj.extralight = saveg_read32()
    obj.fixedcolormap = saveg_read32()
    obj.colormap = saveg_read32()
    for i in range(doomdef.NUMPSPRITES):
        if not hasattr(obj.psprites[i], 'state'): obj.psprites[i] = p_mobj.pspdef_t()
        saveg_read_pspdef_t(obj.psprites[i])
    obj.didsecret = bool(saveg_read32())

def saveg_write_player_t(obj):
    saveg_writep(obj.mo)
    saveg_write_enum(obj.playerstate)
    saveg_write_ticcmd_t(obj.cmd)
    saveg_write32(obj.viewz)
    saveg_write32(obj.viewheight)
    saveg_write32(obj.deltaviewheight)
    saveg_write32(obj.bob)
    saveg_write32(obj.health)
    saveg_write32(obj.armorpoints)
    saveg_write32(obj.armortype)
    for p in obj.powers: saveg_write32(p)
    for c in obj.cards: saveg_write32(int(c))
    saveg_write32(int(obj.backpack))
    for f in obj.frags: saveg_write32(f)
    saveg_write_enum(obj.readyweapon)
    saveg_write_enum(obj.pendingweapon)
    for w in obj.weaponowned: saveg_write32(int(w))
    for a in obj.ammo: saveg_write32(a)
    for ma in obj.maxammo: saveg_write32(ma)
    saveg_write32(obj.attackdown)
    saveg_write32(obj.usedown)
    saveg_write32(obj.cheats)
    saveg_write32(obj.refire)
    saveg_write32(obj.killcount)
    saveg_write32(obj.itemcount)
    saveg_write32(obj.secretcount)
    saveg_writep(obj.message)
    saveg_write32(obj.damagecount)
    saveg_write32(obj.bonuscount)
    saveg_writep(obj.attacker)
    saveg_write32(obj.extralight)
    saveg_write32(obj.fixedcolormap)
    saveg_write32(obj.colormap)
    for i in range(doomdef.NUMPSPRITES):
        saveg_write_pspdef_t(obj.psprites[i])
    saveg_write32(int(obj.didsecret))

# ==============================================================================
# Map Specials
# ==============================================================================

def saveg_read_ceiling_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    obj.type = saveg_read_enum()
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.bottomheight = saveg_read32()
    obj.topheight = saveg_read32()
    obj.speed = saveg_read32()
    obj.crush = bool(saveg_read32())
    obj.direction = saveg_read32()
    obj.tag = saveg_read32()
    obj.olddirection = saveg_read32()

def saveg_write_ceiling_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write_enum(obj.type)
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.bottomheight)
    saveg_write32(obj.topheight)
    saveg_write32(obj.speed)
    saveg_write32(int(obj.crush))
    saveg_write32(obj.direction)
    saveg_write32(obj.tag)
    saveg_write32(obj.olddirection)

def saveg_read_vldoor_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    obj.type = saveg_read_enum()
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.topheight = saveg_read32()
    obj.speed = saveg_read32()
    obj.direction = saveg_read32()
    obj.topwait = saveg_read32()
    obj.topcountdown = saveg_read32()

def saveg_write_vldoor_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write_enum(obj.type)
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.topheight)
    saveg_write32(obj.speed)
    saveg_write32(obj.direction)
    saveg_write32(obj.topwait)
    saveg_write32(obj.topcountdown)

def saveg_read_floormove_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    obj.type = saveg_read_enum()
    obj.crush = bool(saveg_read32())
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.direction = saveg_read32()
    obj.newspecial = saveg_read32()
    obj.texture = saveg_read16()
    obj.floordestheight = saveg_read32()
    obj.speed = saveg_read32()

def saveg_write_floormove_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write_enum(obj.type)
    saveg_write32(int(obj.crush))
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.direction)
    saveg_write32(obj.newspecial)
    saveg_write16(obj.texture)
    saveg_write32(obj.floordestheight)
    saveg_write32(obj.speed)

def saveg_read_plat_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.speed = saveg_read32()
    obj.low = saveg_read32()
    obj.high = saveg_read32()
    obj.wait = saveg_read32()
    obj.count = saveg_read32()
    obj.status = saveg_read_enum()
    obj.oldstatus = saveg_read_enum()
    obj.crush = bool(saveg_read32())
    obj.tag = saveg_read32()
    obj.type = saveg_read_enum()

def saveg_write_plat_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.speed)
    saveg_write32(obj.low)
    saveg_write32(obj.high)
    saveg_write32(obj.wait)
    saveg_write32(obj.count)
    saveg_write_enum(obj.status)
    saveg_write_enum(obj.oldstatus)
    saveg_write32(int(obj.crush))
    saveg_write32(obj.tag)
    saveg_write_enum(obj.type)

def saveg_read_lightflash_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.count = saveg_read32()
    obj.maxlight = saveg_read32()
    obj.minlight = saveg_read32()
    obj.maxtime = saveg_read32()
    obj.mintime = saveg_read32()

def saveg_write_lightflash_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.count)
    saveg_write32(obj.maxlight)
    saveg_write32(obj.minlight)
    saveg_write32(obj.maxtime)
    saveg_write32(obj.mintime)

def saveg_read_strobe_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.count = saveg_read32()
    obj.minlight = saveg_read32()
    obj.maxlight = saveg_read32()
    obj.darktime = saveg_read32()
    obj.brighttime = saveg_read32()

def saveg_write_strobe_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.count)
    saveg_write32(obj.minlight)
    saveg_write32(obj.maxlight)
    saveg_write32(obj.darktime)
    saveg_write32(obj.brighttime)

def saveg_read_glow_t(obj):
    saveg_read_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    sector_idx = saveg_read32()
    obj.sector = p_local.sectors[sector_idx]
    obj.minlight = saveg_read32()
    obj.maxlight = saveg_read32()
    obj.direction = saveg_read32()

def saveg_write_glow_t(obj):
    saveg_write_thinker_t(obj.thinker if hasattr(obj, 'thinker') else obj)
    saveg_write32(p_local.sectors.index(obj.sector))
    saveg_write32(obj.minlight)
    saveg_write32(obj.maxlight)
    saveg_write32(obj.direction)

# ==============================================================================
# High-level save/load routines
# ==============================================================================

def P_WriteSaveGameHeader(description):
    for i, char in enumerate(description):
        if i >= SAVESTRINGSIZE: break
        saveg_write8(ord(char))
    for j in range(len(description), SAVESTRINGSIZE):
        saveg_write8(0)

    vercode = g_game.G_VanillaVersionCode() if hasattr(g_game, 'G_VanillaVersionCode') else 109
    name = f"version {vercode}"
    
    for i in range(VERSIONSIZE):
        saveg_write8(ord(name[i]) if i < len(name) else 0)

    saveg_write8(doomstat.gameskill)
    saveg_write8(doomstat.gameepisode)
    saveg_write8(doomstat.gamemap)

    for i in range(doomdef.MAXPLAYERS):
        saveg_write8(int(doomstat.playeringame[i]))

    saveg_write8((doomstat.leveltime >> 16) & 0xff)
    saveg_write8((doomstat.leveltime >> 8) & 0xff)
    saveg_write8(doomstat.leveltime & 0xff)

def P_ReadSaveGameHeader():
    for _ in range(SAVESTRINGSIZE):
        saveg_read8()

    read_vcheck = ""
    for _ in range(VERSIONSIZE):
        c = saveg_read8()
        if c != 0:
            read_vcheck += chr(c)

    vercode = g_game.G_VanillaVersionCode() if hasattr(g_game, 'G_VanillaVersionCode') else 109
    vcheck = f"version {vercode}"

    if read_vcheck != vcheck:
        return False

    doomstat.gameskill = saveg_read8()
    doomstat.gameepisode = saveg_read8()
    doomstat.gamemap = saveg_read8()

    for i in range(doomdef.MAXPLAYERS):
        doomstat.playeringame[i] = bool(saveg_read8())

    a = saveg_read8()
    b = saveg_read8()
    c = saveg_read8()
    doomstat.leveltime = (a << 16) + (b << 8) + c

    return True

def P_ReadSaveGameEOF():
    return saveg_read8() == SAVEGAME_EOF

def P_WriteSaveGameEOF():
    saveg_write8(SAVEGAME_EOF)

def P_ArchivePlayers():
    for i in range(doomdef.MAXPLAYERS):
        if not doomstat.playeringame[i]: continue
        saveg_write_pad()
        saveg_write_player_t(doomstat.players[i])

def P_UnArchivePlayers():
    for i in range(doomdef.MAXPLAYERS):
        if not doomstat.playeringame[i]: continue
        saveg_read_pad()
        saveg_read_player_t(doomstat.players[i])
        doomstat.players[i].mo = None
        doomstat.players[i].message = None
        doomstat.players[i].attacker = None

def P_ArchiveWorld():
    for sec in p_local.sectors:
        saveg_write16(sec.floorheight >> doomdef.FRACBITS)
        saveg_write16(sec.ceilingheight >> doomdef.FRACBITS)
        saveg_write16(sec.floorpic)
        saveg_write16(sec.ceilingpic)
        saveg_write16(sec.lightlevel)
        saveg_write16(sec.special)
        saveg_write16(sec.tag)
        
    for li in p_local.lines:
        saveg_write16(li.flags)
        saveg_write16(li.special)
        saveg_write16(li.tag)
        for j in range(2):
            if li.sidenum[j] == -1: continue
            si = p_local.sides[li.sidenum[j]]
            saveg_write16(si.textureoffset >> doomdef.FRACBITS)
            saveg_write16(si.rowoffset >> doomdef.FRACBITS)
            saveg_write16(si.toptexture)
            saveg_write16(si.bottomtexture)
            saveg_write16(si.midtexture)

def P_UnArchiveWorld():
    for sec in p_local.sectors:
        sec.floorheight = saveg_read16() << doomdef.FRACBITS
        sec.ceilingheight = saveg_read16() << doomdef.FRACBITS
        sec.floorpic = saveg_read16()
        sec.ceilingpic = saveg_read16()
        sec.lightlevel = saveg_read16()
        sec.special = saveg_read16()
        sec.tag = saveg_read16()
        sec.specialdata = None
        sec.soundtarget = None
        
    for li in p_local.lines:
        li.flags = saveg_read16()
        li.special = saveg_read16()
        li.tag = saveg_read16()
        for j in range(2):
            if li.sidenum[j] == -1: continue
            si = p_local.sides[li.sidenum[j]]
            si.textureoffset = saveg_read16() << doomdef.FRACBITS
            si.rowoffset = saveg_read16() << doomdef.FRACBITS
            si.toptexture = saveg_read16()
            si.bottomtexture = saveg_read16()
            si.midtexture = saveg_read16()

tc_end = 0
tc_mobj = 1

def P_ArchiveThinkers():
    th = p_local.thinkercap.next
    while th != p_local.thinkercap:
        if getattr(th, 'function', None) == p_mobj.P_MobjThinker:
            saveg_write8(tc_mobj)
            saveg_write_pad()
            saveg_write_mobj_t(th)
        th = th.next
    saveg_write8(tc_end)

def P_UnArchiveThinkers():
    currentthinker = p_local.thinkercap.next
    while currentthinker != p_local.thinkercap:
        nxt = currentthinker.next
        if getattr(currentthinker, 'function', None) == p_mobj.P_MobjThinker:
            p_mobj.P_RemoveMobj(currentthinker)
        currentthinker = nxt
        
    p_tick.P_InitThinkers()
    
    while True:
        tclass = saveg_read8()
        if tclass == tc_end:
            return
        elif tclass == tc_mobj:
            saveg_read_pad()
            mobj = p_mobj.mobj_t()
            saveg_read_mobj_t(mobj)
            mobj.target = None
            mobj.tracer = None
            p_mobj.P_SetThingPosition(mobj)
            mobj.info = info.mobjinfo[mobj.type]
            mobj.floorz = mobj.subsector.sector.floorheight
            mobj.ceilingz = mobj.subsector.sector.ceilingheight
            
            mobj.thinker = p_mobj.thinker_t()
            mobj.thinker.function = p_mobj.P_MobjThinker
            p_tick.P_AddThinker(mobj.thinker)
        else:
            i_system.I_Error(f"Unknown tclass {tclass} in savegame")


tc_ceiling = 0
tc_door = 1
tc_floor = 2
tc_plat = 3
tc_flash = 4
tc_strobe = 5
tc_glow = 6
tc_endspecials = 7

def P_ArchiveSpecials():
    th = p_local.thinkercap.next
    while th != p_local.thinkercap:
        fn = getattr(th, 'function', None)
        
        if fn is None:
            if th in p_local.activeceilings:
                saveg_write8(tc_ceiling)
                saveg_write_pad()
                saveg_write_ceiling_t(th)
        elif fn == p_ceilng.T_MoveCeiling:
            saveg_write8(tc_ceiling)
            saveg_write_pad()
            saveg_write_ceiling_t(th)
        elif fn == p_doors.T_VerticalDoor:
            saveg_write8(tc_door)
            saveg_write_pad()
            saveg_write_vldoor_t(th)
        elif fn == p_floor.T_MoveFloor:
            saveg_write8(tc_floor)
            saveg_write_pad()
            saveg_write_floormove_t(th)
        elif fn == p_plats.T_PlatRaise:
            saveg_write8(tc_plat)
            saveg_write_pad()
            saveg_write_plat_t(th)
        elif fn == p_lights.T_LightFlash:
            saveg_write8(tc_flash)
            saveg_write_pad()
            saveg_write_lightflash_t(th)
        elif fn == p_lights.T_StrobeFlash:
            saveg_write8(tc_strobe)
            saveg_write_pad()
            saveg_write_strobe_t(th)
        elif fn == p_lights.T_Glow:
            saveg_write8(tc_glow)
            saveg_write_pad()
            saveg_write_glow_t(th)
            
        th = th.next
        
    saveg_write8(tc_endspecials)

def P_UnArchiveSpecials():
    while True:
        tclass = saveg_read8()
        if tclass == tc_endspecials:
            return
            
        elif tclass == tc_ceiling:
            saveg_read_pad()
            ceiling = p_ceilng.ceiling_t()
            saveg_read_ceiling_t(ceiling)
            ceiling.sector.specialdata = ceiling
            if getattr(ceiling.thinker, 'function', None):
                ceiling.thinker.function = p_ceilng.T_MoveCeiling
            p_tick.P_AddThinker(ceiling.thinker)
            p_local.P_AddActiveCeiling(ceiling)
            
        elif tclass == tc_door:
            saveg_read_pad()
            door = p_doors.vldoor_t()
            saveg_read_vldoor_t(door)
            door.sector.specialdata = door
            door.thinker.function = p_doors.T_VerticalDoor
            p_tick.P_AddThinker(door.thinker)
            
        elif tclass == tc_floor:
            saveg_read_pad()
            floor_move = p_floor.floormove_t()
            saveg_read_floormove_t(floor_move)
            floor_move.sector.specialdata = floor_move
            floor_move.thinker.function = p_floor.T_MoveFloor
            p_tick.P_AddThinker(floor_move.thinker)
            
        elif tclass == tc_plat:
            saveg_read_pad()
            plat = p_plats.plat_t()
            saveg_read_plat_t(plat)
            plat.sector.specialdata = plat
            if getattr(plat.thinker, 'function', None):
                plat.thinker.function = p_plats.T_PlatRaise
            p_tick.P_AddThinker(plat.thinker)
            p_local.P_AddActivePlat(plat)
            
        elif tclass == tc_flash:
            saveg_read_pad()
            flash = p_lights.lightflash_t()
            saveg_read_lightflash_t(flash)
            flash.thinker.function = p_lights.T_LightFlash
            p_tick.P_AddThinker(flash.thinker)
            
        elif tclass == tc_strobe:
            saveg_read_pad()
            strobe = p_lights.strobe_t()
            saveg_read_strobe_t(strobe)
            strobe.thinker.function = p_lights.T_StrobeFlash
            p_tick.P_AddThinker(strobe.thinker)
            
        elif tclass == tc_glow:
            saveg_read_pad()
            glow = p_lights.glow_t()
            saveg_read_glow_t(glow)
            glow.thinker.function = p_lights.T_Glow
            p_tick.P_AddThinker(glow.thinker)
            
        else:
            i_system.I_Error(f"P_UnarchiveSpecials: Unknown tclass {tclass} in savegame")
