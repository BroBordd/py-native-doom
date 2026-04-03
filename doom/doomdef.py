# doomdef.py
# Core constants, types, and fixed-point math
# Ported from doomdef.h / doomtype.h

from d_event import (
    ev_keydown,
    ev_keyup,
    ev_mouse,
    ev_joystick,
    ev_quit
)

# -----------------------------------------------------------------------------
# skill_t - Difficulty levels
# -----------------------------------------------------------------------------
sk_baby      = 0  # I'm too young to die.
sk_easy      = 1  # Hey, not too rough.
sk_medium    = 2  # Hurt me plenty.
sk_hard      = 3  # Ultra-Violence.
sk_nightmare = 4  # Nightmare!

# -----------------------------------------------
# Fixed-point math: 16.16
# -----------------------------------------------
FRACBITS = 16
FRACUNIT = 1 << FRACBITS

def fixed_mul(a: int, b: int) -> int:
    return (a * b) >> FRACBITS

def fixed_div(a: int, b: int) -> int:
    if (abs(a) >> 14) >= abs(b):
        return 0x7FFFFFFF if (a ^ b) >= 0 else -0x7FFFFFFF  # overflow guard
    return (a << FRACBITS) // b

def fixed_to_float(f: int) -> float:
    return f / FRACUNIT

def float_to_fixed(f: float) -> int:
    return int(f * FRACUNIT)

# -----------------------------------------------
# Angles: 0x00000000 - 0xFFFFFFFF = full circle
# -----------------------------------------------
ANG45  = 0x20000000
ANG90  = 0x40000000
ANG180 = 0x80000000
ANG270 = 0xC0000000
ANGLE_MAX = 0xFFFFFFFF

# Degrees to binary angle
def angle_to_fine(angle: int) -> int:
    """Convert BAM angle to fine angle table index (0-8191)."""
    return (angle >> 19) & 0x1FFF

# -----------------------------------------------
# Screen geometry
# -----------------------------------------------
SCREENWIDTH  = 320
SCREENHEIGHT = 200
SCREEN_MUL   = 1        # scale factor; your hook can override rendering scale

# -----------------------------------------------
# Game limits (from doomdef.h)
# -----------------------------------------------
MAXPLAYERS   = 4
TICRATE      = 35       # game tics per second

MAXRADIUS    = 32 * FRACUNIT

# Map geometry limits (vanilla)
MAXLINES     = 32768    # not enforced, Python lists are dynamic
MAXSIDES     = 65536
MAXVERTEXES  = 65536

# -----------------------------------------------
# Game mode / mission enums  (from d_mode.h)
# -----------------------------------------------
class GameMode:
    SHAREWARE    = 0   # DOOM 1 shareware, E1, M9
    REGISTERED   = 1   # DOOM 1 registered
    COMMERCIAL   = 2   # DOOM 2, no episodes
    RETAIL       = 3   # DOOM 1 Ultimate / The Plutonia Experiment
    INDETERMINED = 4   # fallback

class GameMission:
    DOOM    = 0
    DOOM2   = 1
    PACK_TNT    = 2
    PACK_PLUTONIA = 3
    PACK_CHEX   = 4
    PACK_HACX   = 5

class GameVersion:
    exe_doom_1_2 = 0
    exe_doom_1_5 = 1
    exe_doom_1_666 = 2
    exe_doom_1_7 = 3
    exe_doom_1_8 = 4
    exe_doom_1_9 = 5
    exe_hacx = 6
    exe_ultimate = 7
    exe_final = 8
    exe_final2 = 9
    exe_chex = 10
    EXE_DOOM_1_2 = 0
    EXE_DOOM_1_5 = 1
    EXE_DOOM_1_666 = 2
    EXE_DOOM_1_7 = 3
    EXE_DOOM_1_8 = 4
    EXE_DOOM_1_9 = 5
    EXE_HACX = 6
    EXE_ULTIMATE = 7
    EXE_FINAL = 8
    EXE_FINAL2 = 9
    EXE_CHEX = 10
    EXE_DOO_1_7 = 3

class GameVariant:
    VANILLA  = 0
    FREEDOOM = 1
    FREEDM   = 2
    BFGEDITION = 3

