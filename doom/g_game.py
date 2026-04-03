# g_game.py
# Game state machine: G_Ticker, G_InitNew, G_PlayerReborn,
# G_DoLoadLevel, G_ExitLevel, G_WorldDone, G_BuildTiccmd,
# G_DeathMatchSpawnPlayer, G_CheckSpot, G_DoReborn.
# Ported from g_game.c / g_game.h

from doomdef import (
    FRACBITS, FRACUNIT, TICRATE, MAXPLAYERS,
    GameMode, GameVersion, Skill,
    NUMAMMO, NUMWEAPONS, NUMCARDS,
    WeaponType, AmmoType,
    ANG45,
)
from d_player import Player, PlayerState, TicCmd, WbStartStruct, WbPlayerStruct

# ------------------------------------------------------------------
# Game-action enum
# ------------------------------------------------------------------
class GameAction:
    NOTHING    = 0
    LOADLEVEL  = 1
    NEWGAME    = 2
    LOADGAME   = 3
    SAVEGAME   = 4
    PLAYDEMO   = 5
    COMPLETED  = 6
    VICTORY    = 7
    WORLDDONE  = 8
    SCREENSHOT = 9

# ------------------------------------------------------------------
# Global game state (mirrors g_game.c globals)
# ------------------------------------------------------------------
gameaction:  int  = GameAction.NOTHING
oldgamestate: int = -1    # GameState.*

# Deferred new-game params
d_skill:   int = Skill.MEDIUM
d_episode: int = 1
d_map:     int = 1

# Intermission pars
_pars = [
    [0],
    [0, 30, 75, 120, 90, 165, 180, 180, 30, 165],
    [0, 90, 90, 90, 120, 90, 360, 240, 30, 170],
    [0, 90, 45, 90, 150, 90, 90, 165, 30, 135],
]
_cpars = [
    30,90,120,120,90,150,120,120,270,90,
    210,150,150,150,210,150,420,150,210,150,
    240,150,180,150,150,300,330,420,300,180,
    120,30
]

secretexit:  bool = False

# Input state
forwardmove = [0x19, 0x32]
sidemove    = [0x18, 0x28]
angleturn   = [640, 1280, 320]

SLOWTURNTICS = 6
NUMKEYS      = 256

gamekeydown: list = [False] * NUMKEYS
turnheld:    int  = 0
mousex:      int  = 0
mousey:      int  = 0

# Body queue (for deathmatch respawn)
BODYQUESIZE = 32
bodyque:    list = [None] * BODYQUESIZE

sendpause:  bool = False
sendsave:   bool = False

vanilla_savegame_limit = 1
vanilla_demo_limit     = 1

# ------------------------------------------------------------------
# G_InitPlayer
# ------------------------------------------------------------------
def G_InitPlayer(player_idx: int):
    G_PlayerReborn(player_idx)


# ------------------------------------------------------------------
# G_PlayerFinishLevel
# ------------------------------------------------------------------
def G_PlayerFinishLevel(player_idx: int):
    import doomstat
    p = doomstat.players[player_idx]
    if p is None:
        return
    for i in range(len(p.powers)):
        p.powers[i] = 0
    for i in range(len(p.cards)):
        p.cards[i] = False
    if p.mo:
        from p_mobj import MF_SHADOW
        p.mo.flags &= ~MF_SHADOW
    p.extralight     = 0
    p.fixedcolormap  = 0
    p.damagecount    = 0
    p.bonuscount     = 0


# ------------------------------------------------------------------
# G_PlayerReborn  — reset player after death / new game
# ------------------------------------------------------------------
def G_PlayerReborn(player_idx: int):
    import doomstat
    from p_inter import deh_initial_health, deh_initial_bullets, maxammo as _maxammo

    p = doomstat.players[player_idx]
    if p is None:
        p = Player()
        doomstat.players[player_idx] = p

    # Save counters
    frags       = list(p.frags)
    killcount   = p.killcount
    itemcount   = p.itemcount
    secretcount = p.secretcount

    # Full reset
    np = Player()
    doomstat.players[player_idx] = np
    np.frags       = frags
    np.killcount   = killcount
    np.itemcount   = itemcount
    np.secretcount = secretcount

    np.usedown   = True
    np.attackdown = True
    np.playerstate    = PlayerState.LIVE
    np.health         = deh_initial_health
    np.readyweapon    = WeaponType.PISTOL
    np.pendingweapon  = WeaponType.PISTOL
    np.weaponowned[WeaponType.FIST]   = True
    np.weaponowned[WeaponType.PISTOL] = True
    np.ammo[AmmoType.CLIP] = deh_initial_bullets
    for i in range(NUMAMMO):
        np.maxammo[i] = _maxammo[i]


