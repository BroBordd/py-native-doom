# r_segs.py
# Wall segment rendering: R_StoreWallRange and R_RenderSegLoop
# Ported from r_segs.c / r_segs.h
#
# On import this module patches r_bsp.R_StoreWallRange so the BSP
# traversal can call it without circular imports.

from doomdef import (
    FRACBITS, FRACUNIT, SCREENWIDTH,
    ANG90, ANG180,
    fixed_mul, fixed_div,
    ML_DONTPEGTOP, ML_DONTPEGBOTTOM, ML_MAPPED,
)
from tables import ANGLETOFINESHIFT, finesine, finetangent, ANG45
from r_defs import (
    DrawSeg, MAXDRAWSEGS,
    SIL_NONE, SIL_BOTTOM, SIL_TOP, SIL_BOTH,
)
from r_main import (
    LIGHTLEVELS, LIGHTSEGSHIFT, MAXLIGHTSCALE, LIGHTSCALESHIFT,
    NUMCOLORMAPS,
)

HEIGHTBITS = 12
HEIGHTUNIT = 1 << HEIGHTBITS

INT_MAX =  0x7FFFFFFF
INT_MIN = -0x80000000
SHRT_MAX = 32767

# ------------------------------------------------------------------
# Seg rendering state
# ------------------------------------------------------------------
segtextured:   bool = False
markfloor:     bool = False
markceiling:   bool = False
maskedtexture: bool = False

toptexture:    int = 0
bottomtexture: int = 0
midtexture:    int = 0

rw_normalangle: int = 0
rw_angle1:      int = 0
rw_x:           int = 0
rw_stopx:       int = 0
rw_centerangle: int = 0
rw_offset:      int = 0
rw_distance:    int = 0
rw_scale:       int = 0
rw_scalestep:   int = 0
rw_midtexturemid:    int = 0
rw_toptexturemid:    int = 0
rw_bottomtexturemid: int = 0

worldtop:    int = 0
worldbottom: int = 0
worldhigh:   int = 0
worldlow:    int = 0

pixhigh:     int = 0
pixlow:      int = 0
pixhighstep: int = 0
pixlowstep:  int = 0

topfrac:    int = 0
topstep:    int = 0
bottomfrac: int = 0
bottomstep: int = 0

walllights: list = []        # list of colormap levels

maskedtexturecol: list = []  # per-column texture col or SHRT_MAX

# clip arrays (filled from openings pool via r_plane.lastopening)
negonearray:       list = [-1]           * SCREENWIDTH
screenheightarray: list = [0]            * SCREENWIDTH   # filled in R_ExecuteSetViewSize


