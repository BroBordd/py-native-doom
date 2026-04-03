import p_floor
import p_tick
import p_spec
# AUTO-GENERATED from p_ceilng.c
from doomdef import FRACUNIT, CEILSPEED
from p_spec import CeilingMove
from s_sound import S_StartSound
from sounds import sfx_stnmov, sfx_pstop
from doomstat import leveltime
import p_setup

MAXCEILINGS = 30
activeceilings = [None] * MAXCEILINGS

# result_e values
pastdest = 1
crushed  = 2


def T_MoveCeiling(ceiling):
    if ceiling.direction == 0:
        return
    elif ceiling.direction == 1:
        res = p_floor.T_MovePlane(ceiling.sector, ceiling.speed,
                          ceiling.topheight, False, 1, ceiling.direction)
        if not (leveltime & 7):
            if ceiling.type != CeilingMove.silentCrushAndRaise:
                S_StartSound(ceiling.sector.soundorg, sfx_stnmov)
        if res == pastdest:
            if ceiling.type == CeilingMove.raiseToHighest:
                P_RemoveActiveCeiling(ceiling)
            elif ceiling.type in (CeilingMove.silentCrushAndRaise,):
                S_StartSound(ceiling.sector.soundorg, sfx_pstop)
                ceiling.direction = -1
            elif ceiling.type in (CeilingMove.fastCrushAndRaise, CeilingMove.crushAndRaise):
                ceiling.direction = -1
    elif ceiling.direction == -1:
        res = p_floor.T_MovePlane(ceiling.sector, ceiling.speed,
                          ceiling.bottomheight, ceiling.crush, 1, ceiling.direction)
        if not (leveltime & 7):
            if ceiling.type != CeilingMove.silentCrushAndRaise:
                S_StartSound(ceiling.sector.soundorg, sfx_stnmov)
        if res == pastdest:
            if ceiling.type == CeilingMove.silentCrushAndRaise:
                S_StartSound(ceiling.sector.soundorg, sfx_pstop)
                ceiling.speed = CEILSPEED
                ceiling.direction = 1
            elif ceiling.type == CeilingMove.crushAndRaise:
                ceiling.speed = CEILSPEED
                ceiling.direction = 1
            elif ceiling.type == CeilingMove.fastCrushAndRaise:
                ceiling.direction = 1
            elif ceiling.type in (CeilingMove.lowerAndCrush, CeilingMove.lowerToFloor):
                P_RemoveActiveCeiling(ceiling)
        elif res == crushed:
            if ceiling.type in (CeilingMove.silentCrushAndRaise, CeilingMove.crushAndRaise, CeilingMove.lowerAndCrush):
                ceiling.speed = CEILSPEED // 8


def EV_DoCeiling(line, type):
    secnum = -1
    rtn = 0
    if type in (CeilingMove.fastCrushAndRaise, CeilingMove.silentCrushAndRaise, CeilingMove.crushAndRaise):
        P_ActivateInStasisCeiling(line)
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0:
            break
        sec = p_setup.sectors[secnum]
        if sec.specialdata:
            continue
        rtn = 1
        ceiling = type('ceiling_t')  # placeholder; real impl uses object
        p_tick.P_AddThinker(ceiling.thinker)
        sec.specialdata = ceiling
        ceiling.thinker.function = T_MoveCeiling
        ceiling.sector = sec
        ceiling.crush = False
        if type == CeilingMove.fastCrushAndRaise:
            ceiling.crush = True
            ceiling.topheight = sec.ceilingheight
            ceiling.bottomheight = sec.floorheight + 8 * FRACUNIT
            ceiling.direction = -1
            ceiling.speed = CEILSPEED * 2
        elif type in (CeilingMove.silentCrushAndRaise, CeilingMove.crushAndRaise):
            ceiling.crush = True
            ceiling.topheight = sec.ceilingheight
            ceiling.bottomheight = sec.floorheight + 8 * FRACUNIT
            ceiling.direction = -1
            ceiling.speed = CEILSPEED
        elif type in (CeilingMove.lowerAndCrush, CeilingMove.lowerToFloor):
            ceiling.bottomheight = sec.floorheight
            if type != CeilingMove.lowerToFloor:
                ceiling.bottomheight += 8 * FRACUNIT
            ceiling.direction = -1
            ceiling.speed = CEILSPEED
        elif type == CeilingMove.raiseToHighest:
            ceiling.topheight = p_spec.P_FindHighestCeilingSurrounding(sec)
            ceiling.direction = 1
            ceiling.speed = CEILSPEED
        ceiling.tag = sec.tag
        ceiling.type = type
        P_AddActiveCeiling(ceiling)
    return rtn


def P_AddActiveCeiling(c):
    for i in range(MAXCEILINGS):
        if activeceilings[i] is None:
            activeceilings[i] = c
            return


def P_RemoveActiveCeiling(c):
    for i in range(MAXCEILINGS):
        if activeceilings[i] is c:
            activeceilings[i].sector.specialdata = None
            p_tick.P_RemoveThinker(activeceilings[i].thinker)
            activeceilings[i] = None
            return


def P_ActivateInStasisCeiling(line):
    for i in range(MAXCEILINGS):
        c = activeceilings[i]
        if c and c.tag == line.tag and c.direction == 0:
            c.direction = c.olddirection
            c.thinker.function = T_MoveCeiling


def EV_CeilingCrushStop(line):
    rtn = 0
    for i in range(MAXCEILINGS):
        c = activeceilings[i]
        if c and c.tag == line.tag and c.direction != 0:
            c.olddirection = c.direction
            c.thinker.function = None
            c.direction = 0
            rtn = 1
    return rtn
