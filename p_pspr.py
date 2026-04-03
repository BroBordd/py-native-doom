import p_ceilng
import p_floor
import p_tick
import p_spec
# p_pspr.py
# Weapon psprite state machine + all weapon A_* action functions
# Ported from p_pspr.c / p_pspr.h

from doomdef import (
    FRACBITS, FRACUNIT, ANG90, ANG180, ANG270,
    fixed_mul,
    NUMAMMO, WeaponType, AmmoType, PowerType,
    NUMPSPRITES,
)
from tables import ANGLETOFINESHIFT, FINEANGLES, finesine, finecosine
from p_mobj import (
    MF_SHADOW, MF_JUSTATTACKED,
    P_SetMobjState, P_SpawnMobj, P_SpawnMissile, P_SpawnPlayerMissile,
    MELEERANGE, MISSILERANGE,
)

LOWERSPEED   = FRACUNIT * 6
RAISESPEED   = FRACUNIT * 6
WEAPONBOTTOM = 128 * FRACUNIT
WEAPONTOP    = 32  * FRACUNIT

deh_bfg_cells_per_shot = 40

# Psprite slot indices
ps_weapon = 0
ps_flash  = 1

bulletslope: int = 0

# Weapon info table: [upstate, downstate, readystate, atkstate, flashstate, ammo]
# Indices match WeaponType.*
# These will be overridden by info.py when it loads; we stub them here.
weaponinfo = None   # set by info.py

swingx: int = 0
swingy: int = 0


def _wi(weapon, field):
    """Safe weaponinfo field access."""
    if weaponinfo is None:
        return 0
    return getattr(weaponinfo[weapon], field, 0)


# ------------------------------------------------------------------
# P_SetPsprite
# ------------------------------------------------------------------
def P_SetPsprite(player, position: int, statenum: int):
    import info as info_mod

    psp = player.psprites[position]

    while True:
        if statenum == 0:   # S_NULL
            psp.state = None
            break

        state = info_mod.states[statenum]
        psp.state = state
        psp.tics  = state.tics

        if state.misc1:
            psp.sx = state.misc1 << FRACBITS
            psp.sy = state.misc2 << FRACBITS

        if state.action is not None:
            state.action(player, psp)
            if psp.state is None:
                break

        statenum = psp.state.nextstate if psp.state else 0

        if psp.tics:
            break


