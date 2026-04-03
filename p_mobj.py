import p_ceilng
import p_floor
import p_tick
# p_mobj.py
# Map Object (mobj_t) definition, spawn, remove, movement tick
# Ported from p_mobj.h / p_mobj.c

from doomdef import (
    FRACUNIT, FRACBITS, ANG45,
    MAXPLAYERS, TICRATE,
    fixed_mul,
)
from d_think import Thinker, thinkercap, thinker_is_removed

# ------------------------------------------------------------------
# Special Z values passed to P_SpawnMobj
# ------------------------------------------------------------------
ONFLOORZ   =  -0x80000000   # place on floor of sector
ONCEILINGZ =   0x7FFFFFFF   # hang from ceiling

# ------------------------------------------------------------------
# Physics constants
# ------------------------------------------------------------------
GRAVITY    = FRACUNIT        # one unit per tic²
MAXMOVE    = 30 * FRACUNIT
STOPSPEED  = 0x1000
FRICTION   = 0xe800
FLOATSPEED = 4 * FRACUNIT
VIEWHEIGHT = 41 * FRACUNIT
MELEERANGE = 64 * FRACUNIT
MISSILERANGE = 32 * 64 * FRACUNIT

ITEMQUESIZE = 128

# ------------------------------------------------------------------
# mobj flags  (mobjflag_t)
# ------------------------------------------------------------------
MF_SPECIAL     = 1
MF_SOLID       = 2
MF_SHOOTABLE   = 4
MF_NOSECTOR    = 8
MF_NOBLOCKMAP  = 16
MF_AMBUSH      = 32
MF_JUSTHIT     = 64
MF_JUSTATTACKED = 128
MF_SPAWNCEILING = 256
MF_NOGRAVITY   = 512
MF_DROPOFF     = 0x400
MF_PICKUP      = 0x800
MF_NOCLIP      = 0x1000
MF_SLIDE       = 0x2000
MF_FLOAT       = 0x4000
MF_TELEPORT    = 0x8000
MF_MISSILE     = 0x10000
MF_DROPPED     = 0x20000
MF_SHADOW      = 0x40000
MF_NOBLOOD     = 0x80000
MF_CORPSE      = 0x100000
MF_INFLOAT     = 0x200000
MF_COUNTKILL   = 0x400000
MF_COUNTITEM   = 0x800000
MF_SKULLFLY    = 0x1000000
MF_NOTDMATCH   = 0x2000000
MF_TRANSLATION = 0xc000000
MF_TRANSSHIFT  = 26

# Frame flag
FF_FULLBRIGHT  = 0x8000

# mapthing options
MTF_AMBUSH = 8

# ------------------------------------------------------------------
# Mobj class  (mobj_t)
# ------------------------------------------------------------------
class Mobj(Thinker):
    """
    A live map object.  Inherits from Thinker so it lives in the
    global thinker list and gets P_MobjThinker called each tic.
    """

    __slots__ = (
        # position
        'x', 'y', 'z',
        # sector links
        'snext', 'sprev',
        # rendering
        'angle', 'sprite', 'frame',
        # blockmap links
        'bnext', 'bprev',
        'subsector',
        # clipping heights
        'floorz', 'ceilingz',
        # collision
        'radius', 'height',
        # velocity
        'momx', 'momy', 'momz',
        'validcount',
        # type / info
        'type', 'info',
        # state machine
        'tics', 'state', 'flags', 'health',
        # AI movement
        'movedir', 'movecount',
        'target',
        'reactiontime',
        'threshold',
        # player link
        'player',
        'lastlook',
        # spawn record (for nightmare respawn)
        'spawnpoint',
        # tracer (homing)
        'tracer',
    )

    def __init__(self):
        super().__init__()
        self.x = 0
        self.y = 0
        self.z = 0
        self.snext  = None
        self.sprev  = None
        self.angle  = 0
        self.sprite = 0
        self.frame  = 0
        self.bnext  = None
        self.bprev  = None
        self.subsector  = None
        self.floorz     = 0
        self.ceilingz   = 0
        self.radius     = 0
        self.height     = 0
        self.momx       = 0
        self.momy       = 0
        self.momz       = 0
        self.validcount = 0
        self.type       = 0
        self.info       = None
        self.tics       = 0
        self.state      = None
        self.flags      = 0
        self.health     = 0
        self.movedir    = 0
        self.movecount  = 0
        self.target     = None
        self.reactiontime = 0
        self.threshold  = 0
        self.player     = None
        self.lastlook   = 0
        self.spawnpoint = None   # MapThing
        self.tracer     = None


