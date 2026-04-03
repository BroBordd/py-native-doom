import p_ceilng
import p_floor
import p_tick
import p_spec
# p_inter.py
# Item pickup, damage, and kill interactions
# Ported from p_inter.c / p_inter.h

from doomdef import (
    FRACBITS, FRACUNIT, ANG180,
    NUMAMMO, NUMWEAPONS, NUMCARDS,
    AmmoType, WeaponType, CardType, PowerType,
    fixed_mul,
)
from p_mobj import (
    MF_SHADOW, MF_SOLID, MF_CORPSE, MF_DROPOFF,
    MF_NOGRAVITY, MF_SHOOTABLE, MF_FLOAT, MF_SKULLFLY,
    MF_NOBLOOD, MF_DROPPED, MF_COUNTITEM, MF_COUNTKILL,
    ONFLOORZ, MF_NOCLIP,
    P_SetMobjState, P_RemoveMobj, P_SpawnMobj,
)

BONUSADD = 6

# Ammo capacities and clip sizes
maxammo  = [200, 50, 300, 50]    # index = AmmoType.*
clipammo = [ 10,  4,  20,  1]

# Power-up durations (tics)
INVULNTICS = 30 * 35
INVISTICS  = 60 * 35
INFRATICS  = 120 * 35
IRONTICS   = 60 * 35

# Health limits (can be overridden by dehacked in full port)
MAXHEALTH       = 100
deh_initial_health  = 100
deh_initial_bullets = 50
deh_max_health      = 200
deh_max_soulsphere  = 200
deh_max_armor       = 200
deh_soulsphere_health = 100
deh_megasphere_health = 200
deh_green_armor_class = 1
deh_blue_armor_class  = 2
BASETHRESHOLD       = 100

# Weapon info: ammo type per weapon (matches weaponinfo[] in p_pspr.c)
_weapon_ammo = [
    AmmoType.NOAMMO,  # fist
    AmmoType.CLIP,    # pistol
    AmmoType.SHELL,   # shotgun
    AmmoType.CLIP,    # chaingun
    AmmoType.MISL,    # rocket launcher
    AmmoType.CELL,    # plasma
    AmmoType.CELL,    # bfg
    AmmoType.NOAMMO,  # chainsaw
    AmmoType.SHELL,   # super shotgun
]


# ------------------------------------------------------------------
# P_GiveAmmo
# ------------------------------------------------------------------
def P_GiveAmmo(player, ammo: int, num: int) -> bool:
    import doomstat
    from doomdef import Skill

    if ammo == AmmoType.NOAMMO:
        return False
    if player.ammo[ammo] == player.maxammo[ammo]:
        return False

    if num:
        num *= clipammo[ammo]
    else:
        num = clipammo[ammo] // 2

    if doomstat.gameskill in (Skill.BABY, Skill.NIGHTMARE):
        num <<= 1

    oldammo = player.ammo[ammo]
    player.ammo[ammo] = min(player.ammo[ammo] + num, player.maxammo[ammo])

    if oldammo:
        return True   # was already armed

    # Auto-switch weapon if we were dry
    if ammo == AmmoType.CLIP:
        if player.readyweapon == WeaponType.FIST:
            if player.weaponowned[WeaponType.CHAINGUN]:
                player.pendingweapon = WeaponType.CHAINGUN
            else:
                player.pendingweapon = WeaponType.PISTOL
    elif ammo == AmmoType.SHELL:
        if player.readyweapon in (WeaponType.FIST, WeaponType.PISTOL):
            if player.weaponowned[WeaponType.SHOTGUN]:
                player.pendingweapon = WeaponType.SHOTGUN
    elif ammo == AmmoType.CELL:
        if player.readyweapon in (WeaponType.FIST, WeaponType.PISTOL):
            if player.weaponowned[WeaponType.PLASMA]:
                player.pendingweapon = WeaponType.PLASMA
    elif ammo == AmmoType.MISL:
        if player.readyweapon == WeaponType.FIST:
            if player.weaponowned[WeaponType.MISSILE]:
                player.pendingweapon = WeaponType.MISSILE

    return True


