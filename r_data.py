# r_data.py
# Texture / flat / sprite / colormap data loading and retrieval
# Ported from r_data.c / r_data.h

import struct
from doomdef import FRACBITS, FRACUNIT

# ------------------------------------------------------------------
# Patch (sprite/wall graphic) on-disk format helpers
# ------------------------------------------------------------------
# patch_t header: width(2) height(2) leftoffset(2) topoffset(2) columnofs[width](4 each)
# column_t post: topdelta(1) length(1) unused(1) data[length] unused(1)
# topdelta==0xFF → end of column

def _patch_header(data: bytes):
    """Return (width, height, leftoffset, topoffset) from patch bytes."""
    return struct.unpack_from('<hhhh', data, 0)

def _patch_columnofs(data: bytes, width: int):
    """Return list of column offsets (int32) for a patch."""
    return list(struct.unpack_from(f'<{width}i', data, 8))

def _decode_posts(data: bytes, col_offset: int):
    """
    Generator: yield (topdelta, pixels:bytes) for each post in a column.
    Stops at topdelta==0xFF.
    """
    pos = col_offset
    while True:
        topdelta = data[pos]
        if topdelta == 0xFF:
            break
        length = data[pos + 1]
        # post layout: topdelta(1) length(1) unused(1) pixels(length) unused(1)
        pixels = data[pos + 3: pos + 3 + length]
        yield topdelta, pixels
        pos += length + 4


# ------------------------------------------------------------------
# Texture definition (runtime)
# ------------------------------------------------------------------
class TexPatch:
    """One patch composited into a texture."""
    __slots__ = ('originx', 'originy', 'patch_lump')

    def __init__(self, originx, originy, patch_lump):
        self.originx    = originx
        self.originy    = originy
        self.patch_lump = patch_lump   # WAD lump index


class Texture:
    __slots__ = ('name', 'width', 'height', 'patches',
                 'widthmask',        # (next power-of-two width) - 1
                 'height_fixed',     # height << FRACBITS
                 # column cache: per-column data or None if not yet composited
                 '_col_lump',        # list[int]  lump idx or -1 = composite
                 '_col_ofs',         # list[int]  byte offset into lump or composite
                 '_composite',       # bytearray or None
                 '_composite_size',  # int
                 )

    def __init__(self, name, width, height, patches):
        self.name    = name
        self.width   = width
        self.height  = height
        self.patches = patches          # list[TexPatch]

        j = 1
        while j * 2 <= width:
            j <<= 1
        self.widthmask      = j - 1
        self.height_fixed   = height << FRACBITS
        self._col_lump      = [-2] * width   # -2 = uninitialised
        self._col_ofs       = [0]  * width
        self._composite     = None
        self._composite_size = 0


# ------------------------------------------------------------------
# Module-level data tables
# ------------------------------------------------------------------
# Textures
numtextures: int = 0
textures: list   = []            # list[Texture]
_tex_by_name: dict = {}          # uppercase name → index (last wins = vanilla)

# Flats
firstflat:  int = 0
lastflat:   int = 0
numflats:   int = 0
flattranslation: list = []       # list[int] identity initially

# Sprites
firstspritelump: int = 0
lastspritelump:  int = 0
numspritelumps:  int = 0
spritewidth:     list = []       # list[fixed_t]
spriteoffset:    list = []       # list[fixed_t]
spritetopoffset: list = []       # list[fixed_t]

# Animation translation tables (mutable; P_Spec may swap entries)
texturetranslation: list = []    # list[int]

# Colormap: 32 × 256 bytes
colormaps: bytearray = bytearray()   # flat 8192 bytes

# Sky texture index (set by R_InitSkyMap / r_sky.py)
skytexture: int = 0


# ------------------------------------------------------------------
# Lump-name hash (matches W_LumpNameHash from w_wad.c)
# Used for the texture hash table (vanilla lookup order).
# ------------------------------------------------------------------
def _lump_name_hash(name: str) -> int:
    name = name.upper()[:8]
    h = 0
    for c in name:
        h = ((h << 4) + ord(c)) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= (g >> 24)
        h &= ~g
    return h


# ------------------------------------------------------------------
# R_InitColormaps
# ------------------------------------------------------------------
def R_InitColormaps():
    global colormaps
    from wad import get_wad
    wad = get_wad()
    data = wad.get_lump_data('COLORMAP')
    colormaps = bytearray(data)
    # Ensure exactly 32×256 = 8192 bytes
    if len(colormaps) < 8192:
        colormaps += bytearray(8192 - len(colormaps))


def get_colormap(level: int) -> memoryview:
    """Return a memoryview of the 256-byte colormap at the given level (0=bright,31=dark)."""
    level = max(0, min(level, 31))
    return memoryview(colormaps)[level * 256: level * 256 + 256]