# ------------------------------------------------------------------
# Item-respawn queue (P_RemoveMobj / P_RespawnSpecials)
# ------------------------------------------------------------------
itemrespawnque  = [None] * ITEMQUESIZE   # MapThing slots
itemrespawntime = [0]    * ITEMQUESIZE
iquehead = 0
iquetail = 0


# ------------------------------------------------------------------
# Forward-declared helpers (filled in by p_map.py / p_tick.py)
# ------------------------------------------------------------------
# These will be monkey-patched by the modules that implement them.
# This avoids circular imports while keeping the call sites identical
# to the C source.

def _not_ready(name):
    def _stub(*a, **kw):
        raise RuntimeError(f'{name} not yet initialised — check import order')
    _stub.__name__ = name
    return _stub

P_TryMove          = _not_ready('P_TryMove')
P_SlideMove        = _not_ready('P_SlideMove')
P_CheckPosition    = _not_ready('P_CheckPosition')
P_AproxDistance    = _not_ready('P_AproxDistance')
P_AimLineAttack    = _not_ready('P_AimLineAttack')
P_SetThingPosition = _not_ready('P_SetThingPosition')
P_UnsetThingPosition = _not_ready('P_UnsetThingPosition')
P_SetupPsprites    = _not_ready('P_SetupPsprites')
R_PointInSubsector = _not_ready('R_PointInSubsector')
R_PointToAngle2    = _not_ready('R_PointToAngle2')
S_StartSound       = _not_ready('S_StartSound')
S_StopSound        = _not_ready('S_StopSound')
G_PlayerReborn     = _not_ready('G_PlayerReborn')
G_DeathMatchSpawnPlayer = _not_ready('G_DeathMatchSpawnPlayer')

# fine-angle trig tables — set by tables.py / r_main.py
finecosine   = None
finesine     = None
ANGLETOFINESHIFT = 19

# Global state references (set during startup)
_states   = None   # list of State from info.py
_mobjinfo = None   # list of MobjInfo from info.py

# ------------------------------------------------------------------
# Circular-import-safe accessors
# ------------------------------------------------------------------
def _get_doomstat():
    import doomstat
    return doomstat

def _get_info():
    import info
    return info

def _get_p_spec():
    try:
        import p_spec
        return p_spec
    except ImportError:
        return None


# ------------------------------------------------------------------
# P_SetMobjState
# ------------------------------------------------------------------
MOBJ_CYCLE_LIMIT = 1_000_000

def P_SetMobjState(mobj: Mobj, statenum: int) -> bool:
    """
    Transition mobj to a new state.
    Returns False if the mobj was removed (S_NULL).
    """
    info_mod = _get_info()
    S_NULL   = info_mod.S_NULL
    states   = info_mod.states

    cycle_counter = 0
    while True:
        if statenum == S_NULL:
            mobj.state = S_NULL
            P_RemoveMobj(mobj)
            return False

        st = states[statenum]
        mobj.state  = st
        mobj.tics   = st.tics
        mobj.sprite = st.sprite
        mobj.frame  = st.frame

        if st.action is not None:
            st.action(mobj)

        statenum = st.nextstate

        cycle_counter += 1
        if cycle_counter > MOBJ_CYCLE_LIMIT:
            raise RuntimeError('P_SetMobjState: Infinite state cycle detected!')

        if mobj.tics != 0:
            break

    return True