# ------------------------------------------------------------------
# P_GiveWeapon
# ------------------------------------------------------------------
def P_GiveWeapon(player, weapon: int, dropped: bool) -> bool:
    import doomstat
    from p_mobj import S_StartSound
    import info as info_mod

    if (doomstat.netgame and doomstat.deathmatch != 2 and not dropped):
        if player.weaponowned[weapon]:
            return False
        player.bonuscount += BONUSADD
        player.weaponowned[weapon] = True
        ammo = _weapon_ammo[weapon]
        if doomstat.deathmatch:
            P_GiveAmmo(player, ammo, 5)
        else:
            P_GiveAmmo(player, ammo, 2)
        player.pendingweapon = weapon
        import doomstat as ds
        if player is ds.players[ds.consoleplayer]:
            S_StartSound(None, info_mod.sfx_wpnup)
        return False

    ammo = _weapon_ammo[weapon]
    if ammo != AmmoType.NOAMMO:
        gaveammo = P_GiveAmmo(player, ammo, 1 if dropped else 2)
    else:
        gaveammo = False

    if player.weaponowned[weapon]:
        gaveweapon = False
    else:
        gaveweapon = True
        player.weaponowned[weapon] = True
        player.pendingweapon = weapon

    return gaveweapon or gaveammo


# ------------------------------------------------------------------
# P_GiveBody
# ------------------------------------------------------------------
def P_GiveBody(player, num: int) -> bool:
    if player.health >= MAXHEALTH:
        return False
    player.health = min(player.health + num, MAXHEALTH)
    player.mo.health = player.health
    return True


# ------------------------------------------------------------------
# P_GiveArmor
# ------------------------------------------------------------------
def P_GiveArmor(player, armortype: int) -> bool:
    hits = armortype * 100
    if player.armorpoints >= hits:
        return False
    player.armortype   = armortype
    player.armorpoints = hits
    return True


# ------------------------------------------------------------------
# P_GiveCard
# ------------------------------------------------------------------
def P_GiveCard(player, card: int):
    if player.cards[card]:
        return
    player.bonuscount = BONUSADD
    player.cards[card] = True


# ------------------------------------------------------------------
# P_GivePower
# ------------------------------------------------------------------
def P_GivePower(player, power: int) -> bool:
    from p_mobj import MF_SHADOW

    if power == PowerType.INVULNERABILITY:
        player.powers[power] = INVULNTICS
        return True
    if power == PowerType.INVISIBILITY:
        player.powers[power] = INVISTICS
        player.mo.flags |= MF_SHADOW
        return True
    if power == PowerType.INFRARED:
        player.powers[power] = INFRATICS
        return True
    if power == PowerType.IRONFEET:
        player.powers[power] = IRONTICS
        return True
    if power == PowerType.STRENGTH:
        P_GiveBody(player, 100)
        player.powers[power] = 1
        return True
    if player.powers[power]:
        return False
    player.powers[power] = 1
    return True


