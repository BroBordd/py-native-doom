import p_ceilng
import p_floor
import p_tick
import p_spec
# p_enemy.py
# Monster AI: look, chase, attack, special boss actions
# All monster A_* action functions
# Ported from p_enemy.c

from doomdef import (
    FRACBITS, FRACUNIT, ANG90, ANG180, ANG270,
    fixed_mul, MAXPLAYERS,
)
from tables import ANGLETOFINESHIFT, finesine, finecosine
from p_mobj import (
    MF_SHADOW, MF_AMBUSH, MF_JUSTHIT, MF_JUSTATTACKED,
    MF_SKULLFLY, MF_FLOAT, MF_INFLOAT, MF_SOLID, MF_CORPSE,
    MF_COUNTKILL, MF_SHOOTABLE, MF_NOCLIP,
    P_SetMobjState, P_SpawnMobj, P_SpawnMissile, P_SubstNullMobj,
    P_RemoveMobj,
    MELEERANGE, MISSILERANGE, FLOATSPEED, ONFLOORZ,
)
from p_map import (
    P_AproxDistance, P_CheckPosition, P_TryMove,
    P_BlockThingsIterator, P_BlockLinesIterator,
    P_UseSpecialLine, P_AimLineAttack, P_LineAttack,
    P_RadiusAttack, P_TeleportMove,
    floatok, tmfloorz, numspechit, spechit,
    MAPBLOCKSHIFT,
)

# Direction constants
DI_EAST      = 0
DI_NORTHEAST = 1
DI_NORTH     = 2
DI_NORTHWEST = 3
DI_WEST      = 4
DI_SOUTHWEST = 5
DI_SOUTH     = 6
DI_SOUTHEAST = 7
DI_NODIR     = 8
NUMDIRS      = 9

_opposite = [DI_WEST, DI_SOUTHWEST, DI_SOUTH, DI_SOUTHEAST,
             DI_EAST, DI_NORTHEAST, DI_NORTH, DI_NORTHWEST, DI_NODIR]

_diags = [DI_NORTHWEST, DI_NORTHEAST, DI_SOUTHWEST, DI_SOUTHEAST]

_xspeed = [FRACUNIT, 47000, 0, -47000, -FRACUNIT, -47000, 0,  47000]
_yspeed = [0,        47000, FRACUNIT, 47000,  0, -47000, -FRACUNIT, -47000]

TRACEANGLE  = 0xc000000
SKULLSPEED  = 20 * FRACUNIT
FATSPREAD   = ANG90 // 8

soundtarget = None

# Vile resurrection state
corpsehit = None
vileobj   = None
viletryx  = 0
viletryy  = 0

# Brain spit state
braintargets    = [None] * 32
numbraintargets = 0
braintargeton   = 0


# ------------------------------------------------------------------
# P_RecursiveSound
# ------------------------------------------------------------------
def P_RecursiveSound(sec, soundblocks: int):
    import p_setup, r_main
    from p_map import openrange, P_LineOpening
    from doomdef import ML_TWOSIDED, ML_SOUNDBLOCK

    if (sec.validcount == r_main.validcount and
            sec.soundtraversed <= soundblocks + 1):
        return

    sec.validcount    = r_main.validcount
    sec.soundtraversed = soundblocks + 1
    sec.soundtarget   = soundtarget

    for ld in sec.lines:
        if not (ld.flags & ML_TWOSIDED):
            continue
        P_LineOpening(ld)
        if openrange <= 0:
            continue
        other = ld.backsector if ld.frontsector is sec else ld.frontsector
        if other is None:
            continue
        if ld.flags & ML_SOUNDBLOCK:
            if not soundblocks:
                P_RecursiveSound(other, 1)
        else:
            P_RecursiveSound(other, soundblocks)


def P_NoiseAlert(target, emitter):
    global soundtarget
    import r_main
    soundtarget = target
    r_main.validcount += 1
    P_RecursiveSound(emitter.subsector.sector, 0)


# ------------------------------------------------------------------
# P_CheckMeleeRange
# ------------------------------------------------------------------
def P_CheckMeleeRange(actor) -> bool:
    import doomstat
    from doomdef import GameVersion
    from p_map import P_CheckSight

    if not actor.target:
        return False
    pl = actor.target
    dist = P_AproxDistance(pl.x - actor.x, pl.y - actor.y)
    if doomstat.gameversion < GameVersion.EXE_DOOM_1_7:
        rng = MELEERANGE
    else:
        rng = MELEERANGE - 20 * FRACUNIT + pl.info.radius
    if dist >= rng:
        return False
    return P_CheckSight(actor, actor.target)


