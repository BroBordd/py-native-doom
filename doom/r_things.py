# r_things.py
# Sprite rendering: R_InitSprites, R_AddSprites, R_ProjectSprite,
# R_DrawVisSprite, R_DrawMasked, R_DrawPlayerSprites
# Ported from r_things.c / r_things.h

from doomdef import (
    SCREENWIDTH, SCREENHEIGHT, FRACBITS, FRACUNIT,
    NUMPSPRITES, fixed_mul, fixed_div,
)
from r_defs import VisSprite, SpriteFrame, SpriteDef
from r_main import (
    LIGHTLEVELS, LIGHTSEGSHIFT, MAXLIGHTSCALE, LIGHTSCALESHIFT,
    NUMCOLORMAPS,
)
from p_mobj import MF_SHADOW, MF_TRANSLATION, MF_TRANSSHIFT, FF_FULLBRIGHT

MINZ         = FRACUNIT * 4
BASEYCENTER  = SCREENHEIGHT // 2
MAXVISSPRITES = 128

FF_FRAMEMASK = 0x7FFF   # low bits of frame field

# ------------------------------------------------------------------
# Sprite database (filled by R_InitSprites)
# ------------------------------------------------------------------
sprites:    list = []    # list[SpriteDef]
numsprites: int  = 0

# Temporary frame builder
_sprtemp:   list = []
_maxframe:  int  = 0
_spritename: str = ''

# ------------------------------------------------------------------
# VisSprite pool
# ------------------------------------------------------------------
vissprites:    list = [VisSprite() for _ in range(MAXVISSPRITES)]
vissprite_p:   int  = 0
_overflow_sprite = VisSprite()

vsprsortedhead = VisSprite()   # sentinel for sorted list

# ------------------------------------------------------------------
# Draw-state shared with r_segs
# ------------------------------------------------------------------
mfloorclip:   list = None
mceilingclip: list = None
spryscale:    int  = 0
sprtopscreen: int  = 0
spritelights: list = []

negonearray:       list = [-1]         * SCREENWIDTH
screenheightarray: list = [SCREENHEIGHT] * SCREENWIDTH


# ------------------------------------------------------------------
# R_InstallSpriteLump
# ------------------------------------------------------------------
def R_InstallSpriteLump(lump: int, frame: int, rotation: int, flipped: bool):
    from r_data import firstspritelump

    if frame >= 29 or rotation > 8:
        raise RuntimeError(f'R_InstallSpriteLump: bad frame chars in lump {lump}')

    global _maxframe
    if frame > _maxframe:
        _maxframe = frame

    sf = _sprtemp[frame]

    if rotation == 0:
        if sf.rotate is False:
            raise RuntimeError(f'R_InitSprites: {_spritename} frame {chr(ord("A")+frame)} has multiple rot=0')
        if sf.rotate is True:
            raise RuntimeError(f'R_InitSprites: {_spritename} frame {chr(ord("A")+frame)} has rotations and rot=0')
        sf.rotate = False
        for r in range(8):
            sf.lump[r] = lump - firstspritelump
            sf.flip[r] = int(flipped)
    else:
        if sf.rotate is False:
            raise RuntimeError(f'R_InitSprites: {_spritename} frame has rotations and rot=0')
        sf.rotate = True
        r = rotation - 1
        if sf.lump[r] != -1:
            raise RuntimeError(f'R_InitSprites: {_spritename} two lumps mapped to same rotation')
        sf.lump[r] = lump - firstspritelump
        sf.flip[r] = int(flipped)


