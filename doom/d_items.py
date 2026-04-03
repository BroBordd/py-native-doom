# AUTO-GENERATED from d_items.c / d_items.h
from doomdef import am_noammo, am_clip, am_shell, am_misl, am_cell
from info import (S_PUNCHUP, S_PUNCHDOWN, S_PUNCH, S_PUNCH1, S_NULL,
                  S_PISTOLUP, S_PISTOLDOWN, S_PISTOL, S_PISTOL1, S_PISTOLFLASH,
                  S_SGUNUP, S_SGUNDOWN, S_SGUN, S_SGUN1, S_SGUNFLASH1,
                  S_CHAINUP, S_CHAINDOWN, S_CHAIN, S_CHAIN1, S_CHAINFLASH1,
                  S_MISSILEUP, S_MISSILEDOWN, S_MISSILE, S_MISSILE1, S_MISSILEFLASH1,
                  S_PLASMAUP, S_PLASMADOWN, S_PLASMA, S_PLASMA1, S_PLASMAFLASH1,
                  S_BFGUP, S_BFGDOWN, S_BFG, S_BFG1, S_BFGFLASH1,
                  S_SAWUP, S_SAWDOWN, S_SAW, S_SAW1,
                  S_DSGUNUP, S_DSGUNDOWN, S_DSGUN, S_DSGUN1, S_DSGUNFLASH1)

# weaponinfo_t: (ammo, upstate, downstate, readystate, atkstate, flashstate)
weaponinfo = [
    (am_noammo, S_PUNCHUP,   S_PUNCHDOWN,   S_PUNCH,   S_PUNCH1,   S_NULL),        # fist
    (am_clip,   S_PISTOLUP,  S_PISTOLDOWN,  S_PISTOL,  S_PISTOL1,  S_PISTOLFLASH), # pistol
    (am_shell,  S_SGUNUP,    S_SGUNDOWN,    S_SGUN,    S_SGUN1,    S_SGUNFLASH1),  # shotgun
    (am_clip,   S_CHAINUP,   S_CHAINDOWN,   S_CHAIN,   S_CHAIN1,   S_CHAINFLASH1), # chaingun
    (am_misl,   S_MISSILEUP, S_MISSILEDOWN, S_MISSILE, S_MISSILE1, S_MISSILEFLASH1),# rocket
    (am_cell,   S_PLASMAUP,  S_PLASMADOWN,  S_PLASMA,  S_PLASMA1,  S_PLASMAFLASH1),# plasma
    (am_cell,   S_BFGUP,     S_BFGDOWN,     S_BFG,     S_BFG1,     S_BFGFLASH1),  # bfg
    (am_noammo, S_SAWUP,     S_SAWDOWN,     S_SAW,     S_SAW1,     S_NULL),        # chainsaw
    (am_shell,  S_DSGUNUP,   S_DSGUNDOWN,   S_DSGUN,   S_DSGUN1,   S_DSGUNFLASH1), # super sg
]

NUMWEAPONS = len(weaponinfo)
