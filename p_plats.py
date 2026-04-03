import p_ceilng
import p_floor
import p_tick
import p_spec
# AUTO-GENERATED from p_plats.c
from m_random import P_Random
from doomdef import FRACUNIT, PLATSPEED, PLATWAIT, TICRATE

import p_spec
from s_sound import S_StartSound
from sounds import sfx_pstart, sfx_pstop, sfx_stnmov
from doomstat import leveltime
import p_setup

MAXPLATS = 30
activeplats = [None] * MAXPLATS

# plat status values
up = 0; down = 1; waiting = 2; p_spec.in_stasis = 3

pastdest = 1; crushed = 2


def T_PlatRaise(plat):
    if plat.status == up:
        res = p_floor.T_MovePlane(plat.sector, plat.speed, plat.high, plat.crush, 0, 1)
        if plat.type in (p_spec.raiseAndChange, p_spec.raiseToNearestAndChange):
            if not (leveltime & 7):
                S_StartSound(plat.sector.soundorg, sfx_stnmov)
        if res == crushed and not plat.crush:
            plat.count = plat.wait
            plat.status = down
            S_StartSound(plat.sector.soundorg, sfx_pstart)
        elif res == pastdest:
            plat.count = plat.wait
            plat.status = waiting
            S_StartSound(plat.sector.soundorg, sfx_pstop)
            if plat.type in (p_spec.blazeDWUS, p_spec.downWaitUpStay, p_spec.raiseAndChange, p_spec.raiseToNearestAndChange):
                P_RemoveActivePlat(plat)

    elif plat.status == down:
        res = p_floor.T_MovePlane(plat.sector, plat.speed, plat.low, False, 0, -1)
        if res == pastdest:
            plat.count = plat.wait
            plat.status = waiting
            S_StartSound(plat.sector.soundorg, sfx_pstop)

    elif plat.status == waiting:
        plat.count -= 1
        if not plat.count:
            if plat.sector.floorheight == plat.low:
                plat.status = up
            else:
                plat.status = down
            S_StartSound(plat.sector.soundorg, sfx_pstart)


def EV_DoPlat(line, type, amount):
    secnum = -1
    rtn = 0
    if type == p_spec.perpetualRaise:
        P_ActivateInStasis(line.tag)
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0:
            break
        sec = p_setup.sectors[secnum]
        if sec.specialdata:
            continue
        rtn = 1
        from types import SimpleNamespace
        plat = SimpleNamespace()
        p_tick.P_AddThinker(plat)
        plat.type = type
        plat.sector = sec
        sec.specialdata = plat
        plat.function = T_PlatRaise
        plat.crush = False
        plat.tag = line.tag

        if type == p_spec.raiseToNearestAndChange:
            plat.speed = PLATSPEED // 2
            sec.floorpic = sec.lines[line.sidenum[0]].sector.floorpic  # simplified
            plat.high = p_spec.P_FindNextHighestFloor(sec, sec.floorheight)
            plat.wait = 0; plat.status = up
            sec.special = 0
            S_StartSound(sec.soundorg, sfx_stnmov)
        elif type == p_spec.raiseAndChange:
            plat.speed = PLATSPEED // 2
            plat.high = sec.floorheight + amount * FRACUNIT
            plat.wait = 0; plat.status = up
            S_StartSound(sec.soundorg, sfx_stnmov)
        elif type == p_spec.downWaitUpStay:
            plat.speed = PLATSPEED * 4
            plat.low = min(p_spec.P_FindLowestFloorSurrounding(sec), sec.floorheight)
            plat.high = sec.floorheight
            plat.wait = TICRATE * PLATWAIT
            plat.status = down
            S_StartSound(sec.soundorg, sfx_pstart)
        elif type == p_spec.blazeDWUS:
            plat.speed = PLATSPEED * 8
            plat.low = min(p_spec.P_FindLowestFloorSurrounding(sec), sec.floorheight)
            plat.high = sec.floorheight
            plat.wait = TICRATE * PLATWAIT
            plat.status = down
            S_StartSound(sec.soundorg, sfx_pstart)
        elif type == p_spec.perpetualRaise:
            plat.speed = PLATSPEED
            plat.low = min(p_spec.P_FindLowestFloorSurrounding(sec), sec.floorheight)
            plat.high = max(p_spec.P_FindHighestFloorSurrounding(sec), sec.floorheight)
            plat.wait = TICRATE * PLATWAIT
            plat.status = P_Random() & 1
            S_StartSound(sec.soundorg, sfx_pstart)

        P_AddActivePlat(plat)
    return rtn


def P_ActivateInStasis(tag):
    for i in range(MAXPLATS):
        p = activeplats[i]
        if p and p.tag == tag and p.status == p_spec.in_stasis:
            p.status = p.oldstatus
            p.function = T_PlatRaise


def EV_StopPlat(line):
    for j in range(MAXPLATS):
        p = activeplats[j]
        if p and p.status != p_spec.in_stasis and p.tag == line.tag:
            p.oldstatus = p.status
            p.status = p_spec.in_stasis
            p.function = None


def P_AddActivePlat(plat):
    for i in range(MAXPLATS):
        if activeplats[i] is None:
            activeplats[i] = plat
            return
    raise RuntimeError("P_AddActivePlat: no more plats!")


def P_RemoveActivePlat(plat):
    for i in range(MAXPLATS):
        if activeplats[i] is plat:
            activeplats[i].sector.specialdata = None
            p_tick.P_RemoveThinker(activeplats[i])
            activeplats[i] = None
            return
    raise RuntimeError("P_RemoveActivePlat: can't find plat!")