# ------------------------------------------------------------------
# P_CheckMissileRange
# ------------------------------------------------------------------
def P_CheckMissileRange(actor) -> bool:
    from m_random import P_Random
    from p_map import P_CheckSight
    import info as info_mod

    if not P_CheckSight(actor, actor.target):
        return False
    if actor.flags & MF_JUSTHIT:
        actor.flags &= ~MF_JUSTHIT
        return True
    if actor.reactiontime:
        return False

    dist = (P_AproxDistance(actor.x - actor.target.x,
                             actor.y - actor.target.y) - 64 * FRACUNIT)
    if not actor.info.meleestate:
        dist -= 128 * FRACUNIT
    dist >>= FRACBITS

    if actor.type == info_mod.MT_VILE:
        if dist > 14 * 64: return False
    if actor.type == info_mod.MT_UNDEAD:
        if dist < 196: return False
        dist >>= 1
    if actor.type in (info_mod.MT_CYBORG, info_mod.MT_SPIDER, info_mod.MT_SKULL):
        dist >>= 1

    dist = min(dist, 200)
    if actor.type == info_mod.MT_CYBORG:
        dist = min(dist, 160)

    return P_Random() >= dist


# ------------------------------------------------------------------
# P_Move
# ------------------------------------------------------------------
def P_Move(actor) -> bool:
    import p_map

    if actor.movedir == DI_NODIR:
        return False

    tryx = actor.x + actor.info.speed * _xspeed[actor.movedir]
    tryy = actor.y + actor.info.speed * _yspeed[actor.movedir]

    try_ok = P_TryMove(actor, tryx, tryy)

    if not try_ok:
        if actor.flags & MF_FLOAT and p_map.floatok:
            if actor.z < p_map.tmfloorz:
                actor.z += FLOATSPEED
            else:
                actor.z -= FLOATSPEED
            actor.flags |= MF_INFLOAT
            return True

        if not p_map.numspechit:
            return False

        actor.movedir = DI_NODIR
        good = False
        i = p_map.numspechit
        while i > 0:
            i -= 1
            ld = p_map.spechit[i]
            if P_UseSpecialLine(actor, ld, 0):
                good = True
        return good
    else:
        actor.flags &= ~MF_INFLOAT

    if not (actor.flags & MF_FLOAT):
        actor.z = actor.floorz
    return True


def P_TryWalk(actor) -> bool:
    from m_random import P_Random
    if not P_Move(actor):
        return False
    actor.movecount = P_Random() & 15
    return True


# ------------------------------------------------------------------
# P_NewChaseDir
# ------------------------------------------------------------------
def P_NewChaseDir(actor):
    from m_random import P_Random

    olddir    = actor.movedir
    turnaround = _opposite[olddir]
    deltax = actor.target.x - actor.x
    deltay = actor.target.y - actor.y

    d = [DI_NODIR, DI_NODIR, DI_NODIR]
    d[1] = DI_EAST  if deltax >  10 * FRACUNIT else (DI_WEST  if deltax < -10 * FRACUNIT else DI_NODIR)
    d[2] = DI_SOUTH if deltay < -10 * FRACUNIT else (DI_NORTH if deltay >  10 * FRACUNIT else DI_NODIR)

    if d[1] != DI_NODIR and d[2] != DI_NODIR:
        actor.movedir = _diags[((deltay < 0) << 1) + (deltax > 0)]
        if actor.movedir != turnaround and P_TryWalk(actor):
            return

    if P_Random() > 200 or abs(deltay) > abs(deltax):
        d[1], d[2] = d[2], d[1]

    if d[1] == turnaround: d[1] = DI_NODIR
    if d[2] == turnaround: d[2] = DI_NODIR

    if d[1] != DI_NODIR:
        actor.movedir = d[1]
        if P_TryWalk(actor): return

    if d[2] != DI_NODIR:
        actor.movedir = d[2]
        if P_TryWalk(actor): return

    if olddir != DI_NODIR:
        actor.movedir = olddir
        if P_TryWalk(actor): return

    if P_Random() & 1:
        for tdir in range(DI_EAST, DI_SOUTHEAST + 1):
            if tdir != turnaround:
                actor.movedir = tdir
                if P_TryWalk(actor): return
    else:
        for tdir in range(DI_SOUTHEAST, DI_EAST - 1, -1):
            if tdir != turnaround:
                actor.movedir = tdir
                if P_TryWalk(actor): return

    if turnaround != DI_NODIR:
        actor.movedir = turnaround
        if P_TryWalk(actor): return

    actor.movedir = DI_NODIR


# ------------------------------------------------------------------
# P_LookForPlayers
# ------------------------------------------------------------------
def P_LookForPlayers(actor, allaround: bool) -> bool:
    import doomstat
    from r_main import R_PointToAngle2
    from p_map import P_CheckSight

    c    = 0
    stop = (actor.lastlook - 1) & 3

    while True:
        if not doomstat.playeringame[actor.lastlook]:
            actor.lastlook = (actor.lastlook + 1) & 3
            continue

        c += 1
        if c == 2 or actor.lastlook == stop:
            return False

        player = doomstat.players[actor.lastlook]
        actor.lastlook = (actor.lastlook + 1) & 3

        if not player or player.health <= 0:
            continue
        if not P_CheckSight(actor, player.mo):
            continue

        if not allaround:
            an = (R_PointToAngle2(actor.x, actor.y, player.mo.x, player.mo.y)
                  - actor.angle) & 0xFFFFFFFF
            if ANG90 < an < ANG270:
                dist = P_AproxDistance(player.mo.x - actor.x,
                                        player.mo.y - actor.y)
                if dist > MELEERANGE:
                    continue

        actor.target = player.mo
        return True