# ------------------------------------------------------------------
# R_InitFlats
# ------------------------------------------------------------------
def R_InitFlats():
    global firstflat, lastflat, numflats, flattranslation
    from wad import get_wad
    wad = get_wad()
    # Find F_START / F_END markers
    all_names = wad.list_lumps()
    firstflat = all_names.index('F_START') + 1
    lastflat  = all_names.index('F_END')   - 1
    numflats  = lastflat - firstflat + 1
    flattranslation = list(range(numflats))

    # Set skyflatnum in doomstat
    import doomstat
    try:
        doomstat.skyflatnum = R_FlatNumForName('F_SKY1')
    except KeyError:
        doomstat.skyflatnum = 0


# ------------------------------------------------------------------
# R_InitTextures
# ------------------------------------------------------------------
def R_InitTextures():
    global numtextures, textures, _tex_by_name, texturetranslation
    from wad import get_wad
    wad = get_wad()

    all_names = wad.list_lumps()

    # Build patch name → lump index lookup from PNAMES
    pnames_data = wad.get_lump_data('PNAMES')
    npatches = struct.unpack_from('<i', pnames_data, 0)[0]
    patch_lump_by_idx = []
    for i in range(npatches):
        raw = pnames_data[4 + i * 8: 4 + i * 8 + 8]
        name = raw.rstrip(b'\x00').decode('ascii', errors='replace').upper()
        try:
            patch_lump_by_idx.append(all_names.index(name))
        except ValueError:
            patch_lump_by_idx.append(-1)

    def _parse_texlump(data: bytes) -> list:
        """Parse a TEXTURE1/TEXTURE2 lump; return list of Texture."""
        result = []
        ntex = struct.unpack_from('<i', data, 0)[0]
        for i in range(ntex):
            offset = struct.unpack_from('<i', data, 4 + i * 4)[0]
            # maptexture_t: name(8) masked(4) width(2) height(2) obsolete(4) patchcount(2)
            name_raw = data[offset: offset + 8].rstrip(b'\x00')
            name = name_raw.decode('ascii', errors='replace').upper()
            _masked, width, height, _obs, pcount = struct.unpack_from(
                '<ihhih', data, offset + 8)
            patches = []
            patch_off = offset + 22  # sizeof header up to patches
            for _ in range(pcount):
                # mappatch_t: originx(2) originy(2) patch(2) stepdir(2) colormap(2)
                ox, oy, pidx = struct.unpack_from('<hhh', data, patch_off)
                lump_idx = patch_lump_by_idx[pidx] if 0 <= pidx < len(patch_lump_by_idx) else -1
                patches.append(TexPatch(ox, oy, lump_idx))
                patch_off += 10
            result.append(Texture(name, width, height, patches))
        return result

    tex_list = _parse_texlump(wad.get_lump_data('TEXTURE1'))
    if wad.has_lump('TEXTURE2'):
        tex_list += _parse_texlump(wad.get_lump_data('TEXTURE2'))

    textures = tex_list
    numtextures = len(textures)

    # Build name→index dict (first occurrence wins, vanilla behaviour)
    _tex_by_name = {}
    for i, t in enumerate(textures):
        if t.name not in _tex_by_name:
            _tex_by_name[t.name] = i

    # Generate per-texture column lookup tables
    _wad = get_wad()
    for i, tex in enumerate(textures):
        _generate_lookup(i, tex, _wad, all_names)

    texturetranslation = list(range(numtextures))


def _generate_lookup(texnum: int, tex: Texture, wad, all_names: list):
    """
    Populate tex._col_lump and tex._col_ofs.
    Columns covered by a single patch get lump+offset;
    multi-patch columns get lump=-1 and point into the composite.
    """
    patchcount = [0] * tex.width
    col_lump   = [-2] * tex.width
    col_ofs    = [0]  * tex.width
    composite_size = 0

    for tp in tex.patches:
        if tp.patch_lump < 0:
            continue
        try:
            pdata = wad.get_lump_by_index(tp.patch_lump).data
        except Exception:
            continue
        pw, _ph, _lo, _to = _patch_header(pdata)
        col_offsets = _patch_columnofs(pdata, pw)
        x1 = tp.originx
        x2 = x1 + pw
        x  = max(0, x1)
        x2 = min(x2, tex.width)
        for cx in range(x, x2):
            patchcount[cx] += 1
            col_lump[cx] = tp.patch_lump
            # +3 skips topdelta/length/unused in first post header
            col_ofs[cx] = col_offsets[cx - x1] + 3

    for cx in range(tex.width):
        if patchcount[cx] > 1:
            col_lump[cx] = -1   # needs composite
            col_ofs[cx]  = composite_size
            composite_size += tex.height

    tex._col_lump       = col_lump
    tex._col_ofs        = col_ofs
    tex._composite_size = composite_size


def _generate_composite(texnum: int):
    """Build the composite bytearray for textures with multi-patch columns."""
    from wad import get_wad
    wad = get_wad()
    tex = textures[texnum]
    composite = bytearray(tex._composite_size)

    for tp in tex.patches:
        if tp.patch_lump < 0:
            continue
        try:
            pdata = wad.get_lump_by_index(tp.patch_lump).data
        except Exception:
            continue
        pw, _ph, _lo, _to = _patch_header(pdata)
        col_offsets = _patch_columnofs(pdata, pw)
        x1 = tp.originx
        x2 = min(x1 + pw, tex.width)
        x  = max(0, x1)
        for cx in range(x, x2):
            if tex._col_lump[cx] != -1:
                continue   # single-patch column, skip
            cache_ofs = tex._col_ofs[cx]
            for topdelta, pixels in _decode_posts(pdata, col_offsets[cx - x1]):
                dst = cache_ofs + tp.originy + topdelta
                src_end = min(dst + len(pixels), cache_ofs + tex.height)
                src_start = max(dst, cache_ofs)
                if src_start >= src_end:
                    continue
                src_slice = pixels[src_start - dst: src_end - dst]
                composite[src_start: src_end] = src_slice

    tex._composite = composite


