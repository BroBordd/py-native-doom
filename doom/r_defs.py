# r_defs.py
# Runtime map geometry + renderer data structures
# Ported from r_defs.h
#
# These are the *live* objects built from WAD data by p_setup.py.
# They hold Python object references instead of C pointers.

from doomdef import SCREENWIDTH, FRACUNIT, NF_SUBSECTOR

# ------------------------------------------------------------------
# Silhouette flags (for seg/sprite clipping)
# ------------------------------------------------------------------
SIL_NONE   = 0
SIL_BOTTOM = 1
SIL_TOP    = 2
SIL_BOTH   = 3

MAXDRAWSEGS = 256

# Bounding-box corner indices  (matches m_bbox.h)
BOXTOP    = 0
BOXBOTTOM = 1
BOXLEFT   = 2
BOXRIGHT  = 3


# ------------------------------------------------------------------
# vertex_t  — runtime vertex (fixed-point coords)
# ------------------------------------------------------------------
class Vertex:
    __slots__ = ('x', 'y')

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x   # fixed_t
        self.y = y   # fixed_t

    def __repr__(self):
        return f'Vertex({self.x/FRACUNIT:.1f}, {self.y/FRACUNIT:.1f})'


# ------------------------------------------------------------------
# degenmobj_t  — dummy mobj used as sound origin for sectors
# ------------------------------------------------------------------
class DegenMobj:
    __slots__ = ('x', 'y', 'z')

    def __init__(self):
        self.x = 0   # fixed_t
        self.y = 0
        self.z = 0


# ------------------------------------------------------------------
# sector_t
# ------------------------------------------------------------------
class Sector:
    __slots__ = (
        'floorheight', 'ceilingheight',
        'floorpic', 'ceilingpic',          # flat indices (int)
        'lightlevel', 'special', 'tag',
        'soundtraversed',
        'soundtarget',                      # Mobj or None
        'blockbox',                         # [top,bot,left,right] blockmap coords
        'soundorg',                         # DegenMobj
        'validcount',
        'thinglist',                        # first Mobj in sector, or None
        'specialdata',                      # active thinker (door/floor/etc) or None
        'linecount',
        'lines',                            # list of Line
    )

    def __init__(self):
        self.floorheight   = 0
        self.ceilingheight = 0
        self.floorpic      = 0
        self.ceilingpic    = 0
        self.lightlevel    = 160
        self.special       = 0
        self.tag           = 0
        self.soundtraversed = 0
        self.soundtarget   = None
        self.blockbox      = [0, 0, 0, 0]
        self.soundorg      = DegenMobj()
        self.validcount    = 0
        self.thinglist     = None
        self.specialdata   = None
        self.linecount     = 0
        self.lines         = []


# ------------------------------------------------------------------
# Slope types for line_t
# ------------------------------------------------------------------
class SlopeType:
    HORIZONTAL = 0
    VERTICAL   = 1
    POSITIVE   = 2
    NEGATIVE   = 3


# ------------------------------------------------------------------
# side_t
# ------------------------------------------------------------------
class Side:
    __slots__ = (
        'textureoffset',   # fixed_t
        'rowoffset',       # fixed_t
        'toptexture',      # texture index (int)
        'bottomtexture',
        'midtexture',
        'sector',          # Sector
    )

    def __init__(self):
        self.textureoffset = 0
        self.rowoffset     = 0
        self.toptexture    = 0
        self.bottomtexture = 0
        self.midtexture    = 0
        self.sector        = None


# ------------------------------------------------------------------
# line_t
# ------------------------------------------------------------------
class Line:
    __slots__ = (
        'v1', 'v2',          # Vertex
        'dx', 'dy',          # fixed_t  (v2 - v1)
        'flags', 'special', 'tag',
        'sidenum',           # (s0_idx, s1_idx)  — -1 = absent
        'bbox',              # [top, bot, left, right]  fixed_t
        'slopetype',         # SlopeType.*
        'frontsector',       # Sector or None
        'backsector',        # Sector or None
        'validcount',
        'specialdata',       # active thinker or None
    )

    def __init__(self):
        self.v1          = None
        self.v2          = None
        self.dx          = 0
        self.dy          = 0
        self.flags       = 0
        self.special     = 0
        self.tag         = 0
        self.sidenum     = (-1, -1)
        self.bbox        = [0, 0, 0, 0]
        self.slopetype   = SlopeType.HORIZONTAL
        self.frontsector = None
        self.backsector  = None
        self.validcount  = 0
        self.specialdata = None


# ------------------------------------------------------------------
# subsector_t
# ------------------------------------------------------------------
class Subsector:
    __slots__ = ('sector', 'numlines', 'firstline')

    def __init__(self):
        self.sector    = None   # Sector
        self.numlines  = 0
        self.firstline = 0


