import p_ceilng
import p_floor
import p_tick
import p_spec
# AUTO-GENERATED from p_lights.c
from m_random import P_Random
# C macros originally local to p_lights.c
GLOWSPEED = 8
STROBEBRIGHT = 5
FASTDARK = 15
SLOWDARK = 35

import p_setup

FRACUNIT = 1 << 16


def T_FireFlicker(flick):
    flick.count -= 1
    if flick.count:
        return
    amount = (P_Random() & 3) * 16
    if flick.sector.lightlevel - amount < flick.minlight:
        flick.sector.lightlevel = flick.minlight
    else:
        flick.sector.lightlevel = flick.maxlight - amount
    flick.count = 4


def P_SpawnFireFlicker(sector):
    sector.special = 0
    flick = SimpleNamespace()
    p_tick.P_AddThinker(flick)
    flick.function = T_FireFlicker
    flick.sector = sector
    flick.maxlight = sector.lightlevel
    flick.minlight = P_FindMinSurroundingLight(sector, sector.lightlevel) + 16
    flick.count = 4


def T_LightFlash(flash):
    flash.count -= 1
    if flash.count:
        return
    if flash.sector.lightlevel == flash.maxlight:
        flash.sector.lightlevel = flash.minlight
        flash.count = (P_Random() & flash.mintime) + 1
    else:
        flash.sector.lightlevel = flash.maxlight
        flash.count = (P_Random() & flash.maxtime) + 1


def P_SpawnLightFlash(sector):
    sector.special = 0
    flash = SimpleNamespace()
    p_tick.P_AddThinker(flash)
    flash.function = T_LightFlash
    flash.sector = sector
    flash.maxlight = sector.lightlevel
    flash.minlight = P_FindMinSurroundingLight(sector, sector.lightlevel)
    flash.maxtime = 64
    flash.mintime = 7
    flash.count = (P_Random() & flash.maxtime) + 1


def T_StrobeFlash(flash):
    flash.count -= 1
    if flash.count:
        return
    if flash.sector.lightlevel == flash.minlight:
        flash.sector.lightlevel = flash.maxlight
        flash.count = flash.brighttime
    else:
        flash.sector.lightlevel = flash.minlight
        flash.count = flash.darktime


def P_SpawnStrobeFlash(sector, fastOrSlow, inSync):
    flash = SimpleNamespace()
    p_tick.P_AddThinker(flash)
    flash.sector = sector
    flash.darktime = fastOrSlow
    flash.brighttime = STROBEBRIGHT
    flash.function = T_StrobeFlash
    flash.maxlight = sector.lightlevel
    flash.minlight = P_FindMinSurroundingLight(sector, sector.lightlevel)
    if flash.minlight == flash.maxlight:
        flash.minlight = 0
    sector.special = 0
    flash.count = 1 if inSync else (P_Random() & 7) + 1


def EV_StartLightStrobing(line):
    secnum = -1
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0:
            break
        sec = p_setup.sectors[secnum]
        if sec.specialdata:
            continue
        P_SpawnStrobeFlash(sec, SLOWDARK, 0)


def EV_TurnTagLightsOff(line):
    sector = p_setup.sectors
    for j in range(p_setup.numsectors):
        sec = p_setup.sectors[j]
        if sec.tag == line.tag:
            min_light = sec.lightlevel
            for i in range(sec.linecount):
                templine = sec.lines[i]
                tsec = getNextSector(templine, sec)
                if not tsec:
                    continue
                if tsec.lightlevel < min_light:
                    min_light = tsec.lightlevel
            sec.lightlevel = min_light


def EV_LightTurnOn(line, bright):
    for i in range(p_setup.numsectors):
        sec = p_setup.sectors[i]
        if sec.tag == line.tag:
            if not bright:
                for j in range(sec.linecount):
                    templine = sec.lines[j]
                    temp = getNextSector(templine, sec)
                    if not temp:
                        continue
                    if temp.lightlevel > bright:
                        bright = temp.lightlevel
            sec.lightlevel = bright


def T_Glow(g):
    if g.direction == -1:
        g.sector.lightlevel -= GLOWSPEED
        if g.sector.lightlevel <= g.minlight:
            g.sector.lightlevel += GLOWSPEED
            g.direction = 1
    elif g.direction == 1:
        g.sector.lightlevel += GLOWSPEED
        if g.sector.lightlevel >= g.maxlight:
            g.sector.lightlevel -= GLOWSPEED
            g.direction = -1


def P_SpawnGlowingLight(sector):
    g = SimpleNamespace()
    p_tick.P_AddThinker(g)
    g.sector = sector
    g.minlight = P_FindMinSurroundingLight(sector, sector.lightlevel)
    g.maxlight = sector.lightlevel
    g.function = T_Glow
    g.direction = -1
    sector.special = 0


# lazy import to avoid circular
from types import SimpleNamespace