# ------------------------------------------------------------------
# R_GetColumn
# ------------------------------------------------------------------
def R_GetColumn(tex: int, col: int) -> memoryview:
    """
    Return a memoryview of the pixel column data for texture tex, column col.
    The returned view starts at the first pixel and has length tex.height.
    """
    from wad import get_wad
    t   = textures[texturetranslation[tex]]
    col = col & t.widthmask
    lump = t._col_lump[col]
    ofs  = t._col_ofs[col]

    if lump > 0:
        data = get_wad().get_lump_by_index(lump).data
        return memoryview(data)[ofs: ofs + t.height]

    if t._composite is None:
        _generate_composite(tex)

    return memoryview(t._composite)[ofs: ofs + t.height]


# ------------------------------------------------------------------
# R_InitSpriteLumps
# ------------------------------------------------------------------
def R_InitSpriteLumps():
    global firstspritelump, lastspritelump, numspritelumps
    global spritewidth, spriteoffset, spritetopoffset
    from wad import get_wad
    wad = get_wad()
    all_names = wad.list_lumps()

    # Try S_START first, fall back to SS_START
    try:
        firstspritelump = all_names.index('S_START') + 1
        lastspritelump  = all_names.index('S_END')   - 1
    except ValueError:
        firstspritelump = all_names.index('SS_START') + 1
        lastspritelump  = all_names.index('SS_END')   - 1

    numspritelumps = lastspritelump - firstspritelump + 1
    spritewidth    = [0] * numspritelumps
    spriteoffset   = [0] * numspritelumps
    spritetopoffset = [0] * numspritelumps

    for i in range(numspritelumps):
        lump = wad.get_lump_by_index(firstspritelump + i)
        if not lump.data:
            continue
        w, _h, lo, to = _patch_header(lump.data)
        spritewidth[i]     = w  << FRACBITS
        spriteoffset[i]    = lo << FRACBITS
        spritetopoffset[i] = to << FRACBITS


# ------------------------------------------------------------------
# R_InitData  — top-level init
# ------------------------------------------------------------------
def R_InitData():
    R_InitTextures()
    R_InitFlats()
    R_InitSpriteLumps()
    R_InitColormaps()


# ------------------------------------------------------------------
# R_FlatNumForName
# ------------------------------------------------------------------
def R_FlatNumForName(name: str) -> int:
    name = name.upper()
    from wad import get_wad
    wad = get_wad()
    all_names = wad.list_lumps()
    try:
        idx = all_names.index(name)
    except ValueError:
        raise KeyError(f'R_FlatNumForName: {name} not found')
    return idx - firstflat


# ------------------------------------------------------------------
# R_CheckTextureNumForName / R_TextureNumForName
# ------------------------------------------------------------------
def R_CheckTextureNumForName(name: str) -> int:
    """Return texture index, or -1 if not found. '-' → 0 (no texture)."""
    if not name or name[0] == '-':
        return 0
    return _tex_by_name.get(name.upper(), -1)


def R_TextureNumForName(name: str) -> int:
    i = R_CheckTextureNumForName(name)
    if i == -1:
        raise KeyError(f'R_TextureNumForName: {name} not found')
    return i


# ------------------------------------------------------------------
# R_PrecacheLevel
# ------------------------------------------------------------------
def R_PrecacheLevel():
    """
    Pre-generate composite textures for all textures used on the level,
    and confirm flat/sprite data is accessible.
    No-op in demo playback.
    """
    import doomstat
    from p_setup import sectors, sides
    from d_think import thinkercap

    if doomstat.demoplayback:
        return

    # Flats used on level
    flat_used = set()
    for s in sectors:
        flat_used.add(s.floorpic)
        flat_used.add(s.ceilingpic)

    # Textures used on level
    tex_used = set()
    for sd in sides:
        tex_used.add(texturetranslation[sd.toptexture])
        tex_used.add(texturetranslation[sd.midtexture])
        tex_used.add(texturetranslation[sd.bottomtexture])
    tex_used.add(skytexture)

    # Force composite generation for multi-patch textures
    for ti in tex_used:
        if 0 <= ti < numtextures:
            t = textures[ti]
            if t._composite_size > 0 and t._composite is None:
                _generate_composite(ti)

    # Sprites used by live thinkers
    from p_mobj import Mobj, P_MobjThinker
    sprite_used = set()
    for th in thinkercap:
        if isinstance(th, Mobj):
            sprite_used.add(th.sprite)
    # (Actual sprite lump caching not needed — WAD is always in memory)