# -----------------------------------------------
# Skill level
# -----------------------------------------------
class Skill:
    BABY    = 0
    EASY    = 1
    MEDIUM  = 2
    HARD    = 3
    NIGHTMARE = 4

# -----------------------------------------------
# Game state
# -----------------------------------------------
from enum import IntEnum
class GameState(IntEnum):
    LEVEL       = 0
    INTERMISSION = 1
    FINALE      = 2
    DEMOSCREEN  = 3

# -----------------------------------------------
# Key / card types  (from d_items.h)
# -----------------------------------------------
class CardType:
    BLUECARD    = 0
    YELLOWCARD  = 1
    REDCARD     = 2
    BLUESKULL   = 3
    YELLOWSKULL = 4
    REDSKULL    = 5
    NUMCARDS    = 6

NUMCARDS = CardType.NUMCARDS

# -----------------------------------------------
# Weapons  (from d_items.h)
# -----------------------------------------------
class WeaponType:
    FIST        = 0
    PISTOL      = 1
    SHOTGUN     = 2
    CHAINGUN    = 3
    MISSILE     = 4   # rocket launcher
    PLASMA      = 5
    BFG         = 6
    CHAINSAW    = 7
    SUPERSHOTGUN = 8
    NUMWEAPONS  = 9
    NOCHANGE    = 10  # wp_nochange sentinel

NUMWEAPONS = WeaponType.NUMWEAPONS

# -----------------------------------------------
# Ammo types  (from d_items.h)
# -----------------------------------------------
class AmmoType:
    CLIP    = 0
    SHELL   = 1
    CELL    = 2
    MISL    = 3
    NUMAMMO = 4
    NOAMMO  = 5   # fist / chainsaw

NUMAMMO = AmmoType.NUMAMMO

# -----------------------------------------------
# Power-up types  (from d_items.h)
# -----------------------------------------------
class PowerType:
    INVULNERABILITY = 0
    STRENGTH        = 1
    INVISIBILITY    = 2
    IRONFEET        = 3   # radiation suit
    ALLMAP          = 4
    INFRARED        = 5
    NUMPOWERS       = 6

NUMPOWERS = PowerType.NUMPOWERS

# -----------------------------------------------
# Sprite names sentinel / NUMPSPRITES
# -----------------------------------------------
NUMPSPRITES = 2   # PSP_WEAPON, PSP_FLASH

# -----------------------------------------------
# LineDef flags  (from doomdata.h)
# -----------------------------------------------
ML_BLOCKING     = 1
ML_BLOCKMONSTERS = 2
ML_TWOSIDED     = 4
ML_DONTPEGTOP   = 8
ML_DONTPEGBOTTOM = 16
ML_SECRET       = 32
ML_SOUNDBLOCK   = 64
ML_DONTDRAW     = 128
ML_MAPPED       = 256

# -----------------------------------------------
# Map lump indices  (from doomdata.h)
# -----------------------------------------------
ML_LABEL    = 0
ML_THINGS   = 1
ML_LINEDEFS = 2
ML_SIDEDEFS = 3
ML_VERTEXES = 4
ML_SEGS     = 5
ML_SSECTORS = 6
ML_NODES    = 7
ML_SECTORS  = 8
ML_REJECT   = 9
ML_BLOCKMAP = 10

# BSP leaf flag
NF_SUBSECTOR = 0x8000

# -----------------------------------------------
# Misc numeric limits
# -----------------------------------------------
MAXSHORT = 0x7FFF
MINSHORT = -0x8000
MAXINT   = 0x7FFFFFFF
MININT   = -0x80000000

# --- Map Spec / Movement Constants (originally from p_spec.h) ---

CEILSPEED   = FRACUNIT
CEILWAIT    = 150

VDOORSPEED  = FRACUNIT * 2
VDOORWAIT   = 150

FLOORSPEED  = FRACUNIT

PLATWAIT    = 3
PLATSPEED   = FRACUNIT

MAXCEILINGS = 30
MAXPLATS    = 30
PACKAGE_STRING = "Python Doom Port"
PROGRAM_PREFIX = "chocolate-"

PST_LIVE = 0
PST_DEAD = 1
PST_REBORN = 2

PU_CACHE = 101
