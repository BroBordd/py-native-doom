# doomdata.py
# Raw WAD map lump data structures (on-disk binary layout)
# Ported from doomdata.h
#
# Each class has:
#   SIZE  - byte size of the packed struct on disk
#   from_bytes(buf, offset=0) - parse from a bytes/bytearray slice
#
# We use struct.unpack_from throughout so this file is self-contained
# (struct is a builtin module).

import struct
from doomdef import (
    ML_LABEL, ML_THINGS, ML_LINEDEFS, ML_SIDEDEFS, ML_VERTEXES,
    ML_SEGS, ML_SSECTORS, ML_NODES, ML_SECTORS, ML_REJECT, ML_BLOCKMAP,
    NF_SUBSECTOR,
    ML_BLOCKING, ML_BLOCKMONSTERS, ML_TWOSIDED,
    ML_DONTPEGTOP, ML_DONTPEGBOTTOM, ML_SECRET,
    ML_SOUNDBLOCK, ML_DONTDRAW, ML_MAPPED,
)


# -------------------------------------------------------
# mapvertex_t  (4 bytes)
# -------------------------------------------------------
class MapVertex:
    SIZE = 4
    _FMT = '<hh'

    __slots__ = ('x', 'y')

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        x, y = struct.unpack_from(cls._FMT, buf, offset)
        return cls(x, y)

    def __repr__(self):
        return f'MapVertex({self.x}, {self.y})'


# -------------------------------------------------------
# mapsidedef_t  (30 bytes)
# -------------------------------------------------------
class MapSidedef:
    SIZE = 30
    _FMT = '<hh8s8s8sh'

    __slots__ = ('textureoffset', 'rowoffset',
                 'toptexture', 'bottomtexture', 'midtexture',
                 'sector')

    def __init__(self, textureoffset, rowoffset,
                 toptexture, bottomtexture, midtexture, sector):
        self.textureoffset = textureoffset
        self.rowoffset     = rowoffset
        self.toptexture    = _decode_name(toptexture)
        self.bottomtexture = _decode_name(bottomtexture)
        self.midtexture    = _decode_name(midtexture)
        self.sector        = sector

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        fields = struct.unpack_from(cls._FMT, buf, offset)
        return cls(*fields)


# -------------------------------------------------------
# maplinedef_t  (14 bytes)
# -------------------------------------------------------
class MapLinedef:
    SIZE = 14
    _FMT = '<hhhhhhh'   # v1 v2 flags special tag side[0] side[1]

    __slots__ = ('v1', 'v2', 'flags', 'special', 'tag', 'sidenum')

    def __init__(self, v1, v2, flags, special, tag, s0, s1):
        self.v1      = v1
        self.v2      = v2
        self.flags   = flags
        self.special = special
        self.tag     = tag
        self.sidenum = (s0, s1)   # sidenum[1] == -1 means one-sided

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        fields = struct.unpack_from(cls._FMT, buf, offset)
        return cls(*fields)

    # Convenience flag tests
    @property
    def blocking(self):      return bool(self.flags & ML_BLOCKING)
    @property
    def twosided(self):      return bool(self.flags & ML_TWOSIDED)
    @property
    def dontpegtop(self):    return bool(self.flags & ML_DONTPEGTOP)
    @property
    def dontpegbottom(self): return bool(self.flags & ML_DONTPEGBOTTOM)
    @property
    def secret(self):        return bool(self.flags & ML_SECRET)


# -------------------------------------------------------
# mapsector_t  (26 bytes)
# -------------------------------------------------------
class MapSector:
    SIZE = 26
    _FMT = '<hh8s8shhh'

    __slots__ = ('floorheight', 'ceilingheight',
                 'floorpic', 'ceilingpic',
                 'lightlevel', 'special', 'tag')

    def __init__(self, floorheight, ceilingheight,
                 floorpic, ceilingpic,
                 lightlevel, special, tag):
        self.floorheight   = floorheight
        self.ceilingheight = ceilingheight
        self.floorpic      = _decode_name(floorpic)
        self.ceilingpic    = _decode_name(ceilingpic)
        self.lightlevel    = lightlevel
        self.special       = special
        self.tag           = tag

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        fields = struct.unpack_from(cls._FMT, buf, offset)
        return cls(*fields)