# ------------------------------------------------------------------
# R_InitSpriteDefs
# ------------------------------------------------------------------
def R_InitSpriteDefs(namelist: list):
    global sprites, numsprites, _sprtemp, _maxframe, _spritename
    from r_data import firstspritelump, lastspritelump
    from wad import get_wad

    numsprites = len(namelist)
    if not numsprites:
        return

    wad    = get_wad()
    all_names = wad.list_lumps()
    sprites = []

    for i, name in enumerate(namelist):
        if name is None:
            break
        _spritename = name.upper()[:4]

        # reset temp
        _sprtemp = []
        for _ in range(29):
            sf = SpriteFrame()
            sf.rotate = -1   # -1 = not yet seen
            sf.lump   = [-1] * 8
            sf.flip   = [0]  * 8
            _sprtemp.append(sf)
        _maxframe = -1

        # scan sprite lumps
        for l in range(firstspritelump, lastspritelump + 1):
            lump = wad.get_lump_by_index(l)
            if not lump.name.upper().startswith(_spritename):
                continue
            n = lump.name.upper()
            if len(n) < 6:
                continue
            frame    = ord(n[4]) - ord('A')
            rotation = ord(n[5]) - ord('0')
            R_InstallSpriteLump(l, frame, rotation, False)
            if len(n) >= 8 and n[6]:
                frame2    = ord(n[6]) - ord('A')
                rotation2 = ord(n[7]) - ord('0')
                R_InstallSpriteLump(l, frame2, rotation2, True)

        if _maxframe == -1:
            sd = SpriteDef()
            sd.numframes    = 0
            sd.spriteframes = []
            sprites.append(sd)
            continue

        _maxframe += 1

        # validate
        for frame in range(_maxframe):
            r = _sprtemp[frame].rotate
            if r == -1:
                raise RuntimeError(f'R_InitSprites: no patches for {_spritename} frame {chr(ord("A")+frame)}')
            if r == True:
                for rot in range(8):
                    if _sprtemp[frame].lump[rot] == -1:
                        raise RuntimeError(f'R_InitSprites: {_spritename} frame {chr(ord("A")+frame)} missing rotations')

        sd = SpriteDef()
        sd.numframes    = _maxframe
        sd.spriteframes = [_copy_sprframe(_sprtemp[f]) for f in range(_maxframe)]
        sprites.append(sd)


def _copy_sprframe(sf: SpriteFrame) -> SpriteFrame:
    nf = SpriteFrame()
    nf.rotate = sf.rotate
    nf.lump   = list(sf.lump)
    nf.flip   = list(sf.flip)
    return nf


# ------------------------------------------------------------------
# R_InitSprites
# ------------------------------------------------------------------
def R_InitSprites(namelist: list):
    for i in range(SCREENWIDTH):
        negonearray[i] = -1
    R_InitSpriteDefs(namelist)


# ------------------------------------------------------------------
# R_ClearSprites
# ------------------------------------------------------------------
def R_ClearSprites():
    global vissprite_p
    vissprite_p = 0


# ------------------------------------------------------------------
# R_NewVisSprite
# ------------------------------------------------------------------
def R_NewVisSprite() -> VisSprite:
    global vissprite_p
    if vissprite_p == MAXVISSPRITES:
        return _overflow_sprite
    vs = vissprites[vissprite_p]
    vissprite_p += 1
    return vs


# ------------------------------------------------------------------
# R_DrawMaskedColumnRaw — draw column data (bytes) as masked column
# ------------------------------------------------------------------
def R_DrawMaskedColumnRaw(col_data, dc_x: int, mfloor, mceiling):
    """
    col_data: bytes/bytearray/memoryview of a raw texture column (height bytes).
    We iterate over pseudo-posts reading the entire column as one solid post.
    """
    import r_draw, r_main
    from doomdef import FRACBITS, FRACUNIT

    # Treat the column as one big post from top=0, length=len(col_data)
    length    = len(col_data)
    topdelta  = 0

    topscreen    = sprtopscreen + spryscale * topdelta
    bottomscreen = topscreen + spryscale * length

    dc_yl = (topscreen + FRACUNIT - 1) >> FRACBITS
    dc_yh = (bottomscreen - 1)         >> FRACBITS

    # apply clip
    floor_val   = mfloor[dc_x]   if mfloor   else r_main.viewheight
    ceiling_val = mceiling[dc_x] if mceiling else -1

    if dc_yh >= floor_val:   dc_yh = floor_val   - 1
    if dc_yl <= ceiling_val: dc_yl = ceiling_val + 1

    if dc_yl <= dc_yh:
        r_draw.dc_yl     = dc_yl
        r_draw.dc_yh     = dc_yh
        r_draw.dc_source = col_data
        r_draw.dc_x      = dc_x
        r_main.colfunc()