# ------------------------------------------------------------------
# G_CheckSpot  — can a player spawn at this mapthing?
# ------------------------------------------------------------------
def G_CheckSpot(playernum: int, mthing) -> bool:
    import doomstat
    from p_map import P_CheckPosition
    from p_mobj import P_SpawnMobj, S_StartSound
    from r_main import R_PointInSubsector
    import info as info_mod
    from tables import finecosine, finesine, finetangent, ANGLETOFINESHIFT

    p = doomstat.players[playernum]

    if p is None or p.mo is None:
        # First spawn — check no overlap with earlier players
        for i in range(playernum):
            op = doomstat.players[i]
            if op and op.mo:
                if (op.mo.x == mthing.x << FRACBITS and
                        op.mo.y == mthing.y << FRACBITS):
                    return False
        return True

    x = mthing.x << FRACBITS
    y = mthing.y << FRACBITS

    if not P_CheckPosition(p.mo, x, y):
        return False

    # Flush old corpse
    bs = doomstat.bodyqueslot
    if bs >= BODYQUESIZE:
        from p_mobj import P_RemoveMobj
        P_RemoveMobj(bodyque[bs % BODYQUESIZE])
    bodyque[bs % BODYQUESIZE] = p.mo
    doomstat.bodyqueslot += 1

    # Spawn teleport fog (vanilla angle overflow emulation)
    ss = R_PointInSubsector(x, y)
    an = (ANG45 >> ANGLETOFINESHIFT) * (mthing.angle // 45)

    _special_angles = {
        4096: (finetangent[2048], finetangent[0]),
        5120: (finetangent[3072], finetangent[1024]),
        6144: (finesine[0],       finetangent[2048]),
        7168: (finesine[1024],    finetangent[3072]),
        0:    (finecosine[0],     finesine[0]),
        1024: (finecosine[1024],  finesine[1024]),
        2048: (finecosine[2048],  finesine[2048]),
        3072: (finecosine[3072],  finesine[3072]),
    }
    xa, ya = _special_angles.get(an, (finecosine[an & 0x1FFF], finesine[an & 0x1FFF]))
    mo = P_SpawnMobj(x + 20 * xa, y + 20 * ya,
                     ss.sector.floorheight, info_mod.MT_TFOG)

    if doomstat.players[doomstat.consoleplayer].viewz != 1:
        S_StartSound(mo, info_mod.sfx_telept)

    return True


# ------------------------------------------------------------------
# G_DeathMatchSpawnPlayer
# ------------------------------------------------------------------
def G_DeathMatchSpawnPlayer(playernum: int):
    import doomstat
    from m_random import P_Random
    from p_mobj import P_SpawnPlayer

    selections = len(doomstat.deathmatchstarts)
    if selections < 4:
        raise RuntimeError(f'Only {selections} deathmatch spots, 4 required')

    for _ in range(20):
        i = P_Random() % selections
        if G_CheckSpot(playernum, doomstat.deathmatchstarts[i]):
            doomstat.deathmatchstarts[i].type = playernum + 1
            P_SpawnPlayer(doomstat.deathmatchstarts[i])
            return

    from p_mobj import P_SpawnPlayer
    P_SpawnPlayer(doomstat.playerstarts[playernum])


# ------------------------------------------------------------------
# G_DoReborn
# ------------------------------------------------------------------
def G_DoReborn(playernum: int):
    import doomstat
    global gameaction
    from p_mobj import P_SpawnPlayer

    if not doomstat.netgame:
        gameaction = GameAction.LOADLEVEL
        return

    doomstat.players[playernum].mo.player = None

    if doomstat.deathmatch:
        G_DeathMatchSpawnPlayer(playernum)
        return

    if G_CheckSpot(playernum, doomstat.playerstarts[playernum]):
        P_SpawnPlayer(doomstat.playerstarts[playernum])
        return

    for i in range(MAXPLAYERS):
        if G_CheckSpot(playernum, doomstat.playerstarts[i]):
            doomstat.playerstarts[i].type = playernum + 1
            P_SpawnPlayer(doomstat.playerstarts[i])
            doomstat.playerstarts[i].type = i + 1
            return

    P_SpawnPlayer(doomstat.playerstarts[playernum])


# ------------------------------------------------------------------
# G_DoLoadLevel
# ------------------------------------------------------------------
def G_DoLoadLevel():
    import doomstat
    from doomdef import GameState
    global gameaction, mousex, mousey, sendpause, sendsave

    doomstat.gamestate = GameState.LEVEL
    for i in range(MAXPLAYERS):
        p = doomstat.players[i]
        if doomstat.playeringame[i] and p and p.playerstate == PlayerState.DEAD:
            p.playerstate = PlayerState.REBORN
        if p:
            p.frags = [0] * MAXPLAYERS

    from p_setup import P_SetupLevel
    P_SetupLevel(doomstat.gameepisode, doomstat.gamemap, 0, doomstat.gameskill)

    doomstat.displayplayer = doomstat.consoleplayer
    gameaction = GameAction.NOTHING

    gamekeydown[:] = [False] * NUMKEYS
    mousex = mousey = 0
    sendpause = sendsave = doomstat.paused = False


# ------------------------------------------------------------------
# G_DeferedInitNew / G_DoNewGame
# ------------------------------------------------------------------
def G_DeferedInitNew(skill: int, episode: int, map_: int):
    global d_skill, d_episode, d_map, gameaction
    d_skill   = skill
    d_episode = episode
    d_map     = map_
    gameaction = GameAction.NEWGAME


def G_DoNewGame():
    import doomstat
    doomstat.demoplayback  = False
    doomstat.netgame       = False
    doomstat.deathmatch    = 0
    doomstat.respawnparm   = False
    doomstat.fastparm      = False
    doomstat.nomonsters    = False
    doomstat.consoleplayer = 0
    for i in range(1, MAXPLAYERS):
        doomstat.playeringame[i] = False
    G_InitNew(d_skill, d_episode, d_map)
    global gameaction
    gameaction = GameAction.NOTHING


# ------------------------------------------------------------------
# G_InitNew  — main new-game entry point
# ------------------------------------------------------------------
def G_InitNew(skill: int, episode: int, map_: int):
    import doomstat, info as info_mod
    from m_random import M_ClearRandom
    from r_data import R_TextureNumForName, skytexture as _st
    import r_data

    if doomstat.paused:
        doomstat.paused = False
        _resume_sound()

    # Clamp skill
    if skill > Skill.NIGHTMARE:
        skill = Skill.NIGHTMARE

    # Episode clamping
    if doomstat.gameversion >= GameVersion.EXE_ULTIMATE:
        if episode == 0:
            episode = 4
    else:
        episode = max(1, min(episode, 3))

    if episode > 1 and doomstat.gamemode == GameMode.SHAREWARE:
        episode = 1

    map_ = max(1, map_)
    if doomstat.gamemode != GameMode.COMMERCIAL:
        map_ = min(map_, 9)

    M_ClearRandom()

    doomstat.respawnmonsters = (skill == Skill.NIGHTMARE or doomstat.respawnparm)

    # Fast monsters for nightmare / -fast
    if doomstat.fastparm or (skill == Skill.NIGHTMARE and doomstat.gameskill != Skill.NIGHTMARE):
        try:
            for i in range(info_mod.S_SARG_RUN1, info_mod.S_SARG_PAIN2 + 1):
                info_mod.states[i].tics >>= 1
            info_mod.mobjinfo[info_mod.MT_BRUISERSHOT].speed = 20 * FRACUNIT
            info_mod.mobjinfo[info_mod.MT_HEADSHOT].speed    = 20 * FRACUNIT
            info_mod.mobjinfo[info_mod.MT_TROOPSHOT].speed   = 20 * FRACUNIT
        except (AttributeError, IndexError):
            pass
    elif skill != Skill.NIGHTMARE and doomstat.gameskill == Skill.NIGHTMARE:
        try:
            for i in range(info_mod.S_SARG_RUN1, info_mod.S_SARG_PAIN2 + 1):
                info_mod.states[i].tics <<= 1
            info_mod.mobjinfo[info_mod.MT_BRUISERSHOT].speed = 15 * FRACUNIT
            info_mod.mobjinfo[info_mod.MT_HEADSHOT].speed    = 10 * FRACUNIT
            info_mod.mobjinfo[info_mod.MT_TROOPSHOT].speed   = 10 * FRACUNIT
        except (AttributeError, IndexError):
            pass

    for i in range(MAXPLAYERS):
        if doomstat.players[i] is None:
            doomstat.players[i] = Player()
        doomstat.players[i].playerstate = PlayerState.REBORN

    doomstat.usergame      = True
    doomstat.paused        = False
    doomstat.demoplayback  = False
    doomstat.automapactive = False
    doomstat.viewactive    = True
    doomstat.gameepisode   = episode
    doomstat.gamemap       = map_
    doomstat.gameskill     = skill

    # Sky texture
    if doomstat.gamemode == GameMode.COMMERCIAL:
        sky = 'SKY3'
        if map_ < 21:
            sky = 'SKY1' if map_ < 12 else 'SKY2'
    else:
        sky = {1: 'SKY1', 2: 'SKY2', 3: 'SKY3', 4: 'SKY4'}.get(episode, 'SKY1')

    try:
        r_data.skytexture = R_TextureNumForName(sky)
        import r_sky
        r_sky.skytexture = r_data.skytexture
    except Exception:
        pass

    G_DoLoadLevel()


# ------------------------------------------------------------------
# G_ExitLevel / G_SecretExitLevel
# ------------------------------------------------------------------
def G_ExitLevel():
    global secretexit, gameaction
    secretexit = False
    gameaction = GameAction.COMPLETED


def G_SecretExitLevel():
    global secretexit, gameaction
    import doomstat
    from wad import get_wad
    if (doomstat.gamemode == GameMode.COMMERCIAL and
            not get_wad().has_lump('map31')):
        secretexit = False
    else:
        secretexit = True
    gameaction = GameAction.COMPLETED


# ------------------------------------------------------------------
# G_DoCompleted
# ------------------------------------------------------------------
def G_DoCompleted():
    import doomstat
    from doomdef import GameState, GameVersion
    global gameaction, secretexit

    gameaction = GameAction.NOTHING

    for i in range(MAXPLAYERS):
        if doomstat.playeringame[i]:
            G_PlayerFinishLevel(i)

    doomstat.automapactive = False

    if doomstat.gamemode != GameMode.COMMERCIAL:
        if doomstat.gamemap == 8:
            gameaction = GameAction.VICTORY;  return
        if doomstat.gamemap == 9:
            for i in range(MAXPLAYERS):
                if doomstat.players[i]:
                    doomstat.players[i].didsecret = True

    wm = WbStartStruct()
    wm.didsecret = doomstat.players[doomstat.consoleplayer].didsecret if doomstat.players[doomstat.consoleplayer] else False
    wm.epsd = doomstat.gameepisode - 1
    wm.last = doomstat.gamemap - 1

    if doomstat.gamemode == GameMode.COMMERCIAL:
        if secretexit:
            if   doomstat.gamemap == 15: wm.next = 30
            elif doomstat.gamemap == 31: wm.next = 31
            else: wm.next = doomstat.gamemap
        else:
            if doomstat.gamemap in (31, 32): wm.next = 15
            else: wm.next = doomstat.gamemap
    else:
        if secretexit:
            wm.next = 8
        elif doomstat.gamemap == 9:
            wm.next = {1: 3, 2: 5, 3: 6, 4: 2}.get(doomstat.gameepisode, doomstat.gamemap)
        else:
            wm.next = doomstat.gamemap

    wm.maxkills  = doomstat.totalkills
    wm.maxitems  = doomstat.totalitems
    wm.maxsecret = doomstat.totalsecret
    wm.maxfrags  = 0

    if doomstat.gamemode == GameMode.COMMERCIAL:
        wm.partime = TICRATE * (_cpars[doomstat.gamemap - 1] if doomstat.gamemap <= 32 else 30)
    elif doomstat.gameepisode < 4:
        wm.partime = TICRATE * _pars[doomstat.gameepisode][doomstat.gamemap]
    else:
        wm.partime = 0

    for i in range(MAXPLAYERS):
        p = doomstat.players[i]
        wm.plyr[i].in_game = doomstat.playeringame[i]
        if p:
            wm.plyr[i].skills   = p.killcount
            wm.plyr[i].sitems   = p.itemcount
            wm.plyr[i].ssecret  = p.secretcount
            wm.plyr[i].stime    = doomstat.leveltime
            wm.plyr[i].frags    = list(p.frags)

    doomstat.wminfo  = wm
    doomstat.gamestate  = 1  # GS_INTERMISSION
    doomstat.viewactive = False


# ------------------------------------------------------------------
# G_WorldDone / G_DoWorldDone
# ------------------------------------------------------------------
def G_WorldDone():
    global gameaction, secretexit
    import doomstat
    gameaction = GameAction.WORLDDONE
    if secretexit:
        if doomstat.players[doomstat.consoleplayer]:
            doomstat.players[doomstat.consoleplayer].didsecret = True


def G_DoWorldDone():
    import doomstat
    from doomdef import GameState
    doomstat.gamestate = GameState.LEVEL
    if doomstat.wminfo:
        doomstat.gamemap = doomstat.wminfo.next + 1
    G_DoLoadLevel()
    global gameaction
    gameaction = GameAction.NOTHING
    doomstat.viewactive = True


# ------------------------------------------------------------------
# G_Ticker  — main per-tic game dispatcher
# ------------------------------------------------------------------
def G_Ticker():
    import doomstat
    from doomdef import GameState
    global gameaction, oldgamestate

    # Reborn check
    for i in range(MAXPLAYERS):
        p = doomstat.players[i]
        if doomstat.playeringame[i] and p and p.playerstate == PlayerState.REBORN:
            G_DoReborn(i)

    # Action dispatch
    while gameaction != GameAction.NOTHING:
        if gameaction == GameAction.LOADLEVEL:
            G_DoLoadLevel()
        elif gameaction == GameAction.NEWGAME:
            G_DoNewGame()
        elif gameaction == GameAction.COMPLETED:
            G_DoCompleted()
        elif gameaction == GameAction.WORLDDONE:
            G_DoWorldDone()
        elif gameaction == GameAction.VICTORY:
            gameaction = GameAction.NOTHING  # stub — no finale yet
        elif gameaction == GameAction.SCREENSHOT:
            gameaction = GameAction.NOTHING
        else:
            gameaction = GameAction.NOTHING

    # Copy netcmds to player cmd structs
    for i in range(MAXPLAYERS):
        if doomstat.playeringame[i]:
            p = doomstat.players[i]
            if p and doomstat.netcmds is not None:
                # netcmds is a list of TicCmd per player
                src = doomstat.netcmds[i] if i < len(doomstat.netcmds) else TicCmd()
                _copy_ticcmd(p.cmd, src)

    # Check for special buttons (pause / save)
    for i in range(MAXPLAYERS):
        p = doomstat.players[i]
        if doomstat.playeringame[i] and p:
            if p.cmd.buttons & TicCmd.BT_SPECIAL:
                mask = p.cmd.buttons & 0x7F  # BT_SPECIALMASK
                if mask == 1:   # BTS_PAUSE
                    doomstat.paused ^= True
                    if doomstat.paused:
                        _pause_sound()
                    else:
                        _resume_sound()

    oldgamestate = doomstat.gamestate

    # Main-state tick
    if doomstat.gamestate == GameState.LEVEL:
        _p_ticker()
    elif doomstat.gamestate == 1:  # GS_INTERMISSION
        pass  # wi_stuff.WI_Ticker() — stub
    elif doomstat.gamestate == 2:  # GS_FINALE
        pass  # f_finale.F_Ticker() — stub
    # GS_DEMOSCREEN: no-op


def _copy_ticcmd(dst: TicCmd, src: TicCmd):
    dst.forwardmove = src.forwardmove
    dst.sidemove    = src.sidemove
    dst.angleturn   = src.angleturn
    dst.consistancy = src.consistancy
    dst.chatchar    = src.chatchar
    dst.buttons     = src.buttons


def _p_ticker():
    try:
        import p_tick
        p_tick.P_Ticker()
    except (ImportError, AttributeError):
        pass


def _pause_sound():
    try:
        import s_sound
        s_sound.S_PauseSound()
    except (ImportError, AttributeError):
        pass


def _resume_sound():
    try:
        import s_sound
        s_sound.S_ResumeSound()
    except (ImportError, AttributeError):
        pass


# ------------------------------------------------------------------
# G_BuildTiccmd  — build a TicCmd from keyboard/mouse/joy input.
# In our port, callers supply the raw deltas; this function is the
# canonical translation layer.  Your hook should fill gamekeydown[],
# mousex, mousey before calling this each tic.
# ------------------------------------------------------------------
def G_BuildTiccmd(cmd: TicCmd, maketic: int):
    import doomstat
    global turnheld, mousex, mousey

    cmd.forwardmove = 0
    cmd.sidemove    = 0
    cmd.angleturn   = 0
    cmd.buttons     = 0
    cmd.chatchar    = 0

    strafe = gamekeydown[0x2C]   # key_strafe (default: alt)
    speed  = gamekeydown[0x36]   # key_speed  (default: shift)

    forward = side = 0

    # Turning acceleration
    if gamekeydown[0x4D] or gamekeydown[0x4B]:  # right / left
        turnheld += 1
    else:
        turnheld = 0

    tspeed = 2 if turnheld < SLOWTURNTICS else (1 if speed else 2)

    if strafe:
        if gamekeydown[0x4D]: side += sidemove[speed]
        if gamekeydown[0x4B]: side -= sidemove[speed]
    else:
        if gamekeydown[0x4D]: cmd.angleturn -= angleturn[tspeed]
        if gamekeydown[0x4B]: cmd.angleturn += angleturn[tspeed]

    if gamekeydown[0x48]: forward += forwardmove[speed]  # up
    if gamekeydown[0x50]: forward -= forwardmove[speed]  # down

    # Mouse look
    if mousex:
        cmd.angleturn -= mousex * 8
        mousex = 0
    if mousey:
        forward += mousey
        mousey = 0

    # Fire / use
    if gamekeydown[0x1D] or gamekeydown[0x38]:  # ctrl / alt
        cmd.buttons |= TicCmd.BT_ATTACK
    if gamekeydown[0x20]:                         # space
        cmd.buttons |= TicCmd.BT_USE

    # Clamp
    fwd_max = forwardmove[1]
    side_max = sidemove[1]
    if forward > fwd_max:    forward = fwd_max
    if forward < -fwd_max:   forward = -fwd_max
    if side > side_max:      side = side_max
    if side < -side_max:     side = -side_max

    cmd.forwardmove = forward
    cmd.sidemove    = side


def G_Responder(ev) -> bool:
    import doomstat
    from doomdef import GameState, ev_keydown, ev_keyup, ev_mouse
    global gameaction, sendpause, mousex, mousey

    # Changed from ev['type'] to ev.type
    if ev.type == ev_keydown:
        k = ev.data1 # Changed from ev.get('key')
        if 0 <= k < NUMKEYS:
            gamekeydown[k] = True
        if k == 0x19:   # 'p' = pause
            sendpause = True
        return True

    if ev.type == ev_keyup:
        k = ev.data1
        if 0 <= k < NUMKEYS:
            gamekeydown[k] = False
        return False

    if ev.type == ev_mouse:
        # Changed from ev.get('dx') to ev.data2/data3 based on standard porting
        mousex += ev.data2 * (doomstat.mouseSensitivity + 5) // 10
        mousey += ev.data3 * (doomstat.mouseSensitivity + 5) // 10
        
        buttons = ev.data1
        if buttons & 1:
            gamekeydown[0x1D] = True   # fire → ctrl
        else:
            gamekeydown[0x1D] = False
        return True

    return False