# ------------------------------------------------------------------
# P_CalcSwing
# ------------------------------------------------------------------
def P_CalcSwing(player):
    global swingx, swingy
    import doomstat
    swing = player.bob
    angle  = (FINEANGLES // 70 * doomstat.leveltime) & (FINEANGLES - 1)
    swingx = fixed_mul(swing, finesine[angle])
    angle2 = (FINEANGLES // 70 * doomstat.leveltime + FINEANGLES // 2) & (FINEANGLES - 1)
    swingy = -fixed_mul(swingx, finesine[angle2])


# ------------------------------------------------------------------
# P_BringUpWeapon
# ------------------------------------------------------------------
def P_BringUpWeapon(player):
    import info as info_mod

    if player.pendingweapon == WeaponType.NOCHANGE:
        player.pendingweapon = player.readyweapon

    if player.pendingweapon == WeaponType.CHAINSAW:
        from p_mobj import S_StartSound
        S_StartSound(player.mo, info_mod.sfx_sawup)

    newstate = _wi(player.pendingweapon, 'upstate')
    player.pendingweapon = WeaponType.NOCHANGE
    player.psprites[ps_weapon].sy = WEAPONBOTTOM
    P_SetPsprite(player, ps_weapon, newstate)


# ------------------------------------------------------------------
# P_CheckAmmo
# ------------------------------------------------------------------
def P_CheckAmmo(player) -> bool:
    import doomstat
    from doomdef import GameMode

    ammo  = _wi(player.readyweapon, 'ammo')
    count = (deh_bfg_cells_per_shot if player.readyweapon == WeaponType.BFG
             else 2 if player.readyweapon == WeaponType.SUPERSHOTGUN
             else 1)

    if ammo == AmmoType.NOAMMO or player.ammo[ammo] >= count:
        return True

    # Out of ammo — find next best weapon
    while True:
        if (player.weaponowned[WeaponType.PLASMA] and
                player.ammo[AmmoType.CELL] and
                doomstat.gamemode != GameMode.SHAREWARE):
            player.pendingweapon = WeaponType.PLASMA
        elif (player.weaponowned[WeaponType.SUPERSHOTGUN] and
                player.ammo[AmmoType.SHELL] > 2 and
                doomstat.gamemode == GameMode.COMMERCIAL):
            player.pendingweapon = WeaponType.SUPERSHOTGUN
        elif player.weaponowned[WeaponType.CHAINGUN] and player.ammo[AmmoType.CLIP]:
            player.pendingweapon = WeaponType.CHAINGUN
        elif player.weaponowned[WeaponType.SHOTGUN] and player.ammo[AmmoType.SHELL]:
            player.pendingweapon = WeaponType.SHOTGUN
        elif player.ammo[AmmoType.CLIP]:
            player.pendingweapon = WeaponType.PISTOL
        elif player.weaponowned[WeaponType.CHAINSAW]:
            player.pendingweapon = WeaponType.CHAINSAW
        elif player.weaponowned[WeaponType.MISSILE] and player.ammo[AmmoType.MISL]:
            player.pendingweapon = WeaponType.MISSILE
        elif (player.weaponowned[WeaponType.BFG] and
                player.ammo[AmmoType.CELL] > 40 and
                doomstat.gamemode != GameMode.SHAREWARE):
            player.pendingweapon = WeaponType.BFG
        else:
            player.pendingweapon = WeaponType.FIST

        if player.pendingweapon != WeaponType.NOCHANGE:
            break

    P_SetPsprite(player, ps_weapon, _wi(player.readyweapon, 'downstate'))
    return False


# ------------------------------------------------------------------
# P_FireWeapon
# ------------------------------------------------------------------
def P_FireWeapon(player):
    import info as info_mod
    if not P_CheckAmmo(player):
        return
    P_SetMobjState(player.mo, info_mod.S_PLAY_ATK1)
    newstate = _wi(player.readyweapon, 'atkstate')
    P_SetPsprite(player, ps_weapon, newstate)
    P_NoiseAlert(player.mo, player.mo)


# ------------------------------------------------------------------
# P_DropWeapon
# ------------------------------------------------------------------
def P_DropWeapon(player):
    P_SetPsprite(player, ps_weapon, _wi(player.readyweapon, 'downstate'))


# ------------------------------------------------------------------
# P_NoiseAlert
# ------------------------------------------------------------------
def P_NoiseAlert(target, emitter):
    from p_enemy import P_NoiseAlert as _na
    _na(target, emitter)


# ------------------------------------------------------------------
# Helper: decrease ammo (with dehacked overflow emulation)
# ------------------------------------------------------------------
def _decrease_ammo(player, ammonum: int, amount: int):
    if ammonum < NUMAMMO:
        player.ammo[ammonum] -= amount
    else:
        player.maxammo[ammonum - NUMAMMO] -= amount


# ------------------------------------------------------------------
# A_WeaponReady
# ------------------------------------------------------------------
def A_WeaponReady(player, psp):
    import info as info_mod, doomstat
    from d_player import TicCmd

    if (player.mo.state is info_mod.states[info_mod.S_PLAY_ATK1] or
            player.mo.state is info_mod.states[info_mod.S_PLAY_ATK2]):
        P_SetMobjState(player.mo, info_mod.S_PLAY)

    if (player.readyweapon == WeaponType.CHAINSAW and
            psp.state is info_mod.states[info_mod.S_SAW]):
        from p_mobj import S_StartSound
        S_StartSound(player.mo, info_mod.sfx_sawidl)

    if player.pendingweapon != WeaponType.NOCHANGE or not player.health:
        newstate = _wi(player.readyweapon, 'downstate')
        P_SetPsprite(player, ps_weapon, newstate)
        return

    if player.cmd.buttons & TicCmd.BT_ATTACK:
        if (not player.attackdown or
                player.readyweapon not in (WeaponType.MISSILE, WeaponType.BFG)):
            player.attackdown = True
            P_FireWeapon(player)
            return
    else:
        player.attackdown = False

    # Weapon bob
    angle  = (128 * doomstat.leveltime) & (FINEANGLES - 1)
    psp.sx = FRACUNIT + fixed_mul(player.bob, finecosine[angle])
    angle2 = angle & (FINEANGLES // 2 - 1)
    psp.sy = WEAPONTOP + fixed_mul(player.bob, finesine[angle2])


# ------------------------------------------------------------------
# A_ReFire
# ------------------------------------------------------------------
def A_ReFire(player, psp):
    from d_player import TicCmd
    if (player.cmd.buttons & TicCmd.BT_ATTACK and
            player.pendingweapon == WeaponType.NOCHANGE and
            player.health):
        player.refire += 1
        P_FireWeapon(player)
    else:
        player.refire = 0
        P_CheckAmmo(player)


# ------------------------------------------------------------------
# A_CheckReload
# ------------------------------------------------------------------
def A_CheckReload(player, psp):
    P_CheckAmmo(player)


# ------------------------------------------------------------------
# A_Lower
# ------------------------------------------------------------------
def A_Lower(player, psp):
    import info as info_mod
    from d_player import PlayerState

    psp.sy += LOWERSPEED
    if psp.sy < WEAPONBOTTOM:
        return
    if player.playerstate == PlayerState.DEAD:
        psp.sy = WEAPONBOTTOM
        return
    if not player.health:
        P_SetPsprite(player, ps_weapon, 0)  # S_NULL
        return
    player.readyweapon = player.pendingweapon
    P_BringUpWeapon(player)


# ------------------------------------------------------------------
# A_Raise
# ------------------------------------------------------------------
def A_Raise(player, psp):
    psp.sy -= RAISESPEED
    if psp.sy > WEAPONTOP:
        return
    psp.sy = WEAPONTOP
    newstate = _wi(player.readyweapon, 'readystate')
    P_SetPsprite(player, ps_weapon, newstate)


# ------------------------------------------------------------------
# A_GunFlash
# ------------------------------------------------------------------
def A_GunFlash(player, psp):
    import info as info_mod
    P_SetMobjState(player.mo, info_mod.S_PLAY_ATK2)
    P_SetPsprite(player, ps_flash, _wi(player.readyweapon, 'flashstate'))


# ------------------------------------------------------------------
# Bullet slope helper
# ------------------------------------------------------------------
def P_BulletSlope(mo):
    global bulletslope
    from p_map import P_AimLineAttack, linetarget as _lt
    import p_map

    an = mo.angle
    bulletslope = P_AimLineAttack(mo, an, 16 * 64 * FRACUNIT)
    if not p_map.linetarget:
        an2 = (an + (1 << 26)) & 0xFFFFFFFF
        bulletslope = P_AimLineAttack(mo, an2, 16 * 64 * FRACUNIT)
        if not p_map.linetarget:
            an3 = (an - (1 << 26)) & 0xFFFFFFFF
            bulletslope = P_AimLineAttack(mo, an3, 16 * 64 * FRACUNIT)


def P_GunShot(mo, accurate: bool):
    from m_random import P_Random
    from p_map import P_LineAttack

    damage = 5 * (P_Random() % 3 + 1)
    angle  = mo.angle
    if not accurate:
        angle = (angle + ((P_Random() - P_Random()) << 18)) & 0xFFFFFFFF
    P_LineAttack(mo, angle, MISSILERANGE, bulletslope, damage)


# ------------------------------------------------------------------
# A_Punch
# ------------------------------------------------------------------
def A_Punch(player, psp):
    from m_random import P_Random
    from p_map import P_AimLineAttack, P_LineAttack, linetarget
    import p_map, info as info_mod
    from r_main import R_PointToAngle2

    damage = (P_Random() % 10 + 1) << 1
    if player.powers[PowerType.STRENGTH]:
        damage *= 10

    angle = (player.mo.angle + ((P_Random() - P_Random()) << 18)) & 0xFFFFFFFF
    slope = P_AimLineAttack(player.mo, angle, MELEERANGE)
    P_LineAttack(player.mo, angle, MELEERANGE, slope, damage)

    if p_map.linetarget:
        from p_mobj import S_StartSound
        S_StartSound(player.mo, info_mod.sfx_punch)
        player.mo.angle = R_PointToAngle2(
            player.mo.x, player.mo.y,
            p_map.linetarget.x, p_map.linetarget.y)


# ------------------------------------------------------------------
# A_Saw
# ------------------------------------------------------------------
def A_Saw(player, psp):
    from m_random import P_Random
    from p_map import P_AimLineAttack, P_LineAttack
    import p_map, info as info_mod
    from r_main import R_PointToAngle2

    damage = 2 * (P_Random() % 10 + 1)
    angle  = (player.mo.angle + ((P_Random() - P_Random()) << 18)) & 0xFFFFFFFF
    slope  = P_AimLineAttack(player.mo, angle, MELEERANGE + 1)
    P_LineAttack(player.mo, angle, MELEERANGE + 1, slope, damage)

    from p_mobj import S_StartSound
    if not p_map.linetarget:
        S_StartSound(player.mo, info_mod.sfx_sawful)
        return
    S_StartSound(player.mo, info_mod.sfx_sawhit)

    angle = R_PointToAngle2(player.mo.x, player.mo.y,
                            p_map.linetarget.x, p_map.linetarget.y)
    delta = (angle - player.mo.angle) & 0xFFFFFFFF
    if delta > ANG180:
        if (delta & 0x80000000) and (-(delta & 0x7FFFFFFF)) < -(ANG90 // 20):
            player.mo.angle = (angle + ANG90 // 21) & 0xFFFFFFFF
        else:
            player.mo.angle = (player.mo.angle - ANG90 // 20) & 0xFFFFFFFF
    else:
        if delta > ANG90 // 20:
            player.mo.angle = (angle - ANG90 // 21) & 0xFFFFFFFF
        else:
            player.mo.angle = (player.mo.angle + ANG90 // 20) & 0xFFFFFFFF
    player.mo.flags |= MF_JUSTATTACKED


# ------------------------------------------------------------------
# Weapon fire actions
# ------------------------------------------------------------------
def A_FireMissile(player, psp):
    import info as info_mod
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), 1)
    P_SpawnPlayerMissile(player.mo, info_mod.MT_ROCKET)


def A_FireBFG(player, psp):
    import info as info_mod
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), deh_bfg_cells_per_shot)
    P_SpawnPlayerMissile(player.mo, info_mod.MT_BFG)


def A_FirePlasma(player, psp):
    from m_random import P_Random
    import info as info_mod
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), 1)
    P_SetPsprite(player, ps_flash,
                 _wi(player.readyweapon, 'flashstate') + (P_Random() & 1))
    P_SpawnPlayerMissile(player.mo, info_mod.MT_PLASMA)


def A_FirePistol(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(player.mo, info_mod.sfx_pistol)
    P_SetMobjState(player.mo, info_mod.S_PLAY_ATK2)
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), 1)
    P_SetPsprite(player, ps_flash, _wi(player.readyweapon, 'flashstate'))
    P_BulletSlope(player.mo)
    P_GunShot(player.mo, not player.refire)


def A_FireShotgun(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(player.mo, info_mod.sfx_shotgn)
    P_SetMobjState(player.mo, info_mod.S_PLAY_ATK2)
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), 1)
    P_SetPsprite(player, ps_flash, _wi(player.readyweapon, 'flashstate'))
    P_BulletSlope(player.mo)
    for _ in range(7):
        P_GunShot(player.mo, False)