# ------------------------------------------------------------------
# R_DrawMaskedColumn  — draw a column_t post list
# col_data: bytes starting at the post header (topdelta byte first)
# ------------------------------------------------------------------
def R_DrawMaskedColumn(col_data, col_offset: int = 0):
    import r_draw, r_main
    basetexturemid = r_draw.dc_texturemid
    pos = col_offset
    data = col_data

    while True:
        topdelta = data[pos]
        if topdelta == 0xFF:
            break
        length = data[pos + 1]
        # pixels start at pos+3
        topscreen    = sprtopscreen + spryscale * topdelta
        bottomscreen = topscreen + spryscale * length

        dc_yl = (topscreen    + FRACUNIT - 1) >> FRACBITS
        dc_yh = (bottomscreen - 1)             >> FRACBITS

        floor_val   = mfloorclip[r_draw.dc_x]   if mfloorclip   else r_main.viewheight
        ceiling_val = mceilingclip[r_draw.dc_x] if mceilingclip else -1

        if dc_yh >= floor_val:   dc_yh = floor_val   - 1
        if dc_yl <= ceiling_val: dc_yl = ceiling_val + 1

        if dc_yl <= dc_yh:
            r_draw.dc_yl         = dc_yl
            r_draw.dc_yh         = dc_yh
            r_draw.dc_source     = memoryview(data)[pos + 3: pos + 3 + length]
            r_draw.dc_texturemid = basetexturemid - (topdelta << FRACBITS)
            r_main.colfunc()

        pos += length + 4  # skip topdelta(1)+length(1)+unused(1)+pixels+unused(1)

    r_draw.dc_texturemid = basetexturemid


# ------------------------------------------------------------------
# R_DrawVisSprite
# ------------------------------------------------------------------
def R_DrawVisSprite(vis: VisSprite, x1: int, x2: int):
    global spryscale, sprtopscreen, mfloorclip, mceilingclip
    import r_draw, r_main
    from r_data import firstspritelump, colormaps
    from wad import get_wad

    wad       = get_wad()
    patch_lump = wad.get_lump_by_index(vis.patch + firstspritelump)
    patch_data = patch_lump.data

    import struct
    pw, ph, leftofs, topofs = struct.unpack_from('<hhhh', patch_data, 0)
    col_offsets = list(struct.unpack_from(f'<{pw}i', patch_data, 8))

    r_draw.dc_colormap = vis.colormap

    if vis.colormap is None:
        r_main.colfunc = r_main.fuzzcolfunc
    elif vis.mobjflags & MF_TRANSLATION:
        r_main.colfunc = r_main.transcolfunc
        shift = MF_TRANSSHIFT - 8
        idx   = (vis.mobjflags & MF_TRANSLATION) >> shift
        r_draw.dc_translation = memoryview(r_draw.translationtables)[idx * 256: (idx + 1) * 256]

    r_draw.dc_iscale   = abs(vis.xiscale) >> r_main.detailshift
    r_draw.dc_texturemid = vis.texturemid
    frac               = vis.startfrac
    spryscale          = vis.scale
    sprtopscreen       = r_main.centeryfrac - fixed_mul(r_draw.dc_texturemid, spryscale)

    for dc_x in range(x1, x2 + 1):
        texturecolumn = frac >> FRACBITS
        if 0 <= texturecolumn < pw:
            r_draw.dc_x = dc_x
            col_data    = patch_data
            col_ofs     = col_offsets[texturecolumn]
            R_DrawMaskedColumn(col_data, col_ofs)
        frac += vis.xiscale

    r_main.colfunc = r_main.basecolfunc