# ------------------------------------------------------------------
# R_RenderSegLoop
# ------------------------------------------------------------------
def R_RenderSegLoop():
    global topfrac, bottomfrac, rw_scale

    import r_draw, r_main, r_plane, doomstat
    from r_data import R_GetColumn

    viewheight = r_main.viewheight

    for rw_x_cur in range(rw_x, rw_stopx):
        # ceiling/floor boundaries
        yl = (topfrac + HEIGHTUNIT - 1) >> HEIGHTBITS
        if yl < r_plane.ceilingclip[rw_x_cur] + 1:
            yl = r_plane.ceilingclip[rw_x_cur] + 1

        if markceiling:
            top    = r_plane.ceilingclip[rw_x_cur] + 1
            bottom = yl - 1
            if bottom >= r_plane.floorclip[rw_x_cur]:
                bottom = r_plane.floorclip[rw_x_cur] - 1
            if top <= bottom and r_plane.ceilingplane:
                r_plane.ceilingplane.top[rw_x_cur]    = top
                r_plane.ceilingplane.bottom[rw_x_cur] = bottom

        yh = bottomfrac >> HEIGHTBITS
        if yh >= r_plane.floorclip[rw_x_cur]:
            yh = r_plane.floorclip[rw_x_cur] - 1

        if markfloor:
            top    = yh + 1
            bottom = r_plane.floorclip[rw_x_cur] - 1
            if top <= r_plane.ceilingclip[rw_x_cur]:
                top = r_plane.ceilingclip[rw_x_cur] + 1
            if top <= bottom and r_plane.floorplane:
                r_plane.floorplane.top[rw_x_cur]    = top
                r_plane.floorplane.bottom[rw_x_cur] = bottom

        if segtextured:
            angle      = ((rw_centerangle + r_main.xtoviewangle[rw_x_cur]) >> ANGLETOFINESHIFT) & 0x1FFF
            texturecol = rw_offset - fixed_mul(finetangent[angle], rw_distance)
            texturecol >>= FRACBITS

            index = rw_scale >> LIGHTSCALESHIFT
            if index >= MAXLIGHTSCALE:
                index = MAXLIGHTSCALE - 1
            r_draw.dc_colormap = walllights[index]
            r_draw.dc_x        = rw_x_cur
            r_draw.dc_iscale   = 0xFFFFFFFF // max(1, rw_scale)
        else:
            texturecol = 0

        # single-sided wall
        if midtexture:
            r_draw.dc_yl         = yl
            r_draw.dc_yh         = yh
            r_draw.dc_texturemid = rw_midtexturemid
            r_draw.dc_source     = R_GetColumn(midtexture, texturecol)
            r_main.colfunc()
            r_plane.ceilingclip[rw_x_cur] = viewheight
            r_plane.floorclip[rw_x_cur]   = -1
        else:
            # top texture
            if toptexture:
                mid = pixhigh >> HEIGHTBITS
                # pixhigh update applied after this column
                if mid >= r_plane.floorclip[rw_x_cur]:
                    mid = r_plane.floorclip[rw_x_cur] - 1
                if mid >= yl:
                    r_draw.dc_yl         = yl
                    r_draw.dc_yh         = mid
                    r_draw.dc_texturemid = rw_toptexturemid
                    r_draw.dc_source     = R_GetColumn(toptexture, texturecol)
                    r_main.colfunc()
                    r_plane.ceilingclip[rw_x_cur] = mid
                else:
                    r_plane.ceilingclip[rw_x_cur] = yl - 1
            else:
                if markceiling:
                    r_plane.ceilingclip[rw_x_cur] = yl - 1

            # bottom texture
            if bottomtexture:
                mid = (pixlow + HEIGHTUNIT - 1) >> HEIGHTBITS
                if mid <= r_plane.ceilingclip[rw_x_cur]:
                    mid = r_plane.ceilingclip[rw_x_cur] + 1
                if mid <= yh:
                    r_draw.dc_yl         = mid
                    r_draw.dc_yh         = yh
                    r_draw.dc_texturemid = rw_bottomtexturemid
                    r_draw.dc_source     = R_GetColumn(bottomtexture, texturecol)
                    r_main.colfunc()
                    r_plane.floorclip[rw_x_cur] = mid
                else:
                    r_plane.floorclip[rw_x_cur] = yh + 1
            else:
                if markfloor:
                    r_plane.floorclip[rw_x_cur] = yh + 1

            if maskedtexture:
                maskedtexturecol[rw_x_cur] = texturecol

        rw_scale   += rw_scalestep
        topfrac    += topstep
        bottomfrac += bottomstep
        # step pixhigh/pixlow per column
        if toptexture:
            _step_pixhigh()
        if bottomtexture:
            _step_pixlow()


# mutable containers for pixhigh/pixlow (modified inside loop)
_pixhigh_val  = [0]
_pixlow_val   = [0]

def _step_pixhigh():
    global pixhigh
    pixhigh += pixhighstep

def _step_pixlow():
    global pixlow
    pixlow += pixlowstep


