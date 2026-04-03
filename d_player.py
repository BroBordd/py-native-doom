# d_player.py
# Player data structure and intermission structs
# Ported from d_player.h

from doomdef import (
    MAXPLAYERS, NUMPOWERS, NUMCARDS, NUMWEAPONS, NUMAMMO,
    NUMPSPRITES, WeaponType, Skill,
)


# -----------------------------------------------
# Player state
# -----------------------------------------------
class PlayerState:
    LIVE   = 0   # PST_LIVE
    DEAD   = 1   # PST_DEAD
    REBORN = 2   # PST_REBORN


# -----------------------------------------------
# Cheat flags
# -----------------------------------------------
class CheatFlags:
    NOCLIP    = 1   # CF_NOCLIP
    GODMODE   = 2   # CF_GODMODE
    NOMOMENTUM = 4  # CF_NOMOMENTUM


# -----------------------------------------------
# pspdef_t  (weapon sprite overlay)
# Mirrors p_pspr.h  pspdef_t
# -----------------------------------------------
class PSpriteDef:
    """
    Weapon/flash overlay sprite state.
    state  : pointer into the states table (int index or None)
    tics   : tics remaining in current state
    sx, sy : sprite screen-space offsets (fixed_t)
    """
    __slots__ = ('state', 'tics', 'sx', 'sy')

    def __init__(self):
        self.state = None   # statenum index
        self.tics  = 0
        self.sx    = 0      # fixed_t
        self.sy    = 0      # fixed_t


# Sprite overlay indices
PSP_WEAPON = 0
PSP_FLASH  = 1


# -----------------------------------------------
# ticcmd_t  (input command for one game tic)
# Mirrors d_ticcmd.h
# -----------------------------------------------
class TicCmd:
    __slots__ = (
        'forwardmove',   # signed byte: -50..50
        'sidemove',      # signed byte
        'angleturn',     # short: <<16 to get angle delta
        'consistancy',   # for netgame sync checking
        'chatchar',      # outgoing chat character
        'buttons',       # BT_* flags
    )

    # Button flags
    BT_ATTACK    = 1
    BT_USE       = 2
    BT_CHANGE    = 4     # weapon change
    BT_WEAPONMASK = (8 | 16 | 32)  # 3-bit weapon index
    BT_WEAPONSHIFT = 3
    BT_SPECIAL   = 128
    BTS_PAUSE    = 1
    BTS_SAVEGAME = 2
    BTS_LOADGAME = 4
    BTS_QUICKSAVE  = 8
    BTS_QUICKLOAD  = 16
    BTS_SAVEGAMESLOT_MASK = (32 | 64 | 128)
    BTS_SAVEGAMESLOT_SHIFT = 5

    def __init__(self):
        self.forwardmove = 0
        self.sidemove    = 0
        self.angleturn   = 0
        self.consistancy = 0
        self.chatchar    = 0
        self.buttons     = 0

    def clear(self):
        self.forwardmove = 0
        self.sidemove    = 0
        self.angleturn   = 0
        self.consistancy = 0
        self.chatchar    = 0
        self.buttons     = 0


# -----------------------------------------------
# player_t
# -----------------------------------------------
class Player:
    """
    Full player object.  'mo' will be set to an Mobj instance once
    p_mobj.py is in place.
    """

    def __init__(self):
        self.mo          = None           # mobj_t* → Mobj instance
        self.playerstate = PlayerState.LIVE
        self.cmd         = TicCmd()

        # View height / bobbing  (fixed_t)
        self.viewz           = 0
        self.viewheight      = 0
        self.deltaviewheight = 0
        self.bob             = 0

        # Health / armour (between-level values; mo.health used in-level)
        self.health      = 100
        self.armorpoints = 0
        self.armortype   = 0   # 0=none, 1=green, 2=blue

        # Power-ups: tic counters (0 = not active)
        self.powers = [0] * NUMPOWERS
        self.cards  = [False] * NUMCARDS
        self.backpack = False

        # Frags (deathmatch)
        self.frags = [0] * MAXPLAYERS

        # Weapons
        self.readyweapon   = WeaponType.PISTOL
        self.pendingweapon = WeaponType.NOCHANGE
        self.weaponowned   = [False] * NUMWEAPONS
        self.ammo          = [0]    * NUMAMMO
        self.maxammo       = [0]    * NUMAMMO

        # Input state
        self.attackdown = 0
        self.usedown    = 0

        # Cheats
        self.cheats = 0

        # Accuracy degradation on auto-fire
        self.refire = 0

        # Intermission counters
        self.killcount   = 0
        self.itemcount   = 0
        self.secretcount = 0

        # HUD message
        self.message = None   # str or None

        # Screen flash counters
        self.damagecount = 0
        self.bonuscount  = 0

        # Last attacker mobj (or None for env damage)
        self.attacker = None

        # Lighting
        self.extralight    = 0
        self.fixedcolormap = 0
        self.colormap      = 0

        # Weapon overlay sprites
        self.psprites = [PSpriteDef() for _ in range(NUMPSPRITES)]

        # Secret level visited
        self.didsecret = False

    def is_alive(self) -> bool:
        return self.playerstate == PlayerState.LIVE

    def has_key(self, card: int) -> bool:
        return self.cards[card]

    def give_key(self, card: int):
        self.cards[card] = True

    def has_weapon(self, weapon: int) -> bool:
        return bool(self.weaponowned[weapon])

    def give_weapon(self, weapon: int):
        self.weaponowned[weapon] = True

    def has_power(self, power: int) -> bool:
        return self.powers[power] > 0


# -----------------------------------------------
# wbplayerstruct_t  (intermission per-player data)
# -----------------------------------------------
class WbPlayerStruct:
    __slots__ = ('in_game', 'skills', 'sitems', 'ssecret',
                 'stime', 'frags', 'score')

    def __init__(self):
        self.in_game  = False
        self.skills   = 0
        self.sitems   = 0
        self.ssecret  = 0
        self.stime    = 0
        self.frags    = [0] * 4
        self.score    = 0


# -----------------------------------------------
# wbstartstruct_t  (intermission start params)
# -----------------------------------------------
class WbStartStruct:
    __slots__ = ('epsd', 'didsecret', 'last', 'next',
                 'maxkills', 'maxitems', 'maxsecret', 'maxfrags',
                 'partime', 'pnum', 'plyr')

    def __init__(self):
        self.epsd      = 0
        self.didsecret = False
        self.last      = 0
        self.next      = 0
        self.maxkills  = 0
        self.maxitems  = 0
        self.maxsecret = 0
        self.maxfrags  = 0
        self.partime   = 0
        self.pnum      = 0
        self.plyr      = [WbPlayerStruct() for _ in range(MAXPLAYERS)]


class player_t:
    def __init__(self):
        self.playerstate = None
        self.mo = None
