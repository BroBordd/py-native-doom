# r_state.py
# Ported from r_state.h
# Acts as the global state container for the renderer (replacing C's externs).

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
FINEANGLES = 8192
SCREENWIDTH = 320

# -----------------------------------------------------------------------------
# REFRESH / RENDERING DATA STRUCTURES
# -----------------------------------------------------------------------------

# needed for texture pegging
textureheight = []

# needed for pre rendering (fracs)
spritewidth = []
spriteoffset = []
spritetopoffset = []

colormaps = None

viewwidth = 0
scaledviewwidth = 0
viewheight = 0

firstflat = 0

# for global animation
flattranslation = []
texturetranslation = []

# Sprite....
firstspritelump = 0
lastspritelump = 0
numspritelumps = 0

# -----------------------------------------------------------------------------
# MAP DATA LOOKUP TABLES
# -----------------------------------------------------------------------------

numsprites = 0
sprites = []

numvertexes = 0
vertexes = []

numsegs = 0
segs = []

numsectors = 0
sectors = []

numsubsectors = 0
subsectors = []

numnodes = 0
nodes = []

numlines = 0
lines = []

numsides = 0
sides = []

# -----------------------------------------------------------------------------
# POV (Point of View) DATA
# -----------------------------------------------------------------------------

viewx = 0
viewy = 0
viewz = 0

viewangle = 0
viewplayer = None

# -----------------------------------------------------------------------------
# RENDERER MATH / STATE
# -----------------------------------------------------------------------------

clipangle = 0

# Pre-allocated arrays just like the C array declarations
viewangletox = [0] * (FINEANGLES // 2)
xtoviewangle = [0] * (SCREENWIDTH + 1)

rw_distance = 0
rw_normalangle = 0

# angle to line origin
rw_angle1 = 0

# Segs count
sscount = 0

# visplanes
floorplane = None
ceilingplane = None