# ------------------------------------------------------------------
# R_StoreWallRange
# ------------------------------------------------------------------
def R_StoreWallRange(start: int, stop: int):
    global segtextured, markfloor, markceiling, maskedtexture
    global toptexture, bottomtexture, midtexture
    global rw_normalangle, rw_angle1, rw_x, rw_stopx
    global rw_centerangle, rw_offset, rw_distance
    global rw_scale, rw_scalestep
    global rw_midtexturemid, rw_toptexturemid, rw_bottomtexturemid
    global worldtop, worldbottom, worldhigh, worldlow
    global pixhigh, pixlow, pixhighstep, pixlowstep
    global topfrac, topstep, bottomfrac, bottomstep
    global walllights, maskedtexturecol

    import r_bsp, r_main, r_plane
    import doomstat
    from r_data import texturetranslation, textureheight as _texheight

    if r_bsp.ds_p >= MAXDRAWSEGS:
        return

    ds = r_bsp.drawsegs[r_bsp.ds_p]

    sidedef  = r_bsp.curline.sidedef
    linedef_ = r_bsp.curline.linedef
    linedef_.flags |= ML_MAPPED

    # --- distance ---
    rw_normalangle = (r_bsp.curline.angle + ANG90) & 0xFFFFFFFF
    offsetangle    = abs(int(rw_normalangle) - int(r_bsp.rw_angle1))
    if offsetangle > ANG90:
        offsetangle = ANG90

    distangle = (ANG90 - offsetangle) & 0xFFFFFFFF
    hyp       = r_main.R_PointToDist(r_bsp.curline.v1.x, r_bsp.curline.v1.y)
    sineval   = finesine[(distangle >> ANGLETOFINESHIFT) & 0x1FFF]
    rw_distance = fixed_mul(hyp, sineval)

    ds.x1      = start
    ds.x2      = stop
    ds.curline = r_bsp.curline
    rw_x       = start
    rw_stopx   = stop + 1

    # --- scales ---
    ds.scale1 = rw_scale = r_main.R_ScaleFromGlobalAngle(
        (r_main.viewangle + r_main.xtoviewangle[start]) & 0xFFFFFFFF)

    if stop > start:
        ds.scale2    = r_main.R_ScaleFromGlobalAngle(
            (r_main.viewangle + r_main.xtoviewangle[stop]) & 0xFFFFFFFF)
        ds.scalestep = rw_scalestep = (ds.scale2 - rw_scale) // (stop - start)
    else:
        ds.scale2    = ds.scale1
        rw_scalestep = 0
    ds.scalestep = rw_scalestep

    # --- texture boundaries ---
    worldtop    = r_bsp.frontsector.ceilingheight - r_main.viewz
    worldbottom = r_bsp.frontsector.floorheight   - r_main.viewz

    midtexture = toptexture = bottomtexture = 0
    maskedtexture = False
    ds.maskedtexturecol = None

    backsector = r_bsp.backsector

    if not backsector:
        # single-sided
        midtexture = texturetranslation[sidedef.midtexture]
        markfloor = markceiling = True

        if linedef_.flags & ML_DONTPEGBOTTOM:
            vtop = r_bsp.frontsector.floorheight + _texheight[sidedef.midtexture]
            rw_midtexturemid = vtop - r_main.viewz
        else:
            rw_midtexturemid = worldtop
        rw_midtexturemid += sidedef.rowoffset

        ds.silhouette     = SIL_BOTH
        ds.sprtopclip     = screenheightarray
        ds.sprbottomclip  = negonearray
        ds.bsilheight     = INT_MAX
        ds.tsilheight     = INT_MIN
    else:
        # two-sided
        ds.sprtopclip = ds.sprbottomclip = None
        ds.silhouette = SIL_NONE

        if r_bsp.frontsector.floorheight > backsector.floorheight:
            ds.silhouette |= SIL_BOTTOM
            ds.bsilheight  = r_bsp.frontsector.floorheight
        elif backsector.floorheight > r_main.viewz:
            ds.silhouette |= SIL_BOTTOM
            ds.bsilheight  = INT_MAX

        if r_bsp.frontsector.ceilingheight < backsector.ceilingheight:
            ds.silhouette |= SIL_TOP
            ds.tsilheight  = r_bsp.frontsector.ceilingheight
        elif backsector.ceilingheight < r_main.viewz:
            ds.silhouette |= SIL_TOP
            ds.tsilheight  = INT_MIN

        if backsector.ceilingheight <= r_bsp.frontsector.floorheight:
            ds.sprbottomclip = negonearray
            ds.bsilheight    = INT_MAX
            ds.silhouette   |= SIL_BOTTOM

        if backsector.floorheight >= r_bsp.frontsector.ceilingheight:
            ds.sprtopclip  = screenheightarray
            ds.tsilheight  = INT_MIN
            ds.silhouette |= SIL_TOP

        worldhigh = backsector.ceilingheight - r_main.viewz
        worldlow  = backsector.floorheight   - r_main.viewz

        # outdoor sky hack
        if (r_bsp.frontsector.ceilingpic == doomstat.skyflatnum and
                backsector.ceilingpic == doomstat.skyflatnum):
            worldtop = worldhigh

        markfloor = (worldlow != worldbottom or
                     backsector.floorpic   != r_bsp.frontsector.floorpic or
                     backsector.lightlevel != r_bsp.frontsector.lightlevel)

        markceiling = (worldhigh != worldtop or
                       backsector.ceilingpic  != r_bsp.frontsector.ceilingpic or
                       backsector.lightlevel  != r_bsp.frontsector.lightlevel)

        if (backsector.ceilingheight <= r_bsp.frontsector.floorheight or
                backsector.floorheight >= r_bsp.frontsector.ceilingheight):
            markceiling = markfloor = True

        if worldhigh < worldtop:
            toptexture = texturetranslation[sidedef.toptexture]
            if linedef_.flags & ML_DONTPEGTOP:
                rw_toptexturemid = worldtop
            else:
                vtop = backsector.ceilingheight + _texheight[sidedef.toptexture]
                rw_toptexturemid = vtop - r_main.viewz

        if worldlow > worldbottom:
            bottomtexture = texturetranslation[sidedef.bottomtexture]
            if linedef_.flags & ML_DONTPEGBOTTOM:
                rw_bottomtexturemid = worldtop
            else:
                rw_bottomtexturemid = worldlow

        rw_toptexturemid    += sidedef.rowoffset
        rw_bottomtexturemid += sidedef.rowoffset

        if sidedef.midtexture:
            maskedtexture = True
            # allocate from openings pool
            pool_start = r_plane.lastopening
            r_plane.lastopening += rw_stopx - rw_x
            # initialise SHRT_MAX sentinels
            for _i in range(rw_stopx - rw_x):
                r_plane.openings[pool_start + _i] = SHRT_MAX
            # maskedtexturecol is a view into openings offset by -rw_x
            maskedtexturecol = r_plane.openings
            ds.maskedtexturecol = (pool_start, rw_x)  # (pool_base, x_offset)

    # --- texture offset ---
    segtextured = bool(midtexture | toptexture | bottomtexture | maskedtexture)

    if segtextured:
        oa = (int(rw_normalangle) - int(r_bsp.rw_angle1)) & 0xFFFFFFFF
        if oa > ANG180:
            oa = (-oa) & 0xFFFFFFFF
        if oa > ANG90:
            oa = ANG90

        sineval  = finesine[(oa >> ANGLETOFINESHIFT) & 0x1FFF]
        rw_offset = fixed_mul(hyp, sineval)

        if ((int(rw_normalangle) - int(r_bsp.rw_angle1)) & 0xFFFFFFFF) < ANG180:
            rw_offset = -rw_offset

        rw_offset     += sidedef.textureoffset + r_bsp.curline.offset
        rw_centerangle = (ANG90 + r_main.viewangle - rw_normalangle) & 0xFFFFFFFF

        if not r_main.fixedcolormap:
            lightnum = (r_bsp.frontsector.lightlevel >> LIGHTSEGSHIFT) + r_main.extralight
            if r_bsp.curline.v1.y == r_bsp.curline.v2.y:
                lightnum -= 1
            elif r_bsp.curline.v1.x == r_bsp.curline.v2.x:
                lightnum += 1
            lightnum = max(0, min(lightnum, LIGHTLEVELS - 1))
            walllights = r_main.scalelight[lightnum]
        else:
            walllights = r_main.scalelightfixed

    # --- floor/ceiling visibility culling ---
    if r_bsp.frontsector.floorheight >= r_main.viewz:
        markfloor = False
    if (r_bsp.frontsector.ceilingheight <= r_main.viewz and
            r_bsp.frontsector.ceilingpic != doomstat.skyflatnum):
        markceiling = False

    # --- stepping values ---
    wt = worldtop    >> 4
    wb = worldbottom >> 4

    topstep    = -fixed_mul(rw_scalestep, wt)
    topfrac    = (r_main.centeryfrac >> 4) - fixed_mul(wt, rw_scale)
    bottomstep = -fixed_mul(rw_scalestep, wb)
    bottomfrac = (r_main.centeryfrac >> 4) - fixed_mul(wb, rw_scale)

    if backsector:
        wh = worldhigh >> 4
        wl = worldlow  >> 4
        if worldhigh < worldtop:
            pixhigh     = (r_main.centeryfrac >> 4) - fixed_mul(wh, rw_scale)
            pixhighstep = -fixed_mul(rw_scalestep, wh)
        if worldlow > worldbottom:
            pixlow     = (r_main.centeryfrac >> 4) - fixed_mul(wl, rw_scale)
            pixlowstep = -fixed_mul(rw_scalestep, wl)

    # --- plane reservation ---
    if markceiling and r_bsp.ceilingplane:
        r_bsp.ceilingplane = r_plane.R_CheckPlane(r_bsp.ceilingplane, rw_x, rw_stopx - 1)
    if markfloor and r_bsp.floorplane:
        r_bsp.floorplane = r_plane.R_CheckPlane(r_bsp.floorplane, rw_x, rw_stopx - 1)

    R_RenderSegLoop()

    # --- save sprite clip info ---
    if ((ds.silhouette & SIL_TOP) or maskedtexture) and not ds.sprtopclip:
        base = r_plane.lastopening
        for _i in range(rw_stopx - start):
            r_plane.openings[base + _i] = r_plane.ceilingclip[start + _i]
        r_plane.lastopening += rw_stopx - start
        ds.sprtopclip = (base, start)

    if ((ds.silhouette & SIL_BOTTOM) or maskedtexture) and not ds.sprbottomclip:
        base = r_plane.lastopening
        for _i in range(rw_stopx - start):
            r_plane.openings[base + _i] = r_plane.floorclip[start + _i]
        r_plane.lastopening += rw_stopx - start
        ds.sprbottomclip = (base, start)

    if maskedtexture and not (ds.silhouette & SIL_TOP):
        ds.silhouette |= SIL_TOP
        ds.tsilheight  = INT_MIN
    if maskedtexture and not (ds.silhouette & SIL_BOTTOM):
        ds.silhouette |= SIL_BOTTOM
        ds.bsilheight  = INT_MAX

    r_bsp.ds_p += 1