# ------------------------------------------------------------------
# P_ExplodeMissile
# ------------------------------------------------------------------
def P_ExplodeMissile(mo: Mobj):
    from m_random import P_Random
    mo.momx = mo.momy = mo.momz = 0

    info_mod = _get_info()
    P_SetMobjState(mo, mo.info.deathstate)

    mo.tics -= P_Random() & 3
    if mo.tics < 1:
        mo.tics = 1

    mo.flags &= ~MF_MISSILE

    if mo.info.deathsound:
        S_StartSound(mo, mo.info.deathsound)


# ------------------------------------------------------------------
# P_XYMovement
# ------------------------------------------------------------------
def P_XYMovement(mo: Mobj):
    from m_random import P_Random
    from doomdef import fixed_mul
    import doomstat

    if not mo.momx and not mo.momy:
        if mo.flags & MF_SKULLFLY:
            mo.flags &= ~MF_SKULLFLY
            mo.momx = mo.momy = mo.momz = 0
            P_SetMobjState(mo, mo.info.spawnstate)
        return

    player = mo.player

    # clamp momentum
    if mo.momx > MAXMOVE:  mo.momx = MAXMOVE
    elif mo.momx < -MAXMOVE: mo.momx = -MAXMOVE
    if mo.momy > MAXMOVE:  mo.momy = MAXMOVE
    elif mo.momy < -MAXMOVE: mo.momy = -MAXMOVE

    xmove = mo.momx
    ymove = mo.momy

    while True:
        if xmove > MAXMOVE // 2 or ymove > MAXMOVE // 2:
            ptryx = mo.x + xmove // 2
            ptryy = mo.y + ymove // 2
            xmove >>= 1
            ymove >>= 1
        else:
            ptryx = mo.x + xmove
            ptryy = mo.y + ymove
            xmove = ymove = 0

        if not P_TryMove(mo, ptryx, ptryy):
            if mo.player:
                P_SlideMove(mo)
            elif mo.flags & MF_MISSILE:
                # sky hack
                import p_map
                if (p_map.ceilingline and
                        p_map.ceilingline.backsector and
                        p_map.ceilingline.backsector.ceilingpic == doomstat.skyflatnum):
                    P_RemoveMobj(mo)
                    return
                P_ExplodeMissile(mo)
            else:
                mo.momx = mo.momy = 0

        if not (xmove or ymove):
            break

    # friction / stop
    if player and (player.cheats & 4):   # CF_NOMOMENTUM
        mo.momx = mo.momy = 0
        return

    if mo.flags & (MF_MISSILE | MF_SKULLFLY):
        return

    if mo.z > mo.floorz:
        return   # airborne — no friction

    if mo.flags & MF_CORPSE:
        if (mo.momx > FRACUNIT // 4 or mo.momx < -(FRACUNIT // 4) or
                mo.momy > FRACUNIT // 4 or mo.momy < -(FRACUNIT // 4)):
            if mo.floorz != mo.subsector.sector.floorheight:
                return

    if (mo.momx > -STOPSPEED and mo.momx < STOPSPEED and
            mo.momy > -STOPSPEED and mo.momy < STOPSPEED and
            (not player or
             (player.cmd.forwardmove == 0 and player.cmd.sidemove == 0))):
        info_mod = _get_info()
        if player:
            idx = mo.state - info_mod.states  # won't work with list; use state index
            if (mo.state is not None and
                    hasattr(mo.state, 'statenum') and
                    0 <= (mo.state.statenum - info_mod.S_PLAY_RUN1) < 4):
                P_SetMobjState(player.mo, info_mod.S_PLAY)
        mo.momx = 0
        mo.momy = 0
    else:
        mo.momx = fixed_mul(mo.momx, FRICTION)
        mo.momy = fixed_mul(mo.momy, FRICTION)


# ------------------------------------------------------------------
# P_ZMovement
# ------------------------------------------------------------------
def P_ZMovement(mo: Mobj):
    import doomstat
    from doomdef import GameVersion

    # smooth step-up
    if mo.player and mo.z < mo.floorz:
        mo.player.viewheight -= mo.floorz - mo.z
        mo.player.deltaviewheight = (VIEWHEIGHT - mo.player.viewheight) >> 3

    mo.z += mo.momz

    # floater targeting
    if (mo.flags & MF_FLOAT) and mo.target:
        if not (mo.flags & (MF_SKULLFLY | MF_INFLOAT)):
            dist  = P_AproxDistance(mo.x - mo.target.x, mo.y - mo.target.y)
            delta = (mo.target.z + (mo.height >> 1)) - mo.z
            if delta < 0 and dist < -(delta * 3):
                mo.z -= FLOATSPEED
            elif delta > 0 and dist < (delta * 3):
                mo.z += FLOATSPEED

    # floor clip
    if mo.z <= mo.floorz:
        correct_bounce = doomstat.gameversion >= GameVersion.EXE_ULTIMATE

        if correct_bounce and (mo.flags & MF_SKULLFLY):
            mo.momz = -mo.momz

        if mo.momz < 0:
            if mo.player and mo.momz < -(GRAVITY * 8):
                mo.player.deltaviewheight = mo.momz >> 3
                import info as info_mod
                S_StartSound(mo, info_mod.sfx_oof)
            mo.momz = 0

        mo.z = mo.floorz

        if not correct_bounce and (mo.flags & MF_SKULLFLY):
            mo.momz = -mo.momz

        if (mo.flags & MF_MISSILE) and not (mo.flags & MF_NOCLIP):
            P_ExplodeMissile(mo)
            return

    elif not (mo.flags & MF_NOGRAVITY):
        if mo.momz == 0:
            mo.momz = -(GRAVITY * 2)
        else:
            mo.momz -= GRAVITY

    # ceiling clip
    if mo.z + mo.height > mo.ceilingz:
        if mo.momz > 0:
            mo.momz = 0
        mo.z = mo.ceilingz - mo.height

        if mo.flags & MF_SKULLFLY:
            mo.momz = -mo.momz

        if (mo.flags & MF_MISSILE) and not (mo.flags & MF_NOCLIP):
            P_ExplodeMissile(mo)


# ------------------------------------------------------------------
# P_NightmareRespawn
# ------------------------------------------------------------------
def P_NightmareRespawn(mobj: Mobj):
    from m_random import P_Random
    import info as info_mod

    x = mobj.spawnpoint.x << FRACBITS
    y = mobj.spawnpoint.y << FRACBITS

    if not P_CheckPosition(mobj, x, y):
        return

    # fog at old spot
    mo = P_SpawnMobj(mobj.x, mobj.y,
                     mobj.subsector.sector.floorheight,
                     info_mod.MT_TFOG)
    S_StartSound(mo, info_mod.sfx_telept)

    # fog at new spot
    ss = R_PointInSubsector(x, y)
    mo = P_SpawnMobj(x, y, ss.sector.floorheight, info_mod.MT_TFOG)
    S_StartSound(mo, info_mod.sfx_telept)

    mthing = mobj.spawnpoint
    z = ONCEILINGZ if (mobj.info.flags & MF_SPAWNCEILING) else ONFLOORZ

    mo = P_SpawnMobj(x, y, z, mobj.type)
    mo.spawnpoint = mobj.spawnpoint
    mo.angle      = ANG45 * (mthing.angle // 45)

    if mthing.options & MTF_AMBUSH:
        mo.flags |= MF_AMBUSH

    mo.reactiontime = 18
    P_RemoveMobj(mobj)


# ------------------------------------------------------------------
# P_MobjThinker  (the per-tic update, registered as thinker.function)
# ------------------------------------------------------------------
def P_MobjThinker(mobj: Mobj):
    import doomstat

    if mobj.momx or mobj.momy or (mobj.flags & MF_SKULLFLY):
        P_XYMovement(mobj)
        if thinker_is_removed(mobj):
            return

    if (mobj.z != mobj.floorz) or mobj.momz:
        P_ZMovement(mobj)
        if thinker_is_removed(mobj):
            return

    if mobj.tics != -1:
        mobj.tics -= 1
        if not mobj.tics:
            if not P_SetMobjState(mobj, mobj.state.nextstate):
                return   # freed itself
    else:
        # nightmare respawn check
        if not (mobj.flags & MF_COUNTKILL):
            return
        if not doomstat.respawnmonsters:
            return
        mobj.movecount += 1
        if mobj.movecount < 12 * TICRATE:
            return
        if doomstat.leveltime & 31:
            return
        from m_random import P_Random
        if P_Random() > 4:
            return
        P_NightmareRespawn(mobj)


# ------------------------------------------------------------------
# P_SpawnMobj
# ------------------------------------------------------------------
def P_SpawnMobj(x: int, y: int, z: int, type_: int) -> Mobj:
    import doomstat
    from m_random import P_Random
    import info as info_mod

    mobj        = Mobj()
    info        = info_mod.mobjinfo[type_]
    mobj.type   = type_
    mobj.info   = info
    mobj.x      = x
    mobj.y      = y
    mobj.radius = info.radius
    mobj.height = info.height
    mobj.flags  = info.flags
    mobj.health = info.spawnhealth

    from doomdef import Skill
    if doomstat.gameskill != Skill.NIGHTMARE:
        mobj.reactiontime = info.reactiontime

    mobj.lastlook = P_Random() % MAXPLAYERS

    st          = info_mod.states[info.spawnstate]
    mobj.state  = st
    mobj.tics   = st.tics
    mobj.sprite = st.sprite
    mobj.frame  = st.frame

    P_SetThingPosition(mobj)

    mobj.floorz   = mobj.subsector.sector.floorheight
    mobj.ceilingz = mobj.subsector.sector.ceilingheight

    if z == ONFLOORZ:
        mobj.z = mobj.floorz
    elif z == ONCEILINGZ:
        mobj.z = mobj.ceilingz - mobj.info.height
    else:
        mobj.z = z

    mobj.function = P_MobjThinker
    thinkercap.add(mobj)

    return mobj


# ------------------------------------------------------------------
# P_RemoveMobj
# ------------------------------------------------------------------
def P_RemoveMobj(mobj: Mobj):
    global iquehead, iquetail
    import info as info_mod
    import doomstat

    if ((mobj.flags & MF_SPECIAL) and
            not (mobj.flags & MF_DROPPED) and
            mobj.type not in (info_mod.MT_INV, info_mod.MT_INS)):
        itemrespawnque[iquehead]  = mobj.spawnpoint
        itemrespawntime[iquehead] = doomstat.leveltime
        iquehead = (iquehead + 1) & (ITEMQUESIZE - 1)
        if iquehead == iquetail:
            iquetail = (iquetail + 1) & (ITEMQUESIZE - 1)

    P_UnsetThingPosition(mobj)
    S_StopSound(mobj)
    mobj.mark_removed()


# ------------------------------------------------------------------
# P_RespawnSpecials
# ------------------------------------------------------------------
def P_RespawnSpecials():
    global iquetail
    import doomstat
    import info as info_mod

    if doomstat.deathmatch != 2:
        return
    if iquehead == iquetail:
        return
    if doomstat.leveltime - itemrespawntime[iquetail] < 30 * TICRATE:
        return

    mthing = itemrespawnque[iquetail]
    x = mthing.x << FRACBITS
    y = mthing.y << FRACBITS

    ss = R_PointInSubsector(x, y)
    mo = P_SpawnMobj(x, y, ss.sector.floorheight, info_mod.MT_IFOG)
    S_StartSound(mo, info_mod.sfx_itmbk)

    # find type
    type_idx = None
    for i, mi in enumerate(info_mod.mobjinfo):
        if mthing.type == mi.doomednum:
            type_idx = i
            break

    if type_idx is None:
        raise RuntimeError(f'P_RespawnSpecials: unknown doomednum {mthing.type}')

    z = ONCEILINGZ if (info_mod.mobjinfo[type_idx].flags & MF_SPAWNCEILING) else ONFLOORZ
    mo = P_SpawnMobj(x, y, z, type_idx)
    mo.spawnpoint = mthing
    mo.angle      = ANG45 * (mthing.angle // 45)

    iquetail = (iquetail + 1) & (ITEMQUESIZE - 1)


# ------------------------------------------------------------------
# P_SpawnPlayer
# ------------------------------------------------------------------
def P_SpawnPlayer(mthing):
    import doomstat
    import info as info_mod
    from doomdef import NUMCARDS

    if mthing.type == 0:
        return
    player_idx = mthing.type - 1
    if not doomstat.playeringame[player_idx]:
        return

    p = doomstat.players[player_idx]

    from d_player import PlayerState
    if p.playerstate == PlayerState.REBORN:
        G_PlayerReborn(player_idx)

    x = mthing.x << FRACBITS
    y = mthing.y << FRACBITS
    mobj = P_SpawnMobj(x, y, ONFLOORZ, info_mod.MT_PLAYER)

    if mthing.type > 1:
        mobj.flags |= (mthing.type - 1) << MF_TRANSSHIFT

    mobj.angle  = ANG45 * (mthing.angle // 45)
    mobj.player = p
    mobj.health = p.health

    p.mo             = mobj
    p.playerstate    = PlayerState.LIVE
    p.refire         = 0
    p.message        = None
    p.damagecount    = 0
    p.bonuscount     = 0
    p.extralight     = 0
    p.fixedcolormap  = 0
    p.viewheight     = VIEWHEIGHT

    P_SetupPsprites(p)

    if doomstat.deathmatch:
        for i in range(NUMCARDS):
            p.cards[i] = True

    if player_idx == doomstat.consoleplayer:
        # ST_Start() / HU_Start() — will be called by those modules
        pass


# ------------------------------------------------------------------
# P_SpawnMapThing
# ------------------------------------------------------------------
def P_SpawnMapThing(mthing):
    import doomstat
    import info as info_mod
    from doomdef import Skill

    # deathmatch start
    if mthing.type == 11:
        if doomstat.deathmatch_p < 10:
            doomstat.deathmatchstarts.append(mthing)
            doomstat.deathmatch_p += 1
        return

    if mthing.type <= 0:
        return

    # player starts
    if mthing.type <= 4:
        idx = mthing.type - 1
        doomstat.playerstarts[idx]       = mthing
        doomstat.playerstartsingame[idx] = True
        if not doomstat.deathmatch:
            P_SpawnPlayer(mthing)
        return

    # cooperative-only flag
    if not doomstat.netgame and (mthing.options & 16):
        return

    # skill filter
    sk = doomstat.gameskill
    if sk <= 1:
        bit = 1
    elif sk == Skill.NIGHTMARE:
        bit = 4
    else:
        bit = 1 << ((sk - 1) & 0x1F)

    if not (mthing.options & bit):
        return

    # find mobjinfo index by doomednum
    type_idx = None
    for i, mi in enumerate(info_mod.mobjinfo):
        if mthing.type == mi.doomednum:
            type_idx = i
            break

    if type_idx is None:
        raise RuntimeError(
            f'P_SpawnMapThing: Unknown type {mthing.type} at ({mthing.x},{mthing.y})')

    mi = info_mod.mobjinfo[type_idx]

    if doomstat.deathmatch and (mi.flags & MF_NOTDMATCH):
        return

    if doomstat.nomonsters and (
            type_idx == info_mod.MT_SKULL or (mi.flags & MF_COUNTKILL)):
        return

    x = mthing.x << FRACBITS
    y = mthing.y << FRACBITS
    z = ONCEILINGZ if (mi.flags & MF_SPAWNCEILING) else ONFLOORZ

    mobj = P_SpawnMobj(x, y, z, type_idx)
    mobj.spawnpoint = mthing

    from m_random import P_Random
    if mobj.tics > 0:
        mobj.tics = 1 + (P_Random() % mobj.tics)

    if mobj.flags & MF_COUNTKILL:  doomstat.totalkills  += 1
    if mobj.flags & MF_COUNTITEM:  doomstat.totalitems  += 1

    mobj.angle = ANG45 * (mthing.angle // 45)
    if mthing.options & MTF_AMBUSH:
        mobj.flags |= MF_AMBUSH


# ------------------------------------------------------------------
# P_SpawnPuff / P_SpawnBlood
# ------------------------------------------------------------------
def P_SpawnPuff(x: int, y: int, z: int):
    from m_random import P_Random
    import info as info_mod

    z += ((P_Random() - P_Random()) << 10)
    th = P_SpawnMobj(x, y, z, info_mod.MT_PUFF)
    th.momz = FRACUNIT
    th.tics -= P_Random() & 3
    if th.tics < 1:
        th.tics = 1
    import p_local
    if p_local.attackrange == MELEERANGE:
        P_SetMobjState(th, info_mod.S_PUFF3)


def P_SpawnBlood(x: int, y: int, z: int, damage: int):
    from m_random import P_Random
    import info as info_mod

    z += ((P_Random() - P_Random()) << 10)
    th = P_SpawnMobj(x, y, z, info_mod.MT_BLOOD)
    th.momz = FRACUNIT * 2
    th.tics -= P_Random() & 3
    if th.tics < 1:
        th.tics = 1
    if 9 <= damage <= 12:
        P_SetMobjState(th, info_mod.S_BLOOD2)
    elif damage < 9:
        P_SetMobjState(th, info_mod.S_BLOOD3)


# ------------------------------------------------------------------
# P_CheckMissileSpawn
# ------------------------------------------------------------------
def P_CheckMissileSpawn(th: Mobj):
    from m_random import P_Random
    th.tics -= P_Random() & 3
    if th.tics < 1:
        th.tics = 1
    th.x += th.momx >> 1
    th.y += th.momy >> 1
    th.z += th.momz >> 1
    if not P_TryMove(th, th.x, th.y):
        P_ExplodeMissile(th)


# ------------------------------------------------------------------
# P_SubstNullMobj  — null-pointer safety shim
# ------------------------------------------------------------------
_dummy_mobj = Mobj()

def P_SubstNullMobj(mobj):
    return mobj if mobj is not None else _dummy_mobj


# ------------------------------------------------------------------
# P_SpawnMissile / P_SpawnPlayerMissile
# ------------------------------------------------------------------
def P_SpawnMissile(source: Mobj, dest: Mobj, type_: int) -> Mobj:
    from m_random import P_Random
    import info as info_mod

    th = P_SpawnMobj(source.x, source.y,
                     source.z + 4 * 8 * FRACUNIT, type_)
    if th.info.seesound:
        S_StartSound(th, th.info.seesound)

    th.target = source
    an = R_PointToAngle2(source.x, source.y, dest.x, dest.y)

    if dest.flags & MF_SHADOW:
        an += (P_Random() - P_Random()) << 20

    th.angle = an & 0xFFFFFFFF
    fine_idx = (an >> ANGLETOFINESHIFT) & 0x1FFF
    th.momx = fixed_mul(th.info.speed, finecosine[fine_idx])
    th.momy = fixed_mul(th.info.speed, finesine[fine_idx])

    dist = P_AproxDistance(dest.x - source.x, dest.y - source.y)
    dist = dist // th.info.speed
    if dist < 1:
        dist = 1

    th.momz = (dest.z - source.z) // dist
    P_CheckMissileSpawn(th)
    return th


def P_SpawnPlayerMissile(source: Mobj, type_: int):
    import p_map   # for linetarget

    an    = source.angle
    slope = P_AimLineAttack(source, an, 16 * 64 * FRACUNIT)

    if not p_map.linetarget:
        an2 = (an + (1 << 26)) & 0xFFFFFFFF
        slope = P_AimLineAttack(source, an2, 16 * 64 * FRACUNIT)
        if p_map.linetarget:
            an = an2
        else:
            an3 = (an - (1 << 26)) & 0xFFFFFFFF
            slope = P_AimLineAttack(source, an3, 16 * 64 * FRACUNIT)
            if p_map.linetarget:
                an = an3
            else:
                an    = source.angle
                slope = 0

    x = source.x
    y = source.y
    z = source.z + 4 * 8 * FRACUNIT

    th = P_SpawnMobj(x, y, z, type_)

    import info as info_mod
    if th.info.seesound:
        S_StartSound(th, th.info.seesound)

    th.target = source
    th.angle  = an & 0xFFFFFFFF
    fine_idx  = (an >> ANGLETOFINESHIFT) & 0x1FFF
    th.momx   = fixed_mul(th.info.speed, finecosine[fine_idx])
    th.momy   = fixed_mul(th.info.speed, finesine[fine_idx])
    th.momz   = fixed_mul(th.info.speed, slope)

    P_CheckMissileSpawn(th)

# Map Object Flags (mobjflag_t)
MF_SPECIAL      = 1         # Call P_SpecialThing when touched
MF_SOLID        = 2         # Blocks movement
MF_SHOOTABLE    = 4         # Can be hit by hitscan and missiles
MF_NOSECTOR     = 8         # Don't use sector links
MF_NOBLOCKMAP   = 16        # Don't use blockmap links
MF_AMBUSH       = 32        # Deaf monster
MF_JUSTHIT      = 64        # Will try to attack right back
MF_JUSTATTACKED = 128       # Will be ignored by other monsters temporarily
MF_SPAWNCEILING = 256       # Hangs from ceiling (e.g. stalactites)
MF_NOGRAVITY    = 512       # Not affected by gravity
MF_DROPOFF      = 1024      # Can step off ledges
MF_PICKUP       = 2048      # Is an item that can be picked up
MF_NOCLIP       = 4096      # Can walk through walls (mostly for noclip cheat)
MF_SLIDE        = 8192      # Player sliding 
MF_FLOAT        = 16384     # Can fly (Cacodemon, Lost Soul)
MF_TELEPORT     = 32768     # Don't interpolate movement, teleported
MF_MISSILE      = 65536     # Is a projectile
MF_DROPPED      = 131072    # Dropped by a killed monster (half ammo)
MF_SHADOW       = 262144    # Partial invisibility (Spectre)
MF_NOBLOOD      = 524288    # Bleeds puffs instead of blood
MF_CORPSE       = 1048576   # Dead body
MF_INFLOAT      = 2097152   # Floating to a target height
MF_COUNTKILL    = 4194304   # Counts towards kill percentage
MF_COUNTITEM    = 8388608   # Counts towards item percentage
MF_SKULLFLY     = 16777216  # Lost Soul charging attack
MF_NOTDMATCH    = 33554432  # Doesn't spawn in Deathmatch
MF_TRANSLATION  = 0xc000000 # Player sprite translation map
MF_TRANSSHIFT   = 26
