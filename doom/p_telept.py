import p_ceilng
import p_floor
import p_tick
import p_spec
# AUTO-GENERATED from p_telept.c
from doomdef import MF_MISSILE, ANGLETOFINESHIFT
from doomstat import sectors, numsectors, thinkercap, gameversion, exe_final
from info import MT_TELEPORTMAN, MT_TFOG
from p_local import P_TeleportMove, P_SpawnMobj, P_MobjThinker
from s_sound import S_StartSound
from sounds import sfx_telept
from tables import finecosine, finesine


def EV_Teleport(line, side, thing):
    if thing.flags & MF_MISSILE:
        return 0
    if side == 1:
        return 0

    tag = line.tag
    for i in range(numsectors):
        if sectors[i].tag == tag:
            thinker = thinkercap.next
            while thinker != thinkercap:
                if thinker.function != P_MobjThinker:
                    thinker = thinker.next
                    continue
                m = thinker  # mobj
                if m.type != MT_TELEPORTMAN:
                    thinker = thinker.next
                    continue
                sector = m.subsector.sector
                if sector is not sectors[i]:
                    thinker = thinker.next
                    continue

                oldx, oldy, oldz = thing.x, thing.y, thing.z

                if not P_TeleportMove(thing, m.x, m.y):
                    return 0

                if gameversion != exe_final:
                    thing.z = thing.floorz

                if thing.player:
                    thing.player.viewz = thing.z + thing.player.viewheight

                fog = P_SpawnMobj(oldx, oldy, oldz, MT_TFOG)
                S_StartSound(fog, sfx_telept)

                an = m.angle >> ANGLETOFINESHIFT
                fog = P_SpawnMobj(
                    m.x + 20 * finecosine[an],
                    m.y + 20 * finesine[an],
                    thing.z, MT_TFOG)
                S_StartSound(fog, sfx_telept)

                if thing.player:
                    thing.reactiontime = 18

                thing.angle = m.angle
                thing.momx = thing.momy = thing.momz = 0
                return 1

                thinker = thinker.next
    return 0