# ------------------------------------------------------------------
# P_TouchSpecialThing  — item pickup dispatcher
# ------------------------------------------------------------------
def P_TouchSpecialThing(special, toucher):
    import doomstat, info as info_mod
    from p_mobj import S_StartSound
    from doomdef import GameVersion, GameMode

    delta = special.z - toucher.z
    if delta > toucher.height or delta < -8 * FRACUNIT:
        return   # out of reach

    if toucher.health <= 0:
        return

    player = toucher.player
    spr    = special.sprite
    sound  = info_mod.sfx_itemup

    # ---- Sprite-based dispatch ----
    sn = info_mod.sprnames

    def _spr(name): return sn.index(name) if name in sn else -1

    SPR = {n: i for i, n in enumerate(sn)}

    def is_spr(name): return spr == SPR.get(name, -9999)

    if is_spr('ARM1'):
        if not P_GiveArmor(player, deh_green_armor_class): return
        player.message = 'Picked up the armor.'
    elif is_spr('ARM2'):
        if not P_GiveArmor(player, deh_blue_armor_class): return
        player.message = 'You got the MegaArmor!'
    elif is_spr('BON1'):
        player.health = min(player.health + 1, deh_max_health)
        player.mo.health = player.health
        player.message = "Picked up a health bonus."
    elif is_spr('BON2'):
        player.armorpoints = min(player.armorpoints + 1, deh_max_armor)
        if not player.armortype:
            player.armortype = 1
        player.message = "Picked up an armor bonus."
    elif is_spr('SOUL'):
        player.health = min(player.health + deh_soulsphere_health, deh_max_soulsphere)
        player.mo.health = player.health
        player.message = "Supercharge!"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7:
            sound = info_mod.sfx_getpow
    elif is_spr('MEGA'):
        if doomstat.gamemode != GameMode.COMMERCIAL: return
        player.health = deh_megasphere_health
        player.mo.health = player.health
        P_GiveArmor(player, 2)
        player.message = "MegaSphere!"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7:
            sound = info_mod.sfx_getpow
    # Keys
    elif is_spr('BKEY'):
        if not player.cards[CardType.BLUECARD]: player.message = "Picked up a blue keycard."
        P_GiveCard(player, CardType.BLUECARD)
        if not doomstat.netgame: pass
        else: return
    elif is_spr('YKEY'):
        if not player.cards[CardType.YELLOWCARD]: player.message = "Picked up a yellow keycard."
        P_GiveCard(player, CardType.YELLOWCARD)
        if not doomstat.netgame: pass
        else: return
    elif is_spr('RKEY'):
        if not player.cards[CardType.REDCARD]: player.message = "Picked up a red keycard."
        P_GiveCard(player, CardType.REDCARD)
        if not doomstat.netgame: pass
        else: return
    elif is_spr('BSKU'):
        if not player.cards[CardType.BLUESKULL]: player.message = "Picked up a blue skull key."
        P_GiveCard(player, CardType.BLUESKULL)
        if not doomstat.netgame: pass
        else: return
    elif is_spr('YSKU'):
        if not player.cards[CardType.YELLOWSKULL]: player.message = "Picked up a yellow skull key."
        P_GiveCard(player, CardType.YELLOWSKULL)
        if not doomstat.netgame: pass
        else: return
    elif is_spr('RSKU'):
        if not player.cards[CardType.REDSKULL]: player.message = "Picked up a red skull key."
        P_GiveCard(player, CardType.REDSKULL)
        if not doomstat.netgame: pass
        else: return
    # Health
    elif is_spr('STIM'):
        if not P_GiveBody(player, 10): return
        player.message = "Picked up a stimpack."
    elif is_spr('MEDI'):
        if not P_GiveBody(player, 25): return
        player.message = "Picked up a medikit that you REALLY needed!" if player.health < 25 else "Picked up a medikit."
    # Power-ups
    elif is_spr('PINV'):
        if not P_GivePower(player, PowerType.INVULNERABILITY): return
        player.message = "Invulnerability!"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7: sound = info_mod.sfx_getpow
    elif is_spr('PSTR'):
        if not P_GivePower(player, PowerType.STRENGTH): return
        player.message = "Berserk!"
        if player.readyweapon != WeaponType.FIST: player.pendingweapon = WeaponType.FIST
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7: sound = info_mod.sfx_getpow
    elif is_spr('PINS'):
        if not P_GivePower(player, PowerType.INVISIBILITY): return
        player.message = "Partial Invisibility"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7: sound = info_mod.sfx_getpow
    elif is_spr('SUIT'):
        if not P_GivePower(player, PowerType.IRONFEET): return
        player.message = "Radiation Shielding Suit"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7: sound = info_mod.sfx_getpow
    elif is_spr('PMAP'):
        if not P_GivePower(player, PowerType.ALLMAP): return
        player.message = "Computer Area Map"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7: sound = info_mod.sfx_getpow
    elif is_spr('PVIS'):
        if not P_GivePower(player, PowerType.INFRARED): return
        player.message = "Light Amplification Visor"
        if doomstat.gameversion > GameVersion.EXE_DOOM_1_7: sound = info_mod.sfx_getpow
    # Ammo
    elif is_spr('CLIP'):
        if not P_GiveAmmo(player, AmmoType.CLIP, 0 if (special.flags & MF_DROPPED) else 1): return
        player.message = "Picked up a clip."
    elif is_spr('AMMO'):
        if not P_GiveAmmo(player, AmmoType.CLIP, 5): return
        player.message = "Picked up a box of bullets."
    elif is_spr('ROCK'):
        if not P_GiveAmmo(player, AmmoType.MISL, 1): return
        player.message = "Picked up a rocket."
    elif is_spr('BROK'):
        if not P_GiveAmmo(player, AmmoType.MISL, 5): return
        player.message = "Picked up a box of rockets."
    elif is_spr('CELL'):
        if not P_GiveAmmo(player, AmmoType.CELL, 1): return
        player.message = "Picked up an energy cell."
    elif is_spr('CELP'):
        if not P_GiveAmmo(player, AmmoType.CELL, 5): return
        player.message = "Picked up an energy cell pack."
    elif is_spr('SHEL'):
        if not P_GiveAmmo(player, AmmoType.SHELL, 1): return
        player.message = "Picked up 4 shotgun shells."
    elif is_spr('SBOX'):
        if not P_GiveAmmo(player, AmmoType.SHELL, 5): return
        player.message = "Picked up a box of shotgun shells."
    elif is_spr('BPAK'):
        if not player.backpack:
            for i in range(NUMAMMO):
                player.maxammo[i] *= 2
            player.backpack = True
        for i in range(NUMAMMO):
            P_GiveAmmo(player, i, 1)
        player.message = "Picked up a backpack full of ammo!"
    # Weapons
    elif is_spr('BFUG'):
        if not P_GiveWeapon(player, WeaponType.BFG, False): return
        player.message = "You got the BFG9000!  Oh, yes."
        sound = info_mod.sfx_wpnup
    elif is_spr('MGUN'):
        if not P_GiveWeapon(player, WeaponType.CHAINGUN, bool(special.flags & MF_DROPPED)): return
        player.message = "You got the chaingun!"
        sound = info_mod.sfx_wpnup
    elif is_spr('CSAW'):
        if not P_GiveWeapon(player, WeaponType.CHAINSAW, False): return
        player.message = "A chainsaw!  Find some meat!"
        sound = info_mod.sfx_wpnup
    elif is_spr('LAUN'):
        if not P_GiveWeapon(player, WeaponType.MISSILE, False): return
        player.message = "You got the rocket launcher!"
        sound = info_mod.sfx_wpnup
    elif is_spr('PLAS'):
        if not P_GiveWeapon(player, WeaponType.PLASMA, False): return
        player.message = "You got the plasma gun!"
        sound = info_mod.sfx_wpnup
    elif is_spr('SHOT'):
        if not P_GiveWeapon(player, WeaponType.SHOTGUN, bool(special.flags & MF_DROPPED)): return
        player.message = "You got the shotgun!"
        sound = info_mod.sfx_wpnup
    elif is_spr('SGN2'):
        if not P_GiveWeapon(player, WeaponType.SUPERSHOTGUN, bool(special.flags & MF_DROPPED)): return
        player.message = "You got the super shotgun!"
        sound = info_mod.sfx_wpnup
    else:
        return  # unknown item — ignore

    if special.flags & MF_COUNTITEM:
        player.itemcount += 1
    P_RemoveMobj(special)
    player.bonuscount += BONUSADD
    if player is doomstat.players[doomstat.consoleplayer]:
        S_StartSound(None, sound)


