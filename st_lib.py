#
# Copyright(C) 1993-1996 Id Software, Inc.
# Copyright(C) 2005-2014 Simon Howard
# Copyright(C) 2025 Python Port Contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# DESCRIPTION:
#	The status bar widget code.
#

# Hack display negative frags.
# Loads and stores the stminus lump.
sttminus = None

# ----------------------------------------------------------------------------
# Helper: Resolves simulated C Pointers in Python.
# Supports functions/lambdas and single element lists.
# ----------------------------------------------------------------------------
def get_val(ptr):
    if callable(ptr):
        return ptr()
    if isinstance(ptr, list):
        return ptr[0]
    return ptr


# ----------------------------------------------------------------------------
# Struct equivalents (st_lib.h)
# ----------------------------------------------------------------------------

class st_number_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 0
        self.oldnum = 0
        self.num = None
        self.on = None
        self.p = None
        self.data = 0

class st_percent_t:
    def __init__(self):
        self.n = st_number_t()
        self.p = None

class st_multicon_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.oldinum = -1
        self.inum = None
        self.on = None
        self.p = None
        self.data = 0

class st_binicon_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.oldval = False
        self.val = None
        self.on = None
        self.p = None
        self.data = 0


# ----------------------------------------------------------------------------
# STlib General Init
# ----------------------------------------------------------------------------

def STlib_init():
    global sttminus
    from w_wad import W_CheckNumForName, W_CacheLumpName
    from z_zone import PU_STATIC
    from deh_main import DEH_String

    lump_name = DEH_String("STTMINUS")
    if W_CheckNumForName(lump_name) >= 0:
        sttminus = W_CacheLumpName(lump_name, PU_STATIC)
    else:
        sttminus = None


# ----------------------------------------------------------------------------
# Number widget routines
# ----------------------------------------------------------------------------

def STlib_initNum(n, x, y, pl, num_func, on_func, width):
    n.x = x
    n.y = y
    n.oldnum = 0
    n.width = width
    n.num = num_func
    n.on = on_func
    n.p = pl

def STlib_drawNum(n, refresh):
    import st_stuff
    import v_video

    numdigits = n.width
    num = get_val(n.num)
    
    w = n.p[0].width
    h = n.p[0].height
    x = n.x
    
    neg = num < 0
    n.oldnum = num

    if neg:
        if numdigits == 2 and num < -9:
            num = -9
        elif numdigits == 3 and num < -99:
            num = -99
        
        num = -num

    # clear the area
    x = n.x - numdigits * w

    if n.y - st_stuff.ST_Y < 0:
        raise RuntimeError("drawNum: n.y - ST_Y < 0")

    v_video.V_CopyRect(x, n.y - st_stuff.ST_Y, st_stuff.st_backing_screen, w * numdigits, h, x, n.y)

    # if non-number, do not draw it
    if num == 1994:
        return

    x = n.x

    # in the special case of 0, you draw 0
    if not num:
        v_video.V_DrawPatch(x - w, n.y, n.p[0])

    # draw the new number
    while num and numdigits > 0:
        numdigits -= 1
        x -= w
        v_video.V_DrawPatch(x, n.y, n.p[num % 10])
        num //= 10

    # draw a minus sign if necessary
    global sttminus
    if neg and sttminus:
        v_video.V_DrawPatch(x - 8, n.y, sttminus)

def STlib_updateNum(n, refresh):
    if get_val(n.on):
        STlib_drawNum(n, refresh)


# ----------------------------------------------------------------------------
# Percent widget routines
# ----------------------------------------------------------------------------

def STlib_initPercent(p, x, y, pl, num_func, on_func, percent_patch):
    STlib_initNum(p.n, x, y, pl, num_func, on_func, 3)
    p.p = percent_patch

def STlib_updatePercent(per, refresh):
    import v_video
    
    if refresh and get_val(per.n.on):
        v_video.V_DrawPatch(per.n.x, per.n.y, per.p)
    
    STlib_updateNum(per.n, refresh)


# ----------------------------------------------------------------------------
# Multiple Icon widget routines
# ----------------------------------------------------------------------------

def STlib_initMultIcon(i, x, y, il, inum_func, on_func):
    i.x = x
    i.y = y
    i.oldinum = -1
    i.inum = inum_func
    i.on = on_func
    i.p = il

def STlib_updateMultIcon(mi, refresh):
    import st_stuff
    import v_video

    on_val = get_val(mi.on)
    inum_val = get_val(mi.inum)

    if on_val and (mi.oldinum != inum_val or refresh) and (inum_val != -1):
        if mi.oldinum != -1:
            old_patch = mi.p[mi.oldinum]
            x = mi.x - old_patch.leftoffset
            y = mi.y - old_patch.topoffset
            w = old_patch.width
            h = old_patch.height

            if y - st_stuff.ST_Y < 0:
                raise RuntimeError("updateMultIcon: y - ST_Y < 0")

            v_video.V_CopyRect(x, y - st_stuff.ST_Y, st_stuff.st_backing_screen, w, h, x, y)

        v_video.V_DrawPatch(mi.x, mi.y, mi.p[inum_val])
        mi.oldinum = inum_val


# ----------------------------------------------------------------------------
# Binary Icon widget routines
# ----------------------------------------------------------------------------

def STlib_initBinIcon(b, x, y, i, val_func, on_func):
    b.x = x
    b.y = y
    b.oldval = False
    b.val = val_func
    b.on = on_func
    b.p = i

def STlib_updateBinIcon(bi, refresh):
    import st_stuff
    import v_video

    on_val = get_val(bi.on)
    val_val = get_val(bi.val)

    if on_val and (bi.oldval != val_val or refresh):
        x = bi.x - bi.p.leftoffset
        y = bi.y - bi.p.topoffset
        w = bi.p.width
        h = bi.p.height

        if y - st_stuff.ST_Y < 0:
            raise RuntimeError("updateBinIcon: y - ST_Y < 0")

        if val_val:
            v_video.V_DrawPatch(bi.x, bi.y, bi.p)
        else:
            v_video.V_CopyRect(x, y - st_stuff.ST_Y, st_stuff.st_backing_screen, w, h, x, y)

        bi.oldval = val_val
