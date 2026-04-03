import p_ceilng
import p_floor
import p_tick
import p_spec
# p_local.py
# Translated DOOM play functions, animation, global header

import doomdef

# ==============================================================================
# PHYSICS & GAMEPLAY CONSTANTS
# ==============================================================================

FLOATSPEED      = (doomdef.FRACUNIT * 4)

MAXHEALTH       = 100
VIEWHEIGHT      = (41 * doomdef.FRACUNIT)

# Mapblocks are used to check movement against lines and things
MAPBLOCKUNITS   = 128
MAPBLOCKSIZE    = (MAPBLOCKUNITS * doomdef.FRACUNIT)
MAPBLOCKSHIFT   = (doomdef.FRACBITS + 7)
MAPBMASK        = (MAPBLOCKSIZE - 1)
MAPBTOFRAC      = (MAPBLOCKSHIFT - doomdef.FRACBITS)

# Player radius for movement checking
PLAYERRADIUS    = (16 * doomdef.FRACUNIT)

# MAXRADIUS is for precalculated sector block boxes
MAXRADIUS       = (32 * doomdef.FRACUNIT)

GRAVITY         = doomdef.FRACUNIT
MAXMOVE         = (30 * doomdef.FRACUNIT)

USERANGE        = (64 * doomdef.FRACUNIT)
MELEERANGE      = (64 * doomdef.FRACUNIT)
MISSILERANGE    = (32 * 64 * doomdef.FRACUNIT)

# Follow a player exclusively for 3 seconds
BASETHRESHOLD   = 100

ONFLOORZ        = -2147483648  # INT_MIN equivalent
ONCEILINGZ      =  2147483647  # INT_MAX equivalent

# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

class mapthing_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.angle = 0
        self.type = 0
        self.options = 0

class divline_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0

class intercept_t:
    def __init__(self):
        self.frac = 0
        self.isaline = False
        self.d = None  # Will hold either a mobj_t or line_t instance

class thinker_t:
    def __init__(self):
        self.prev = None
        self.next = None
        self.function = None

# ==============================================================================
# GLOBAL STATE & VARIABLES
# ==============================================================================

# Thinker list head/tail (doubly linked list)
thinkercap = thinker_t()
thinkercap.prev = thinkercap
thinkercap.next = thinkercap

# Item respawn queue
ITEMQUESIZE = 128
itemrespawnque = [mapthing_t() for _ in range(ITEMQUESIZE)]
itemrespawntime = [0] * ITEMQUESIZE
iquehead = 0
iquetail = 0

# Intercepts (Line of sight / hitscan logic)
MAXINTERCEPTS_ORIGINAL = 128
MAXINTERCEPTS = (MAXINTERCEPTS_ORIGINAL + 61)
intercepts = [intercept_t() for _ in range(MAXINTERCEPTS)]
intercept_p = 0  # Points to the current intercept index

PT_ADDLINES  = 1
PT_ADDTHINGS = 2
PT_EARLYOUT  = 4

opentop = 0
openbottom = 0
openrange = 0
lowfloor = 0

trace = divline_t()

floatok = False
tmfloorz = 0
tmceilingz = 0

ceilingline = None

MAXSPECIALCROSS = 20
spechit = [None] * MAXSPECIALCROSS
numspechit = 0

linetarget = None   # who got hit (or None)
attackrange = 0
topslope = 0
bottomslope = 0

# P_SETUP Blockmap / Reject / Maps Data
rejectmatrix = None
blockmaplump = None
blockmap = []
bmapwidth = 0
bmapheight = 0
bmaporgx = 0
bmaporgy = 0
blocklinks = []

# Map Structural Elements (Populated by p_setup, read by p_saveg, r_bsp)
vertexes = []
segs = []
sectors = []
subsectors = []
nodes = []
lines = []
sides = []

# P_INTER Ammo Base Constants
# Indexes: 0 = Clip, 1 = Shell, 2 = Cell, 3 = Missile
maxammo = [200, 50, 300, 50]
clipammo = [10, 4, 20, 1]

# ==============================================================================
# P_SPEC ACTIVE SPECIALS TRACKING
# (Used by physics to tick elevators, doors, ceilings and save states)
# ==============================================================================

MAXCEILINGS = 30
MAXPLATS    = 30

activeceilings = [None] * MAXCEILINGS
activeplats    = [None] * MAXPLATS

def P_AddActiveCeiling(c):
    for i in range(MAXCEILINGS):
        if activeceilings[i] is None:
            activeceilings[i] = c
            return

def P_RemoveActiveCeiling(c):
    for i in range(MAXCEILINGS):
        if activeceilings[i] == c:
            activeceilings[i] = None
            break

def P_AddActivePlat(p):
    for i in range(MAXPLATS):
        if activeplats[i] is None:
            activeplats[i] = p
            return

def P_RemoveActivePlat(p):
    for i in range(MAXPLATS):
        if activeplats[i] == p:
            activeplats[i] = None
            break