# ------------------------------------------------------------------
# A_Look
# ------------------------------------------------------------------
def A_Look(actor):
    import info as info_mod
    from m_random import P_Random
    from p_mobj import S_StartSound

    actor.threshold = 0
    targ = actor.subsector.sector.soundtarget

    if targ and (targ.flags & MF_SHOOTABLE):
        actor.target = targ
        if actor.flags & MF_AMBUSH:
            from p_map import P_CheckSight
            if not P_CheckSight(actor, actor.target):
                if not P_LookForPlayers(actor, False):
                    return
            # fall through to seeyou
        # seeyou:
    elif not P_LookForPlayers(actor, False):
        return

    # seeyou:
    if actor.info.seesound:
        snd = actor.info.seesound
        if snd in (info_mod.sfx_posit1, info_mod.sfx_posit2, info_mod.sfx_posit3):
            snd = info_mod.sfx_posit1 + P_Random() % 3
        elif snd in (info_mod.sfx_bgsit1, info_mod.sfx_bgsit2):
            snd = info_mod.sfx_bgsit1 + P_Random() % 2

        if actor.type in (info_mod.MT_SPIDER, info_mod.MT_CYBORG):
            S_StartSound(None, snd)
        else:
            S_StartSound(actor, snd)

    P_SetMobjState(actor, actor.info.seestate)