# ------------------------------------------------------------------
# P_KillMobj
# ------------------------------------------------------------------
def P_KillMobj(source, target):
    import doomstat, info as info_mod
    from m_random import P_Random
    from doomdef import GameVersion, PowerType, WeaponType

    target.flags &= ~(MF_SHOOTABLE | MF_FLOAT | MF_SKULLFLY)
    if target.type != info_mod.MT_SKULL:
        target.flags &= ~MF_NOGRAVITY
    target.flags |= MF_CORPSE | MF_DROPOFF
    target.height >>= 2

    # Kill credit
    if source and source.player:
        if target.flags & MF_COUNTKILL:
            source.player.killcount += 1
        if target.player:
            idx = doomstat.players.index(target.player)
            src_idx = doomstat.players.index(source.player)
            source.player.frags[idx] += 1
    elif not doomstat.netgame and (target.flags & MF_COUNTKILL):
        doomstat.players[0].killcount += 1

    if target.player:
        if not source:
            idx = doomstat.players.index(target.player)
            target.player.frags[idx] += 1
        target.flags &= ~MF_SOLID
        from d_player import PlayerState
        target.player.playerstate = PlayerState.DEAD
        _drop_weapon(target.player)

        if (target.player is doomstat.players[doomstat.consoleplayer] and
                doomstat.automapactive):
            doomstat.automapactive = False

    # Death state
    if (target.health < -target.info.spawnhealth and
            target.info.xdeathstate):
        P_SetMobjState(target, target.info.xdeathstate)
    else:
        P_SetMobjState(target, target.info.deathstate)

    target.tics -= P_Random() & 3
    if target.tics < 1:
        target.tics = 1

    if doomstat.gameversion == GameVersion.EXE_CHEX:
        return  # Chex Quest — no drops

    # Drop item
    _item_drop = {
        info_mod.MT_WOLFSS:   info_mod.MT_CLIP,
        info_mod.MT_POSSESSED: info_mod.MT_CLIP,
        info_mod.MT_SHOTGUY:  info_mod.MT_SHOTGUN,
        info_mod.MT_CHAINGUY: info_mod.MT_CHAINGUN,
    }
    item = _item_drop.get(target.type)
    if item is not None:
        mo = P_SpawnMobj(target.x, target.y, ONFLOORZ, item)
        mo.flags |= MF_DROPPED