# ------------------------------------------------------------------
# R_ProjectSprite
# ------------------------------------------------------------------
def R_ProjectSprite(thing):
    global spritelights
    import r_main
    from doomdef import ANG45

    tr_x = thing.x - r_main.viewx
    tr_y = thing.y - r_main.viewy

    gxt = fixed_mul(tr_x,  r_main.viewcos)
    gyt = fixed_mul(tr_y, -r_main.viewsin)
    tz  = gxt - gyt

    if tz < MINZ:
        return

    xscale = fixed_div(r_main.projection, tz)

    gxt = fixed_mul(tr_x, -r_main.viewsin)
    gyt = fixed_mul(tr_y,  r_main.viewcos)
    tx  = -(gyt + gxt)

    if abs(tx) > (tz << 2):
        return

    if thing.sprite >= len(sprites):
        return
    sprdef = sprites[thing.sprite]
    if sprdef.numframes == 0:
        return

    frame_idx = thing.frame & FF_FRAMEMASK
    if frame_idx >= sprdef.numframes:
        return
    sprframe = sprdef.spriteframes[frame_idx]

    if sprframe.rotate:
        ang = r_main.R_PointToAngle(thing.x, thing.y)
        rot = ((ang - thing.angle + ANG45 // 2 * 9) >> 29) & 7
        lump = sprframe.lump[rot]
        flip = bool(sprframe.flip[rot])
    else:
        lump = sprframe.lump[0]
        flip = bool(sprframe.flip[0])

    from r_data import spritewidth, spriteoffset, spritetopoffset

    tx -= spriteoffset[lump]
    x1  = (r_main.centerxfrac + fixed_mul(tx, xscale)) >> FRACBITS
    if x1 > r_main.viewwidth:
        return

    tx += spritewidth[lump]
    x2  = ((r_main.centerxfrac + fixed_mul(tx, xscale)) >> FRACBITS) - 1
    if x2 < 0:
        return

    vis = R_NewVisSprite()
    vis.mobjflags = thing.flags
    vis.scale     = xscale << r_main.detailshift
    vis.gx        = thing.x
    vis.gy        = thing.y
    vis.gz        = thing.z
    vis.gzt       = thing.z + spritetopoffset[lump]
    vis.texturemid = vis.gzt - r_main.viewz
    vis.x1        = max(0, x1)
    vis.x2        = min(r_main.viewwidth - 1, x2)

    iscale = fixed_div(FRACUNIT, xscale)
    if flip:
        vis.startfrac = spritewidth[lump] - 1
        vis.xiscale   = -iscale
    else:
        vis.startfrac = 0
        vis.xiscale   = iscale

    if vis.x1 > x1:
        vis.startfrac += vis.xiscale * (vis.x1 - x1)
    vis.patch = lump

    from r_data import colormaps
    if thing.flags & MF_SHADOW:
        vis.colormap = None
    elif r_main.fixedcolormap:
        vis.colormap = r_main.fixedcolormap
    elif thing.frame & FF_FULLBRIGHT:
        vis.colormap = 0   # colormaps level 0 = bright
    else:
        index = xscale >> (LIGHTSCALESHIFT - r_main.detailshift)
        if index >= MAXLIGHTSCALE:
            index = MAXLIGHTSCALE - 1
        vis.colormap = spritelights[index]


# ------------------------------------------------------------------
# R_AddSprites
# ------------------------------------------------------------------
def R_AddSprites(sec):
    global spritelights
    import r_main

    if sec.validcount == r_main.validcount:
        return
    sec.validcount = r_main.validcount

    lightnum = (sec.lightlevel >> LIGHTSEGSHIFT) + r_main.extralight
    lightnum = max(0, min(lightnum, LIGHTLEVELS - 1))
    spritelights = r_main.scalelight[lightnum]

    thing = sec.thinglist
    while thing:
        R_ProjectSprite(thing)
        thing = thing.snext


# ------------------------------------------------------------------
# R_DrawPSprite  — player weapon sprite
# ------------------------------------------------------------------
def R_DrawPSprite(psp):
    global spryscale, sprtopscreen, mfloorclip, mceilingclip
    import r_main, r_draw
    from r_data import spriteoffset, spritewidth, spritetopoffset

    if psp.state is None:
        return

    sprdef = sprites[psp.state.sprite]
    if sprdef.numframes == 0:
        return
    sprframe = sprdef.spriteframes[psp.state.frame & FF_FRAMEMASK]

    lump = sprframe.lump[0]
    flip = bool(sprframe.flip[0])

    tx = psp.sx - (SCREENWIDTH // 2) * FRACUNIT
    tx -= spriteoffset[lump]
    x1  = (r_main.centerxfrac + fixed_mul(tx, r_main.pspritescale)) >> FRACBITS
    if x1 > r_main.viewwidth:
        return

    tx += spritewidth[lump]
    x2  = ((r_main.centerxfrac + fixed_mul(tx, r_main.pspritescale)) >> FRACBITS) - 1
    if x2 < 0:
        return

    vis = VisSprite()
    vis.mobjflags  = 0
    vis.texturemid = ((BASEYCENTER << FRACBITS) + FRACUNIT // 2 -
                      (psp.sy - spritetopoffset[lump]))
    vis.x1    = max(0, x1)
    vis.x2    = min(r_main.viewwidth - 1, x2)
    vis.scale = r_main.pspritescale << r_main.detailshift

    if flip:
        vis.xiscale  = -r_main.pspriteiscale
        vis.startfrac = spritewidth[lump] - 1
    else:
        vis.xiscale  = r_main.pspriteiscale
        vis.startfrac = 0

    if vis.x1 > x1:
        vis.startfrac += vis.xiscale * (vis.x1 - x1)
    vis.patch = lump

    from r_data import colormaps
    import doomstat
    from doomdef import PowerType
    if (r_main.viewplayer.powers[PowerType.INVISIBILITY] > 4 * 32 or
            r_main.viewplayer.powers[PowerType.INVISIBILITY] & 8):
        vis.colormap = None
    elif r_main.fixedcolormap:
        vis.colormap = r_main.fixedcolormap
    elif psp.state.frame & FF_FULLBRIGHT:
        vis.colormap = 0
    else:
        vis.colormap = spritelights[MAXLIGHTSCALE - 1]

    mfloorclip   = screenheightarray
    mceilingclip = negonearray
    R_DrawVisSprite(vis, vis.x1, vis.x2)


# ------------------------------------------------------------------
# R_DrawPlayerSprites
# ------------------------------------------------------------------
def R_DrawPlayerSprites():
    global spritelights, mfloorclip, mceilingclip
    import r_main

    lightnum = ((r_main.viewplayer.mo.subsector.sector.lightlevel >> LIGHTSEGSHIFT) +
                r_main.extralight)
    lightnum = max(0, min(lightnum, LIGHTLEVELS - 1))
    spritelights = r_main.scalelight[lightnum]

    mfloorclip   = screenheightarray
    mceilingclip = negonearray

    for i in range(NUMPSPRITES):
        psp = r_main.viewplayer.psprites[i]
        if psp.state:
            R_DrawPSprite(psp)


# ------------------------------------------------------------------
# R_SortVisSprites  — selection sort by scale (back-to-front)
# ------------------------------------------------------------------
def R_SortVisSprites():
    count = vissprite_p
    if not count:
        vsprsortedhead.next = vsprsortedhead.prev = vsprsortedhead
        return

    # Build a simple sorted list using Python sort (O(n log n))
    # The C code does a selection sort — same result.
    active = vissprites[:count]
    active_sorted = sorted(active, key=lambda v: v.scale)

    # thread into doubly-linked list with vsprsortedhead sentinel
    vsprsortedhead.next = active_sorted[0]
    vsprsortedhead.prev = active_sorted[-1]
    for i, v in enumerate(active_sorted):
        v.prev = active_sorted[i - 1] if i > 0 else vsprsortedhead
        v.next = active_sorted[i + 1] if i < len(active_sorted) - 1 else vsprsortedhead


# ------------------------------------------------------------------
# R_DrawSprite  — clip and draw one vissprite
# ------------------------------------------------------------------
def R_DrawSprite(spr: VisSprite):
    global mfloorclip, mceilingclip
    import r_main
    from r_defs import SIL_BOTTOM, SIL_TOP, SIL_BOTH

    clipbot = [-2] * SCREENWIDTH
    cliptop = [-2] * SCREENWIDTH

    import r_bsp
    import r_segs

    for ds_idx in range(r_bsp.ds_p - 1, -1, -1):
        ds = r_bsp.drawsegs[ds_idx]

        if ds.x1 > spr.x2 or ds.x2 < spr.x1:
            continue
        if not ds.silhouette and not ds.maskedtexturecol:
            continue

        r1 = max(ds.x1, spr.x1)
        r2 = min(ds.x2, spr.x2)

        scale    = max(ds.scale1, ds.scale2)
        lowscale = min(ds.scale1, ds.scale2)

        if (scale < spr.scale or
                (lowscale < spr.scale and
                 not r_main.R_PointOnSegSide(spr.gx, spr.gy, ds.curline))):
            if ds.maskedtexturecol:
                r_segs.R_RenderMaskedSegRange(ds, r1, r2)
            continue

        silhouette = ds.silhouette

        if spr.gz  >= ds.bsilheight: silhouette &= ~SIL_BOTTOM
        if spr.gzt <= ds.tsilheight: silhouette &= ~SIL_TOP

        def _get_clip(arr_info, x):
            if arr_info is None:
                return -2
            if isinstance(arr_info, list):
                return arr_info[x]
            base, xoff = arr_info
            import r_plane
            idx = base + x - xoff
            if 0 <= idx < len(r_plane.openings):
                return r_plane.openings[idx]
            return -2

        for x in range(r1, r2 + 1):
            if silhouette & SIL_BOTTOM:
                if clipbot[x] == -2:
                    clipbot[x] = _get_clip(ds.sprbottomclip, x)
            if silhouette & SIL_TOP:
                if cliptop[x] == -2:
                    cliptop[x] = _get_clip(ds.sprtopclip, x)

    # fill unclipped
    for x in range(spr.x1, spr.x2 + 1):
        if clipbot[x] == -2: clipbot[x] = r_main.viewheight
        if cliptop[x] == -2: cliptop[x] = -1

    mfloorclip   = clipbot
    mceilingclip = cliptop
    R_DrawVisSprite(spr, spr.x1, spr.x2)


# ------------------------------------------------------------------
# R_DrawMasked  — draw all vissprites + masked mid textures + psprites
# ------------------------------------------------------------------
def R_DrawMasked():
    import r_main, r_bsp, r_segs

    R_SortVisSprites()

    spr = vsprsortedhead.next
    while spr is not vsprsortedhead:
        R_DrawSprite(spr)
        spr = spr.next

    # remaining masked mid textures
    for ds_idx in range(r_bsp.ds_p - 1, -1, -1):
        ds = r_bsp.drawsegs[ds_idx]
        if ds.maskedtexturecol:
            r_segs.R_RenderMaskedSegRange(ds, ds.x1, ds.x2)

    if not r_main.viewangleoffset:
        R_DrawPlayerSprites()


# ------------------------------------------------------------------
# R_InitTranslationTables  (delegated to r_draw)
# ------------------------------------------------------------------
def R_InitTranslationTables():
    import r_draw
    r_draw.R_InitTranslationTables()