# ------------------------------------------------------------------
# A_Chase
# ------------------------------------------------------------------
def A_Chase(actor):
    import doomstat
    from m_random import P_Random
    from p_map import P_CheckSight

    if actor.reactiontime:
        actor.reactiontime -= 1

    if actor.threshold:
        from doomdef import GameVersion
        if (doomstat.gameversion > GameVersion.EXE_DOOM_1_7 and
                (not actor.target or actor.target.health <= 0)):
            actor.threshold = 0
        else:
            actor.threshold -= 1

    # Face movement direction
    if actor.movedir < 8:
        actor.angle &= (7 << 29)
        delta = (actor.angle - (actor.movedir << 29)) & 0xFFFFFFFF
        if delta > 0x80000000:
            actor.angle = (actor.angle + ANG90 // 2) & 0xFFFFFFFF
        elif delta:
            actor.angle = (actor.angle - ANG90 // 2) & 0xFFFFFFFF

    if not actor.target or not (actor.target.flags & MF_SHOOTABLE):
        if P_LookForPlayers(actor, True):
            return
        P_SetMobjState(actor, actor.info.spawnstate)
        return

    if actor.flags & MF_JUSTATTACKED:
        actor.flags &= ~MF_JUSTATTACKED
        if (doomstat.gameskill != 4 and not doomstat.fastparm):  # sk_nightmare=4
            P_NewChaseDir(actor)
        return

    if actor.info.meleestate and P_CheckMeleeRange(actor):
        if actor.info.attacksound:
            from p_mobj import S_StartSound
            S_StartSound(actor, actor.info.attacksound)
        P_SetMobjState(actor, actor.info.meleestate)
        return

    if actor.info.missilestate:
        if (doomstat.gameskill < 4 and not doomstat.fastparm and actor.movecount):
            pass  # goto nomissile
        elif P_CheckMissileRange(actor):
            P_SetMobjState(actor, actor.info.missilestate)
            actor.flags |= MF_JUSTATTACKED
            return

    # nomissile
    if (doomstat.netgame and not actor.threshold and
            not P_CheckSight(actor, actor.target)):
        if P_LookForPlayers(actor, True):
            return

    actor.movecount -= 1
    if actor.movecount < 0 or not P_Move(actor):
        P_NewChaseDir(actor)

    if actor.info.activesound and P_Random() < 3:
        from p_mobj import S_StartSound
        S_StartSound(actor, actor.info.activesound)


# ------------------------------------------------------------------
# A_FaceTarget
# ------------------------------------------------------------------
def A_FaceTarget(actor):
    from m_random import P_Random
    from r_main import R_PointToAngle2

    if not actor.target:
        return
    actor.flags &= ~MF_AMBUSH
    actor.angle = R_PointToAngle2(actor.x, actor.y,
                                   actor.target.x, actor.target.y)
    if actor.target.flags & MF_SHADOW:
        actor.angle = (actor.angle + ((P_Random() - P_Random()) << 21)) & 0xFFFFFFFF


# ------------------------------------------------------------------
# Monster attack helpers
# ------------------------------------------------------------------
def _face_and_missile(actor, mtype):
    A_FaceTarget(actor)
    P_SpawnMissile(actor, actor.target, mtype)


def A_PosAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_mobj import S_StartSound
    if not actor.target: return
    A_FaceTarget(actor)
    angle = (actor.angle + ((P_Random() - P_Random()) << 20)) & 0xFFFFFFFF
    slope = P_AimLineAttack(actor, actor.angle, MISSILERANGE)
    S_StartSound(actor, info_mod.sfx_pistol)
    damage = ((P_Random() % 5) + 1) * 3
    P_LineAttack(actor, angle, MISSILERANGE, slope, damage)


def A_SPosAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_mobj import S_StartSound
    if not actor.target: return
    S_StartSound(actor, info_mod.sfx_shotgn)
    A_FaceTarget(actor)
    bangle = actor.angle
    slope  = P_AimLineAttack(actor, bangle, MISSILERANGE)
    for _ in range(3):
        angle  = (bangle + ((P_Random() - P_Random()) << 20)) & 0xFFFFFFFF
        damage = ((P_Random() % 5) + 1) * 3
        P_LineAttack(actor, angle, MISSILERANGE, slope, damage)


def A_CPosAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_mobj import S_StartSound
    if not actor.target: return
    S_StartSound(actor, info_mod.sfx_shotgn)
    A_FaceTarget(actor)
    bangle = actor.angle
    slope  = P_AimLineAttack(actor, bangle, MISSILERANGE)
    angle  = (bangle + ((P_Random() - P_Random()) << 20)) & 0xFFFFFFFF
    damage = ((P_Random() % 5) + 1) * 3
    P_LineAttack(actor, angle, MISSILERANGE, slope, damage)


def A_CPosRefire(actor):
    from m_random import P_Random
    from p_map import P_CheckSight
    A_FaceTarget(actor)
    if P_Random() < 40: return
    if (not actor.target or actor.target.health <= 0 or
            not P_CheckSight(actor, actor.target)):
        P_SetMobjState(actor, actor.info.seestate)


def A_SpidRefire(actor):
    from m_random import P_Random
    from p_map import P_CheckSight
    A_FaceTarget(actor)
    if P_Random() < 10: return
    if (not actor.target or actor.target.health <= 0 or
            not P_CheckSight(actor, actor.target)):
        P_SetMobjState(actor, actor.info.seestate)


def A_BspiAttack(actor):
    import info as info_mod
    if not actor.target: return
    A_FaceTarget(actor)
    P_SpawnMissile(actor, actor.target, info_mod.MT_ARACHPLAZ)


def A_TroopAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_inter import P_DamageMobj
    from p_mobj import S_StartSound
    if not actor.target: return
    A_FaceTarget(actor)
    if P_CheckMeleeRange(actor):
        S_StartSound(actor, info_mod.sfx_claw)
        P_DamageMobj(actor.target, actor, actor, (P_Random() % 8 + 1) * 3)
        return
    P_SpawnMissile(actor, actor.target, info_mod.MT_TROOPSHOT)


def A_SargAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_inter import P_DamageMobj
    from doomdef import GameVersion
    import doomstat
    if not actor.target: return
    A_FaceTarget(actor)
    if doomstat.gameversion >= GameVersion.EXE_DOOM_1_7:
        if not P_CheckMeleeRange(actor): return
    damage = ((P_Random() % 10) + 1) * 4
    if doomstat.gameversion <= GameVersion.EXE_DOOM_1_7:
        P_LineAttack(actor, actor.angle, MELEERANGE, 0, damage)
    else:
        P_DamageMobj(actor.target, actor, actor, damage)


def A_HeadAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_inter import P_DamageMobj
    if not actor.target: return
    A_FaceTarget(actor)
    if P_CheckMeleeRange(actor):
        P_DamageMobj(actor.target, actor, actor, (P_Random() % 6 + 1) * 10)
        return
    P_SpawnMissile(actor, actor.target, info_mod.MT_HEADSHOT)


def A_CyberAttack(actor):
    import info as info_mod
    if not actor.target: return
    A_FaceTarget(actor)
    P_SpawnMissile(actor, actor.target, info_mod.MT_ROCKET)


def A_BruisAttack(actor):
    from m_random import P_Random
    import info as info_mod
    from p_inter import P_DamageMobj
    from p_mobj import S_StartSound
    if not actor.target: return
    if P_CheckMeleeRange(actor):
        S_StartSound(actor, info_mod.sfx_claw)
        P_DamageMobj(actor.target, actor, actor, (P_Random() % 8 + 1) * 10)
        return
    P_SpawnMissile(actor, actor.target, info_mod.MT_BRUISERSHOT)


def A_SkelMissile(actor):
    import info as info_mod
    if not actor.target: return
    A_FaceTarget(actor)
    actor.z += 16 * FRACUNIT
    mo = P_SpawnMissile(actor, actor.target, info_mod.MT_TRACER)
    actor.z -= 16 * FRACUNIT
    mo.x += mo.momx
    mo.y += mo.momy
    mo.tracer = actor.target


def A_Tracer(actor):
    from m_random import P_Random
    import info as info_mod
    import doomstat
    from r_main import R_PointToAngle2

    if doomstat.gametic & 3:
        return

    from p_mobj import P_SpawnPuff
    P_SpawnPuff(actor.x, actor.y, actor.z)

    th = P_SpawnMobj(actor.x - actor.momx, actor.y - actor.momy,
                     actor.z, info_mod.MT_SMOKE)
    th.momz = FRACUNIT
    th.tics -= P_Random() & 3
    if th.tics < 1: th.tics = 1

    dest = actor.tracer
    if not dest or dest.health <= 0:
        return

    exact = R_PointToAngle2(actor.x, actor.y, dest.x, dest.y)
    if exact != actor.angle:
        d = (exact - actor.angle) & 0xFFFFFFFF
        if d > 0x80000000:
            actor.angle = (actor.angle - TRACEANGLE) & 0xFFFFFFFF
            if ((exact - actor.angle) & 0xFFFFFFFF) < 0x80000000:
                actor.angle = exact
        else:
            actor.angle = (actor.angle + TRACEANGLE) & 0xFFFFFFFF
            if ((exact - actor.angle) & 0xFFFFFFFF) > 0x80000000:
                actor.angle = exact

    fine = (actor.angle >> ANGLETOFINESHIFT) & 0x1FFF
    actor.momx = fixed_mul(actor.info.speed, finecosine[fine])
    actor.momy = fixed_mul(actor.info.speed, finesine[fine])

    dist = max(1, P_AproxDistance(dest.x - actor.x, dest.y - actor.y) // actor.info.speed)
    slope = (dest.z + 40 * FRACUNIT - actor.z) // dist

    if slope < actor.momz: actor.momz -= FRACUNIT // 8
    else:                  actor.momz += FRACUNIT // 8


def A_SkelWhoosh(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    if not actor.target: return
    A_FaceTarget(actor)
    S_StartSound(actor, info_mod.sfx_skeswg)


def A_SkelFist(actor):
    from m_random import P_Random
    import info as info_mod
    from p_inter import P_DamageMobj
    from p_mobj import S_StartSound
    if not actor.target: return
    A_FaceTarget(actor)
    if P_CheckMeleeRange(actor):
        damage = ((P_Random() % 10) + 1) * 6
        S_StartSound(actor, info_mod.sfx_skepch)
        P_DamageMobj(actor.target, actor, actor, damage)


def PIT_VileCheck(thing) -> bool:
    global corpsehit
    import info as info_mod

    if not (thing.flags & MF_CORPSE): return True
    if thing.tics != -1:             return True
    if thing.info.raisestate == info_mod.S_NULL: return True

    maxdist = thing.info.radius + info_mod.mobjinfo[info_mod.MT_VILE].radius
    if (abs(thing.x - viletryx) > maxdist or
            abs(thing.y - viletryy) > maxdist):
        return True

    corpsehit = thing
    corpsehit.momx = corpsehit.momy = 0
    corpsehit.height <<= 2
    check = P_CheckPosition(corpsehit, corpsehit.x, corpsehit.y)
    corpsehit.height >>= 2
    if not check: return True
    return False


def A_VileChase(actor):
    global viletryx, viletryy, vileobj
    import info as info_mod
    import p_setup
    from p_mobj import S_StartSound

    if actor.movedir != DI_NODIR:
        viletryx = actor.x + actor.info.speed * _xspeed[actor.movedir]
        viletryy = actor.y + actor.info.speed * _yspeed[actor.movedir]

        xl = (viletryx - p_setup.bmaporgx - 2 * 64 * FRACUNIT) >> MAPBLOCKSHIFT
        xh = (viletryx - p_setup.bmaporgx + 2 * 64 * FRACUNIT) >> MAPBLOCKSHIFT
        yl = (viletryy - p_setup.bmaporgy - 2 * 64 * FRACUNIT) >> MAPBLOCKSHIFT
        yh = (viletryy - p_setup.bmaporgy + 2 * 64 * FRACUNIT) >> MAPBLOCKSHIFT

        vileobj = actor
        for bx in range(xl, xh + 1):
            for by in range(yl, yh + 1):
                if not P_BlockThingsIterator(bx, by, PIT_VileCheck):
                    temp = actor.target
                    actor.target = corpsehit
                    A_FaceTarget(actor)
                    actor.target = temp
                    P_SetMobjState(actor, info_mod.S_VILE_HEAL1)
                    S_StartSound(corpsehit, info_mod.sfx_slop)
                    info = corpsehit.info
                    P_SetMobjState(corpsehit, info.raisestate)
                    corpsehit.height <<= 2
                    corpsehit.flags  = info.flags
                    corpsehit.health = info.spawnhealth
                    corpsehit.target = None
                    return
    A_Chase(actor)


def A_VileStart(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_vilatk)


def A_Fire(actor):
    from p_map import P_CheckSight, P_SetThingPosition, P_UnsetThingPosition

    dest   = actor.tracer
    if not dest: return
    target = P_SubstNullMobj(actor.target)
    if not P_CheckSight(target, dest): return

    fine = (dest.angle >> ANGLETOFINESHIFT) & 0x1FFF
    P_UnsetThingPosition(actor)
    actor.x = dest.x + fixed_mul(24 * FRACUNIT, finecosine[fine])
    actor.y = dest.y + fixed_mul(24 * FRACUNIT, finesine[fine])
    actor.z = dest.z
    P_SetThingPosition(actor)


def A_StartFire(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_flamst)
    A_Fire(actor)


def A_FireCrackle(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_flame)
    A_Fire(actor)


def A_VileTarget(actor):
    import info as info_mod
    if not actor.target: return
    A_FaceTarget(actor)
    fog = P_SpawnMobj(actor.target.x, actor.target.y,
                      actor.target.z, info_mod.MT_FIRE)
    actor.tracer = fog
    fog.target   = actor
    fog.tracer   = actor.target
    A_Fire(fog)


def A_VileAttack(actor):
    import info as info_mod
    from p_inter import P_DamageMobj
    from p_mobj import S_StartSound

    if not actor.target: return
    A_FaceTarget(actor)
    from p_map import P_CheckSight
    if not P_CheckSight(actor, actor.target): return

    S_StartSound(actor, info_mod.sfx_barexp)
    P_DamageMobj(actor.target, actor, actor, 20)
    actor.target.momz = 1000 * FRACUNIT // actor.target.info.mass

    fine = (actor.angle >> ANGLETOFINESHIFT) & 0x1FFF
    fire = actor.tracer
    if not fire: return
    fire.x = actor.target.x - fixed_mul(24 * FRACUNIT, finecosine[fine])
    fire.y = actor.target.y - fixed_mul(24 * FRACUNIT, finesine[fine])
    P_RadiusAttack(fire, actor, 70)


def A_FatRaise(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    A_FaceTarget(actor)
    S_StartSound(actor, info_mod.sfx_manatk)


def A_FatAttack1(actor):
    import info as info_mod
    actor.angle = (actor.angle + FATSPREAD) & 0xFFFFFFFF
    target = P_SubstNullMobj(actor.target)
    P_SpawnMissile(actor, target, info_mod.MT_FATSHOT)
    mo = P_SpawnMissile(actor, target, info_mod.MT_FATSHOT)
    mo.angle = (mo.angle + FATSPREAD) & 0xFFFFFFFF
    fine = (mo.angle >> ANGLETOFINESHIFT) & 0x1FFF
    mo.momx = fixed_mul(mo.info.speed, finecosine[fine])
    mo.momy = fixed_mul(mo.info.speed, finesine[fine])


def A_FatAttack2(actor):
    import info as info_mod
    actor.angle = (actor.angle - FATSPREAD) & 0xFFFFFFFF
    target = P_SubstNullMobj(actor.target)
    P_SpawnMissile(actor, target, info_mod.MT_FATSHOT)
    mo = P_SpawnMissile(actor, target, info_mod.MT_FATSHOT)
    mo.angle = (mo.angle - FATSPREAD * 2) & 0xFFFFFFFF
    fine = (mo.angle >> ANGLETOFINESHIFT) & 0x1FFF
    mo.momx = fixed_mul(mo.info.speed, finecosine[fine])
    mo.momy = fixed_mul(mo.info.speed, finesine[fine])


def A_FatAttack3(actor):
    import info as info_mod
    target = P_SubstNullMobj(actor.target)
    mo = P_SpawnMissile(actor, target, info_mod.MT_FATSHOT)
    mo.angle = (mo.angle - FATSPREAD // 2) & 0xFFFFFFFF
    fine = (mo.angle >> ANGLETOFINESHIFT) & 0x1FFF
    mo.momx = fixed_mul(mo.info.speed, finecosine[fine])
    mo.momy = fixed_mul(mo.info.speed, finesine[fine])
    mo = P_SpawnMissile(actor, target, info_mod.MT_FATSHOT)
    mo.angle = (mo.angle + FATSPREAD // 2) & 0xFFFFFFFF
    fine = (mo.angle >> ANGLETOFINESHIFT) & 0x1FFF
    mo.momx = fixed_mul(mo.info.speed, finecosine[fine])
    mo.momy = fixed_mul(mo.info.speed, finesine[fine])


def A_SkullAttack(actor):
    if not actor.target: return
    dest = actor.target
    actor.flags |= MF_SKULLFLY
    from p_mobj import S_StartSound
    S_StartSound(actor, actor.info.attacksound)
    A_FaceTarget(actor)
    fine = (actor.angle >> ANGLETOFINESHIFT) & 0x1FFF
    actor.momx = fixed_mul(SKULLSPEED, finecosine[fine])
    actor.momy = fixed_mul(SKULLSPEED, finesine[fine])
    dist = max(1, P_AproxDistance(dest.x - actor.x, dest.y - actor.y) // SKULLSPEED)
    actor.momz = (dest.z + (dest.height >> 1) - actor.z) // dist


def A_PainShootSkull(actor, angle: int):
    from m_random import P_Random
    import info as info_mod
    from p_inter import P_DamageMobj
    from d_think import thinkercap
    from p_mobj import Mobj, P_MobjThinker

    count = sum(1 for th in thinkercap
                if isinstance(th, Mobj) and th.type == info_mod.MT_SKULL)
    if count > 20: return

    fine    = (angle >> ANGLETOFINESHIFT) & 0x1FFF
    prestep = (4 * FRACUNIT +
               3 * (actor.info.radius + info_mod.mobjinfo[info_mod.MT_SKULL].radius) // 2)
    x = actor.x + fixed_mul(prestep, finecosine[fine])
    y = actor.y + fixed_mul(prestep, finesine[fine])
    z = actor.z + 8 * FRACUNIT

    newmobj = P_SpawnMobj(x, y, z, info_mod.MT_SKULL)
    if not P_TryMove(newmobj, newmobj.x, newmobj.y):
        P_DamageMobj(newmobj, actor, actor, 10000)
        return
    newmobj.target = actor.target
    A_SkullAttack(newmobj)


def A_PainAttack(actor):
    if not actor.target: return
    A_FaceTarget(actor)
    A_PainShootSkull(actor, actor.angle)


def A_PainDie(actor):
    A_Fall(actor)
    A_PainShootSkull(actor, (actor.angle + ANG90)  & 0xFFFFFFFF)
    A_PainShootSkull(actor, (actor.angle + ANG180) & 0xFFFFFFFF)
    A_PainShootSkull(actor, (actor.angle + ANG270) & 0xFFFFFFFF)


def A_Scream(actor):
    from m_random import P_Random
    import info as info_mod
    from p_mobj import S_StartSound

    snd = actor.info.deathsound
    if not snd: return
    if snd in (info_mod.sfx_podth1, info_mod.sfx_podth2, info_mod.sfx_podth3):
        snd = info_mod.sfx_podth1 + P_Random() % 3
    elif snd in (info_mod.sfx_bgdth1, info_mod.sfx_bgdth2):
        snd = info_mod.sfx_bgdth1 + P_Random() % 2

    if actor.type in (info_mod.MT_SPIDER, info_mod.MT_CYBORG):
        S_StartSound(None, snd)
    else:
        S_StartSound(actor, snd)


def A_XScream(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_slop)


def A_Pain(actor):
    from p_mobj import S_StartSound
    if actor.info.painsound:
        S_StartSound(actor, actor.info.painsound)


def A_Fall(actor):
    actor.flags &= ~MF_SOLID


def A_Explode(actor):
    P_RadiusAttack(actor, actor.target, 128)


def A_KeenDie(actor):
    import info as info_mod
    from d_think import thinkercap
    from p_mobj import Mobj

    A_Fall(actor)
    for mo2 in thinkercap:
        if isinstance(mo2, Mobj) and mo2 is not actor and mo2.type == actor.type and mo2.health > 0:
            return

    junk = _fake_line(tag=666)
    from p_spec import p_doors
    p_doors.EV_DoDoor(junk, 3)  # vld_open=3


def A_BossDeath(actor):
    import doomstat
    import info as info_mod
    from doomdef import GameMode, GameVersion
    from d_think import thinkercap
    from p_mobj import Mobj
    from g_game import G_ExitLevel

    if doomstat.gamemode == GameMode.COMMERCIAL:
        if doomstat.gamemap != 7: return
        if actor.type not in (info_mod.MT_FATSO, info_mod.MT_BABY): return
    else:
        ep, gm = doomstat.gameepisode, doomstat.gamemap
        if doomstat.gameversion < GameVersion.EXE_ULTIMATE:
            if gm != 8: return
            if actor.type == info_mod.MT_BRUISER and ep != 1: return
        else:
            ok = {1: (gm == 8 and actor.type == info_mod.MT_BRUISER),
                  2: (gm == 8 and actor.type == info_mod.MT_CYBORG),
                  3: (gm == 8 and actor.type == info_mod.MT_SPIDER),
                  4: ((gm == 6 and actor.type == info_mod.MT_CYBORG) or
                      (gm == 8 and actor.type == info_mod.MT_SPIDER)),
                  }.get(ep, gm == 8)
            if not ok: return

    alive = any(doomstat.playeringame[i] and doomstat.players[i] and
                doomstat.players[i].health > 0 for i in range(MAXPLAYERS))
    if not alive: return

    for mo2 in thinkercap:
        if isinstance(mo2, Mobj) and mo2 is not actor and mo2.type == actor.type and mo2.health > 0:
            return

    # Victory
    if doomstat.gamemode == GameMode.COMMERCIAL and doomstat.gamemap == 7:
        from p_spec import p_floor, p_doors
        junk = _fake_line(tag=666 if actor.type == info_mod.MT_FATSO else 667)
        if actor.type == info_mod.MT_FATSO:
            p_floor.EV_DoFloor(junk, 1)   # lowerFloorToLowest
        else:
            p_floor.EV_DoFloor(junk, 12)  # raiseToTexture
        return

    if doomstat.gamemode != GameMode.COMMERCIAL:
        ep = doomstat.gameepisode
        if ep == 1:
            junk = _fake_line(tag=666)
            from p_spec import p_floor
            p_floor.EV_DoFloor(junk, 1)
            return
        elif ep == 4:
            gm = doomstat.gamemap
            if gm == 6:
                junk = _fake_line(tag=666)
                from p_spec import p_doors
                p_doors.EV_DoDoor(junk, 5)  # vld_blazeOpen
                return
            elif gm == 8:
                junk = _fake_line(tag=666)
                from p_spec import p_floor
                p_floor.EV_DoFloor(junk, 1)
                return

    G_ExitLevel()


class _fake_line:
    """Minimal line_t substitute for boss-death special triggers."""
    def __init__(self, tag=0):
        self.tag     = tag
        self.special = 0
        self.flags   = 0
        self.sidenum = (-1, -1)
        self.frontsector = None
        self.backsector  = None


def A_Hoof(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_hoof)
    A_Chase(actor)


def A_Metal(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_metal)
    A_Chase(actor)


def A_BabyMetal(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_bspwlk)
    A_Chase(actor)


def A_BrainAwake(actor):
    global numbraintargets, braintargeton
    import info as info_mod
    from d_think import thinkercap
    from p_mobj import Mobj, S_StartSound

    numbraintargets = 0
    braintargeton   = 0
    for mo in thinkercap:
        if isinstance(mo, Mobj) and mo.type == info_mod.MT_BOSSTARGET:
            braintargets[numbraintargets] = mo
            numbraintargets += 1
    S_StartSound(None, info_mod.sfx_bossit)


def A_BrainPain(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(None, info_mod.sfx_bospn)


def A_BrainScream(actor):
    from m_random import P_Random
    import info as info_mod
    x = actor.x - 196 * FRACUNIT
    while x < actor.x + 320 * FRACUNIT:
        y  = actor.y - 320 * FRACUNIT
        z  = 128 + P_Random() * 2 * FRACUNIT
        th = P_SpawnMobj(x, y, z, info_mod.MT_ROCKET)
        th.momz = P_Random() * 512
        P_SetMobjState(th, info_mod.S_BRAINEXPLODE1)
        th.tics -= P_Random() & 7
        if th.tics < 1: th.tics = 1
        x += FRACUNIT * 8
    from p_mobj import S_StartSound
    S_StartSound(None, info_mod.sfx_bosdth)


def A_BrainExplode(actor):
    from m_random import P_Random
    import info as info_mod
    x  = actor.x + (P_Random() - P_Random()) * 2048
    z  = 128 + P_Random() * 2 * FRACUNIT
    th = P_SpawnMobj(x, actor.y, z, info_mod.MT_ROCKET)
    th.momz = P_Random() * 512
    P_SetMobjState(th, info_mod.S_BRAINEXPLODE1)
    th.tics -= P_Random() & 7
    if th.tics < 1: th.tics = 1


def A_BrainDie(actor):
    from g_game import G_ExitLevel
    G_ExitLevel()


_easy_toggle = [0]

def A_BrainSpit(actor):
    global braintargeton
    from m_random import P_Random
    import info as info_mod, doomstat
    from p_mobj import S_StartSound

    _easy_toggle[0] ^= 1
    if doomstat.gameskill <= 1 and not _easy_toggle[0]:
        return
    if numbraintargets == 0:
        raise RuntimeError('A_BrainSpit: no brain targets')

    targ = braintargets[braintargeton]
    braintargeton = (braintargeton + 1) % numbraintargets

    newmobj = P_SpawnMissile(actor, targ, info_mod.MT_SPAWNSHOT)
    newmobj.target = targ
    newmobj.reactiontime = (
        ((targ.y - actor.y) // newmobj.momy) // newmobj.state.tics
        if newmobj.momy and newmobj.state else 1)
    S_StartSound(None, info_mod.sfx_bospit)


def A_SpawnSound(actor):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(actor, info_mod.sfx_boscub)
    A_SpawnFly(actor)


def A_SpawnFly(actor):
    from m_random import P_Random
    import info as info_mod
    from p_mobj import S_StartSound

    actor.reactiontime -= 1
    if actor.reactiontime:
        return

    targ = P_SubstNullMobj(actor.target)
    fog  = P_SpawnMobj(targ.x, targ.y, targ.z, info_mod.MT_SPAWNFIRE)
    S_StartSound(fog, info_mod.sfx_telept)

    r = P_Random()
    if   r < 50:  mtype = info_mod.MT_TROOP
    elif r < 90:  mtype = info_mod.MT_SERGEANT
    elif r < 120: mtype = info_mod.MT_SHADOWS
    elif r < 130: mtype = info_mod.MT_PAIN
    elif r < 160: mtype = info_mod.MT_HEAD
    elif r < 162: mtype = info_mod.MT_VILE
    elif r < 172: mtype = info_mod.MT_UNDEAD
    elif r < 192: mtype = info_mod.MT_BABY
    elif r < 222: mtype = info_mod.MT_FATSO
    elif r < 246: mtype = info_mod.MT_KNIGHT
    else:         mtype = info_mod.MT_BRUISER

    newmobj = P_SpawnMobj(targ.x, targ.y, targ.z, mtype)
    if P_LookForPlayers(newmobj, True):
        P_SetMobjState(newmobj, newmobj.info.seestate)
    P_TeleportMove(newmobj, newmobj.x, newmobj.y)
    P_RemoveMobj(actor)


def A_PlayerScream(actor):
    import doomstat, info as info_mod
    from doomdef import GameMode
    from p_mobj import S_StartSound
    snd = info_mod.sfx_pldeth
    if doomstat.gamemode == GameMode.COMMERCIAL and actor.health < -50:
        snd = info_mod.sfx_pdiehi
    S_StartSound(actor, snd)