# -------------------------------------------------------
# mapsubsector_t  (4 bytes)
# -------------------------------------------------------
class MapSubsector:
    SIZE = 4
    _FMT = '<hh'

    __slots__ = ('numsegs', 'firstseg')

    def __init__(self, numsegs, firstseg):
        self.numsegs  = numsegs
        self.firstseg = firstseg

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        numsegs, firstseg = struct.unpack_from(cls._FMT, buf, offset)
        return cls(numsegs, firstseg)


# -------------------------------------------------------
# mapseg_t  (12 bytes)
# -------------------------------------------------------
class MapSeg:
    SIZE = 12
    _FMT = '<hhhhhh'

    __slots__ = ('v1', 'v2', 'angle', 'linedef', 'side', 'offset')

    def __init__(self, v1, v2, angle, linedef, side, offset):
        self.v1      = v1
        self.v2      = v2
        self.angle   = angle
        self.linedef = linedef
        self.side    = side    # 0 = front, 1 = back
        self.offset  = offset

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        fields = struct.unpack_from(cls._FMT, buf, offset)
        return cls(*fields)


# -------------------------------------------------------
# mapnode_t  (28 bytes)
# -------------------------------------------------------
# bbox layout: [child][corner]  corners: BOXTOP=0,BOXBOTTOM=1,BOXLEFT=2,BOXRIGHT=3
class MapNode:
    SIZE = 28
    _FMT = '<hhhh' + 'hhhh' + 'hhhh' + 'HH'
    #        x y dx dy   bbox[0][4]   bbox[1][4]   children[2]

    __slots__ = ('x', 'y', 'dx', 'dy', 'bbox', 'children')

    def __init__(self, x, y, dx, dy, bbox, children):
        self.x        = x
        self.y        = y
        self.dx       = dx
        self.dy       = dy
        self.bbox     = bbox       # ((top,bot,left,right),(top,bot,left,right))
        self.children = children   # (right_child, left_child)  — unsigned shorts

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        vals = struct.unpack_from(cls._FMT, buf, offset)
        x, y, dx, dy = vals[0:4]
        bbox = (vals[4:8], vals[8:12])
        children = (vals[12], vals[13])
        return cls(x, y, dx, dy, bbox, children)

    def is_subsector(self, child_index: int) -> bool:
        return bool(self.children[child_index] & NF_SUBSECTOR)

    def subsector_index(self, child_index: int) -> int:
        return self.children[child_index] & ~NF_SUBSECTOR


# -------------------------------------------------------
# mapthing_t  (10 bytes)
# -------------------------------------------------------
class MapThing:
    SIZE = 10
    _FMT = '<hhhhh'

    __slots__ = ('x', 'y', 'angle', 'type', 'options')

    # options bit flags
    MTF_EASY      = 1
    MTF_MEDIUM    = 2
    MTF_HARD      = 4
    MTF_AMBUSH    = 8
    MTF_COOPERATIVE = 16

    def __init__(self, x, y, angle, type_, options):
        self.x       = x
        self.y       = y
        self.angle   = angle
        self.type    = type_
        self.options = options

    @classmethod
    def from_bytes(cls, buf, offset: int = 0):
        x, y, angle, type_, options = struct.unpack_from(cls._FMT, buf, offset)
        return cls(x, y, angle, type_, options)

    def skill_match(self, skill: int) -> bool:
        """Return True if this thing appears on the given skill (0-4)."""
        if skill <= 1:
            return bool(self.options & self.MTF_EASY)
        elif skill == 2:
            return bool(self.options & self.MTF_MEDIUM)
        else:
            return bool(self.options & self.MTF_HARD)


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def _decode_name(raw: bytes) -> str:
    """Null-terminated 8-byte WAD name → uppercase Python str."""
    try:
        end = raw.index(0)
        raw = raw[:end]
    except ValueError:
        pass
    return raw.decode('ascii', errors='replace').upper()


def load_lump_array(lump_data: bytes, item_class) -> list:
    """
    Generic helper: parse a lump into a list of item_class instances.
    item_class must have SIZE and from_bytes(buf, offset).
    """
    size   = item_class.SIZE
    count  = len(lump_data) // size
    result = []
    for i in range(count):
        result.append(item_class.from_bytes(lump_data, i * size))
    return result
