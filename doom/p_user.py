import p_ceilng
import p_floor
import p_tick
# p_user.py
# Player per-tic logic: movement, view bobbing, death cam, weapon cycling
# Ported from p_user.c

from doomdef import (
    FRACBITS, FRACUNIT, ANG90, ANG180,
    fixed_mul, fixed_div,
    NUMPSPRITES,
)
from tables import ANGLETOFINESHIFT, FINEANGLES, finesine, finecosine
from p_mobj import (
    MF_NOCLIP, MF_JUSTATTACKED, MF_SHADOW,
    P_SetMobjState,
    VIEWHEIGHT,
)
from d_player import PlayerState, CheatFlags, TicCmd

MAXBOB        = 0x100000   # 16 pixels of bob
INVERSECOLORMAP = 32       # invul effect colormap index
ANG5          = ANG90 // 18

# ------------------------------------------------------------------
# P_Thrust  — apply momentum along angle
# ------------------------------------------------------------------
def P_Thrust(player, angle: int, move: int):
    fine = (angle >> ANGLETOFINESHIFT) & 0x1FFF
    player.mo.momx += fixed_mul(move, finecosine[fine])
    player.mo.momy += fixed_mul(move, finesine[fine])


# ------------------------------------------------------------------
# P_CalcHeight  — walking/running view bob
# ------------------------------------------------------------------
def P_CalcHeight(player):
    import doomstat

    player.bob = (fixed_mul(player.mo.momx, player.mo.momx) +
                  fixed_mul(player.mo.momy, player.mo.momy)) >> 2
    if player.bob > MAXBOB:
        player.bob = MAXBOB

    if (player.cheats & CheatFlags.NOMOMENTUM) or not _onground(player):
        player.viewz = player.mo.z + VIEWHEIGHT
        if player.viewz > player.mo.ceilingz - 4 * FRACUNIT:
            player.viewz = player.mo.ceilingz - 4 * FRACUNIT
        player.viewz = player.mo.z + player.viewheight
        return

    angle = (FINEANGLES // 20 * doomstat.leveltime) & (FINEANGLES - 1)
    bob   = fixed_mul(player.bob // 2, finesine[angle])

    if player.playerstate == PlayerState.LIVE:
        player.viewheight += player.deltaviewheight
        if player.viewheight > VIEWHEIGHT:
            player.viewheight    = VIEWHEIGHT
            player.deltaviewheight = 0
        if player.viewheight < VIEWHEIGHT // 2:
            player.viewheight = VIEWHEIGHT // 2
            if player.deltaviewheight <= 0:
                player.deltaviewheight = 1
        if player.deltaviewheight:
            player.deltaviewheight += FRACUNIT // 4
            if not player.deltaviewheight:
                player.deltaviewheight = 1

    player.viewz = player.mo.z + player.viewheight + bob
    if player.viewz > player.mo.ceilingz - 4 * FRACUNIT:
        player.viewz = player.mo.ceilingz - 4 * FRACUNIT


def _onground(player) -> bool:
    return player.mo.z <= player.mo.floorz


# ------------------------------------------------------------------
# P_MovePlayer  — apply ticcmd movement to player mobj
# ------------------------------------------------------------------
def P_MovePlayer(player):
    import info as info_mod
    cmd = player.cmd

    player.mo.angle = (player.mo.angle + (cmd.angleturn << FRACBITS)) & 0xFFFFFFFF

    on_ground = _onground(player)

    if cmd.forwardmove and on_ground:
        P_Thrust(player, player.mo.angle, cmd.forwardmove * 2048)

    if cmd.sidemove and on_ground:
        P_Thrust(player, (player.mo.angle - ANG90) & 0xFFFFFFFF,
                 cmd.sidemove * 2048)

    if (cmd.forwardmove or cmd.sidemove):
        if player.mo.state is info_mod.states[info_mod.S_PLAY]:
            P_SetMobjState(player.mo, info_mod.S_PLAY_RUN1)


# ------------------------------------------------------------------
# P_DeathThink  — POV falls, rotates toward killer
# ------------------------------------------------------------------
def P_DeathThink(player):
    from d_player import PlayerState

    _move_psprites(player)

    if player.viewheight > 6 * FRACUNIT:
        player.viewheight -= FRACUNIT
    if player.viewheight < 6 * FRACUNIT:
        player.viewheight = 6 * FRACUNIT

    player.deltaviewheight = 0
    P_CalcHeight(player)

    if player.attacker and player.attacker is not player.mo:
        from r_main import R_PointToAngle2
        angle = R_PointToAngle2(
            player.mo.x, player.mo.y,
            player.attacker.x, player.attacker.y)
        delta = (angle - player.mo.angle) & 0xFFFFFFFF

        if delta < ANG5 or delta > (0xFFFFFFFF - ANG5 + 1):
            player.mo.angle = angle
            if player.damagecount:
                player.damagecount -= 1
        elif delta < ANG180:
            player.mo.angle = (player.mo.angle + ANG5) & 0xFFFFFFFF
        else:
            player.mo.angle = (player.mo.angle - ANG5) & 0xFFFFFFFF
    elif player.damagecount:
        player.damagecount -= 1

    if player.cmd.buttons & TicCmd.BT_USE:
        player.playerstate = PlayerState.REBORN


# ------------------------------------------------------------------
# P_PlayerThink  — full per-tic player update
# ------------------------------------------------------------------
def P_PlayerThink(player):
    import doomstat, info as info_mod
    from doomdef import GameMode, PowerType, WeaponType, Skill

    # noclip cheat sync
    if player.cheats & CheatFlags.NOCLIP:
        player.mo.flags |= MF_NOCLIP
    else:
        player.mo.flags &= ~MF_NOCLIP

    cmd = player.cmd

    # chainsaw auto-run
    if player.mo.flags & MF_JUSTATTACKED:
        cmd.angleturn  = 0
        cmd.forwardmove = 0xc800 // 512
        cmd.sidemove   = 0
        player.mo.flags &= ~MF_JUSTATTACKED

    if player.playerstate == PlayerState.DEAD:
        P_DeathThink(player)
        return

    # movement freeze after teleport
    if player.mo.reactiontime:
        player.mo.reactiontime -= 1
    else:
        P_MovePlayer(player)

    P_CalcHeight(player)

    if player.mo.subsector.sector.special:
        _player_in_special_sector(player)

    # weapon change
    if cmd.buttons & TicCmd.BT_SPECIAL:
        cmd.buttons = 0

    if cmd.buttons & TicCmd.BT_CHANGE:
        newweapon = (cmd.buttons & TicCmd.BT_WEAPONMASK) >> TicCmd.BT_WEAPONSHIFT

        # fist → chainsaw preference
        if (newweapon == WeaponType.FIST and
                player.weaponowned[WeaponType.CHAINSAW] and
                not (player.readyweapon == WeaponType.CHAINSAW and
                     player.powers[PowerType.STRENGTH])):
            newweapon = WeaponType.CHAINSAW

        # shotgun → super shotgun preference (Doom II)
        if (doomstat.gamemode == GameMode.COMMERCIAL and
                newweapon == WeaponType.SHOTGUN and
                player.weaponowned[WeaponType.SUPERSHOTGUN] and
                player.readyweapon != WeaponType.SUPERSHOTGUN):
            newweapon = WeaponType.SUPERSHOTGUN

        if (player.weaponowned[newweapon] and
                newweapon != player.readyweapon):
            if ((newweapon not in (WeaponType.PLASMA, WeaponType.BFG)) or
                    doomstat.gamemode != GameMode.SHAREWARE):
                player.pendingweapon = newweapon

    # use button
    if cmd.buttons & TicCmd.BT_USE:
        if not player.usedown:
            from p_map import P_UseLines
            P_UseLines(player)
            player.usedown = True
    else:
        player.usedown = False

    # weapon sprites
    _move_psprites(player)

    # Power-up countdowns
    if player.powers[PowerType.STRENGTH]:
        player.powers[PowerType.STRENGTH] += 1
    if player.powers[PowerType.INVULNERABILITY]:
        player.powers[PowerType.INVULNERABILITY] -= 1
    if player.powers[PowerType.INVISIBILITY]:
        player.powers[PowerType.INVISIBILITY] -= 1
        if not player.powers[PowerType.INVISIBILITY]:
            player.mo.flags &= ~MF_SHADOW
    if player.powers[PowerType.INFRARED]:
        player.powers[PowerType.INFRARED] -= 1
    if player.powers[PowerType.IRONFEET]:
        player.powers[PowerType.IRONFEET] -= 1

    if player.damagecount:
        player.damagecount -= 1
    if player.bonuscount:
        player.bonuscount -= 1

    # Colormap effects
    if player.powers[PowerType.INVULNERABILITY]:
        if (player.powers[PowerType.INVULNERABILITY] > 4 * 32 or
                (player.powers[PowerType.INVULNERABILITY] & 8)):
            player.fixedcolormap = INVERSECOLORMAP
        else:
            player.fixedcolormap = 0
    elif player.powers[PowerType.INFRARED]:
        if (player.powers[PowerType.INFRARED] > 4 * 32 or
                (player.powers[PowerType.INFRARED] & 8)):
            player.fixedcolormap = 1
        else:
            player.fixedcolormap = 0
    else:
        player.fixedcolormap = 0


# ------------------------------------------------------------------
# Stubs for p_pspr.py (weapon sprite state machine)
# ------------------------------------------------------------------
def _move_psprites(player):
    try:
        import p_pspr
        p_pspr.P_MovePsprites(player)
    except (ImportError, AttributeError):
        pass


def _player_in_special_sector(player):
    try:
        import p_spec
        p_spec.P_PlayerInSpecialSector(player)
    except (ImportError, AttributeError):
        pass