def A_FireShotgun2(player, psp):
    from m_random import P_Random
    from p_map import P_LineAttack
    import info as info_mod
    from p_mobj import S_StartSound

    S_StartSound(player.mo, info_mod.sfx_dshtgn)
    P_SetMobjState(player.mo, info_mod.S_PLAY_ATK2)
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), 2)
    P_SetPsprite(player, ps_flash, _wi(player.readyweapon, 'flashstate'))
    P_BulletSlope(player.mo)
    for _ in range(20):
        damage = 5 * (P_Random() % 3 + 1)
        angle  = (player.mo.angle + ((P_Random() - P_Random()) << ANGLETOFINESHIFT)) & 0xFFFFFFFF
        P_LineAttack(player.mo, angle, MISSILERANGE,
                     bulletslope + ((P_Random() - P_Random()) << 5), damage)


def A_FireCGun(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound

    S_StartSound(player.mo, info_mod.sfx_pistol)
    if not player.ammo[_wi(player.readyweapon, 'ammo')]:
        return
    P_SetMobjState(player.mo, info_mod.S_PLAY_ATK2)
    _decrease_ammo(player, _wi(player.readyweapon, 'ammo'), 1)

    # Flash offset based on current state index relative to S_CHAIN1
    try:
        state_offset = info_mod.states.index(psp.state) - info_mod.S_CHAIN1
    except (ValueError, AttributeError):
        state_offset = 0

    P_SetPsprite(player, ps_flash,
                 _wi(player.readyweapon, 'flashstate') + state_offset)
    P_BulletSlope(player.mo)
    P_GunShot(player.mo, not player.refire)


# ------------------------------------------------------------------
# Light effects
# ------------------------------------------------------------------
def A_Light0(player, psp): player.extralight = 0
def A_Light1(player, psp): player.extralight = 1
def A_Light2(player, psp): player.extralight = 2


# ------------------------------------------------------------------
# A_BFGSpray
# ------------------------------------------------------------------
def A_BFGSpray(mo):
    from m_random import P_Random
    from p_map import P_AimLineAttack
    import p_map, info as info_mod
    from p_inter import P_DamageMobj

    for i in range(40):
        an = (mo.angle - ANG90 // 2 + ANG90 // 40 * i) & 0xFFFFFFFF
        P_AimLineAttack(mo.target, an, 16 * 64 * FRACUNIT)
        if not p_map.linetarget:
            continue
        P_SpawnMobj(p_map.linetarget.x,
                    p_map.linetarget.y,
                    p_map.linetarget.z + (p_map.linetarget.height >> 2),
                    info_mod.MT_EXTRABFG)
        damage = sum((P_Random() & 7) + 1 for _ in range(15))
        P_DamageMobj(p_map.linetarget, mo.target, mo.target, damage)


def A_BFGsound(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(player.mo, info_mod.sfx_bfg)


# ------------------------------------------------------------------
# Super-shotgun actions
# ------------------------------------------------------------------
def A_OpenShotgun2(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(player.mo, info_mod.sfx_dbopn)


def A_LoadShotgun2(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(player.mo, info_mod.sfx_dbload)


def A_CloseShotgun2(player, psp):
    import info as info_mod
    from p_mobj import S_StartSound
    S_StartSound(player.mo, info_mod.sfx_dbcls)
    A_ReFire(player, psp)


# ------------------------------------------------------------------
# P_SetupPsprites  — called at level start for each player
# ------------------------------------------------------------------
def P_SetupPsprites(player):
    for i in range(NUMPSPRITES):
        player.psprites[i].state = None
    player.pendingweapon = player.readyweapon
    P_BringUpWeapon(player)


# ------------------------------------------------------------------
# P_MovePsprites  — called every tic
# ------------------------------------------------------------------
def P_MovePsprites(player):
    for i in range(NUMPSPRITES):
        psp = player.psprites[i]
        if psp.state:
            if psp.tics != -1:
                psp.tics -= 1
                if not psp.tics:
                    P_SetPsprite(player, i, psp.state.nextstate)

    # Sync flash position to weapon
    player.psprites[ps_flash].sx = player.psprites[ps_weapon].sx
    player.psprites[ps_flash].sy = player.psprites[ps_weapon].sy


# Patch p_mobj stub
import p_mobj as _pm
_pm.P_SetupPsprites = P_SetupPsprites