def _drop_weapon(player):
    """P_DropWeapon — lower weapon on player death."""
    try:
        import p_pspr
        p_pspr.P_DropWeapon(player)
    except (ImportError, AttributeError):
        pass


# ------------------------------------------------------------------
# P_DamageMobj
# ------------------------------------------------------------------
def P_DamageMobj(target, inflictor, source, damage: int):
    import doomstat
    from m_random import P_Random
    from doomdef import Skill, PowerType, CheatFlags
    from tables import ANGLETOFINESHIFT, finecosine, finesine
    from r_main import R_PointToAngle2
    import info as info_mod

    if not (target.flags & MF_SHOOTABLE):
        return
    if target.health <= 0:
        return
    if target.flags & MF_SKULLFLY:
        target.momx = target.momy = target.momz = 0

    player = target.player

    if player and doomstat.gameskill == Skill.BABY:
        damage >>= 1

    # Thrust
    if inflictor and not (target.flags & MF_NOCLIP):
        if not (source and source.player and
                source.player.readyweapon == WeaponType.CHAINSAW):
            ang = R_PointToAngle2(inflictor.x, inflictor.y, target.x, target.y)
            thrust = damage * (FRACUNIT >> 3) * 100 // target.info.mass

            if (damage < 40 and damage > target.health and
                    target.z - inflictor.z > 64 * FRACUNIT and
                    (P_Random() & 1)):
                ang = (ang + ANG180) & 0xFFFFFFFF
                thrust *= 4

            fine = (ang >> ANGLETOFINESHIFT) & 0x1FFF
            target.momx += fixed_mul(thrust, finecosine[fine])
            target.momy += fixed_mul(thrust, finesine[fine])

    # Player-specific
    if player:
        if target.subsector.sector.special == 11 and damage >= target.health:
            damage = target.health - 1
        if (damage < 1000 and
                ((player.cheats & CheatFlags.GODMODE) or
                 player.powers[PowerType.INVULNERABILITY])):
            return

        if player.armortype:
            saved = damage // 3 if player.armortype == 1 else damage // 2
            if player.armorpoints <= saved:
                saved = player.armorpoints
                player.armortype = 0
            player.armorpoints -= saved
            damage -= saved

        player.health = max(0, player.health - damage)
        player.attacker    = source
        player.damagecount = min(player.damagecount + damage, 100)

    target.health -= damage
    if target.health <= 0:
        P_KillMobj(source, target)
        return

    if (P_Random() < target.info.painchance and
            not (target.flags & MF_SKULLFLY)):
        target.flags |= MF_JUSTHIT
        P_SetMobjState(target, target.info.painstate)

    target.reactiontime = 0

    if (not target.threshold or target.type == info_mod.MT_VILE):
        if (source and source is not target and
                source.type != info_mod.MT_VILE):
            target.target    = source
            target.threshold = BASETHRESHOLD
            if (target.state is info_mod.states[target.info.spawnstate] and
                    target.info.seestate != info_mod.S_NULL):
                P_SetMobjState(target, target.info.seestate)


# Patch p_map.P_TouchSpecialThing
try:
    import p_map
    p_map.P_TouchSpecialThing = P_TouchSpecialThing
except ImportError:
    pass

# Patch p_mobj stubs
import p_mobj as _pm
_pm.P_DamageMobj = P_DamageMobj

# Also expose deh values used by g_game
from p_inter import deh_initial_health, deh_initial_bullets, maxammo as _maxammo