# ------------------------------------------------------------------
# seg_t
# ------------------------------------------------------------------
class Seg:
    __slots__ = (
        'v1', 'v2',          # Vertex
        'offset',            # fixed_t  (distance along linedef)
        'angle',             # angle_t  (BAM)
        'sidedef',           # Side
        'linedef',           # Line
        'frontsector',       # Sector
        'backsector',        # Sector or None
    )

    def __init__(self):
        self.v1          = None
        self.v2          = None
        self.offset      = 0
        self.angle       = 0
        self.sidedef     = None
        self.linedef     = None
        self.frontsector = None
        self.backsector  = None


# ------------------------------------------------------------------
# node_t  — BSP node (runtime, fixed-point coords)
# ------------------------------------------------------------------
class Node:
    __slots__ = ('x', 'y', 'dx', 'dy', 'bbox', 'children')

    def __init__(self):
        self.x        = 0    # fixed_t partition line origin
        self.y        = 0
        self.dx       = 0    # partition direction
        self.dy       = 0
        # bbox[side][corner]:  side 0=right, 1=left;  corner = BOX* consts
        self.bbox     = [[0, 0, 0, 0], [0, 0, 0, 0]]
        # children[side]: unsigned short; high bit set → subsector index
        self.children = [0, 0]

    def is_subsector(self, side: int) -> bool:
        return bool(self.children[side] & NF_SUBSECTOR)

    def child_index(self, side: int) -> int:
        return self.children[side] & ~NF_SUBSECTOR


# ------------------------------------------------------------------
# drawseg_t  — one clipped wall segment during rendering
# ------------------------------------------------------------------
class DrawSeg:
    __slots__ = (
        'curline',            # Seg
        'x1', 'x2',          # screen columns
        'scale1', 'scale2', 'scalestep',   # fixed_t
        'silhouette',         # SIL_* flags
        'bsilheight',         # fixed_t  — bottom sil height
        'tsilheight',         # fixed_t  — top sil height
        # clip arrays: Python lists indexed by screen column
        'sprtopclip',         # list[int] or None
        'sprbottomclip',      # list[int] or None
        'maskedtexturecol',   # list[int] or None
    )

    def __init__(self):
        self.curline         = None
        self.x1              = 0
        self.x2              = 0
        self.scale1          = 0
        self.scale2          = 0
        self.scalestep       = 0
        self.silhouette      = SIL_NONE
        self.bsilheight      = 0
        self.tsilheight      = 0
        self.sprtopclip      = None
        self.sprbottomclip   = None
        self.maskedtexturecol = None


# ------------------------------------------------------------------
# vissprite_t  — a thing that will be drawn this frame
# ------------------------------------------------------------------
class VisSprite:
    __slots__ = (
        'prev', 'next',       # doubly-linked list (VisSprite or None)
        'x1', 'x2',
        'gx', 'gy',           # fixed_t world position
        'gz', 'gzt',          # fixed_t global bottom / top
        'startfrac',          # fixed_t horizontal position of x1
        'scale',              # fixed_t
        'xiscale',            # fixed_t (negative if flipped)
        'texturemid',         # fixed_t
        'patch',              # lump index
        'colormap',           # lighttable (list[int] or bytearray slice)
        'mobjflags',
    )

    def __init__(self):
        self.prev       = None
        self.next       = None
        self.x1         = 0
        self.x2         = 0
        self.gx         = 0
        self.gy         = 0
        self.gz         = 0
        self.gzt        = 0
        self.startfrac  = 0
        self.scale      = 0
        self.xiscale    = 0
        self.texturemid = 0
        self.patch      = 0
        self.colormap   = None
        self.mobjflags  = 0


# ------------------------------------------------------------------
# spriteframe_t
# ------------------------------------------------------------------
class SpriteFrame:
    __slots__ = ('rotate', 'lump', 'flip')

    def __init__(self):
        self.rotate = False
        self.lump   = [-1] * 8    # lump index for each of 8 view angles
        self.flip   = [0]  * 8   # 1 = horizontally flipped


# ------------------------------------------------------------------
# spritedef_t
# ------------------------------------------------------------------
class SpriteDef:
    __slots__ = ('numframes', 'spriteframes')

    def __init__(self):
        self.numframes    = 0
        self.spriteframes = []   # list[SpriteFrame]


# ------------------------------------------------------------------
# visplane_t
# ------------------------------------------------------------------
class VisPlane:
    __slots__ = ('height', 'picnum', 'lightlevel', 'minx', 'maxx',
                 'top', 'bottom')

    def __init__(self):
        self.height     = 0       # fixed_t
        self.picnum     = 0
        self.lightlevel = 0
        self.minx       = SCREENWIDTH
        self.maxx       = -1
        # top/bottom: screen-row arrays, one entry per column.
        # 0xFF means "unused" (matching the C byte sentinel 0xff)
        self.top    = bytearray([0xFF] * SCREENWIDTH)
        self.bottom = bytearray([0xFF] * SCREENWIDTH)

    def clear(self):
        self.minx = SCREENWIDTH
        self.maxx = -1
        for i in range(SCREENWIDTH):
            self.top[i]    = 0xFF
            self.bottom[i] = 0xFF