# ------------------------------------------------------------------
# R_RenderMaskedSegRange  (called from r_things during R_DrawSprite)
# ------------------------------------------------------------------
def R_RenderMaskedSegRange(ds: DrawSeg, x1: int, x2: int):
    import r_draw, r_main
    from r_data import texturetranslation, textureheight as _th, R_GetColumn

    curline = ds.curline
    import r_bsp
    r_bsp.curline    = curline
    r_bsp.frontsector = curline.frontsector
    r_bsp.backsector  = curline.backsector
    texnum = texturetranslation[curline.sidedef.midtexture]

    lightnum = (curline.frontsector.lightlevel >> LIGHTSEGSHIFT) + r_main.extralight
    if curline.v1.y == curline.v2.y:
        lightnum -= 1
    elif curline.v1.x == curline.v2.x:
        lightnum += 1
    lightnum = max(0, min(lightnum, LIGHTLEVELS - 1))
    wl = r_main.scalelight[lightnum]

    # maskedtexturecol is stored as (pool_base, x_offset) tuple
    mc_base, mc_xoff = ds.maskedtexturecol

    rw_scalestep_local = ds.scalestep
    spryscale_local    = ds.scale1 + (x1 - ds.x1) * rw_scalestep_local

    # floor/ceiling clip arrays
    mfloor   = ds.sprbottomclip
    mceiling = ds.sprtopclip

    if curline.linedef.flags & ML_DONTPEGBOTTOM:
        texmid = max(curline.frontsector.floorheight, curline.backsector.floorheight)
        texmid = texmid + _th[texnum] - r_main.viewz
    else:
        texmid = min(curline.frontsector.ceilingheight, curline.backsector.ceilingheight)
        texmid = texmid - r_main.viewz
    texmid += curline.sidedef.rowoffset

    if r_main.fixedcolormap:
        r_draw.dc_colormap = r_main.fixedcolormap

    import r_things
    for dc_x in range(x1, x2 + 1):
        mc_idx = mc_base + dc_x - mc_xoff
        col = r_plane.openings[mc_idx] if 0 <= mc_idx < len(r_plane.openings) else SHRT_MAX
        if col != SHRT_MAX:
            if not r_main.fixedcolormap:
                index = spryscale_local >> LIGHTSCALESHIFT
                if index >= MAXLIGHTSCALE:
                    index = MAXLIGHTSCALE - 1
                r_draw.dc_colormap = wl[index]

            r_things.sprtopscreen = r_main.centeryfrac - fixed_mul(texmid, spryscale_local)
            r_draw.dc_iscale      = 0xFFFFFFFF // max(1, spryscale_local)
            r_draw.dc_x           = dc_x
            r_draw.dc_texturemid  = texmid

            col_data = R_GetColumn(texnum, col)
            _draw_masked_col_from_data(col_data, dc_x, mfloor, mceiling, texnum)
            r_plane.openings[mc_idx] = SHRT_MAX

        spryscale_local += rw_scalestep_local


def _draw_masked_col_from_data(col_data, dc_x, mfloor, mceiling, texnum):
    import r_things
    r_things.R_DrawMaskedColumnRaw(col_data, dc_x, mfloor, mceiling)


# ------------------------------------------------------------------
# Patch r_bsp.R_StoreWallRange now that we're loaded
# ------------------------------------------------------------------
import r_bsp as _rb
_rb.R_StoreWallRange = R_StoreWallRange

import r_plane  # ensure it's importable for references above
