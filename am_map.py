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
# DESCRIPTION:  the automap code
#

import math

# Assumed imported modules from the larger DOOM ecosystem:
from doomdef import *
from doomstat import *
from d_event import *
from m_cheat import *
from deh_main import DEH_String
import p_setup
import p_local
import v_video
import st_stuff
import w_wad
import i_timer
from tables import finecosine, finesine

# ----------------------------------------------------------------------------
# am_map.h 
# ----------------------------------------------------------------------------

AM_MSGHEADER  = (ord('a') << 24) | (ord('m') << 16)
AM_MSGENTERED = AM_MSGHEADER | (ord('e') << 8)
AM_MSGEXITED  = AM_MSGHEADER | (ord('x') << 8)

class cheatseq_t:
    def __init__(self, sequence, p):
        self.sequence = sequence
        self.p = p

cheat_amap = cheatseq_t("iddt", 0)

# ----------------------------------------------------------------------------
# Constants and Macros
# ----------------------------------------------------------------------------

INT_MAX = 2147483647

# Fixed point math equivalents
FRACBITS = 16
FRACUNIT = 1 << FRACBITS

# p_local.h geometry variables used heavily in automap logic
PLAYERRADIUS  = 16 * FRACUNIT
MAPBLOCKUNITS = 128

def FixedMul(a, b):
    return (a * b) >> FRACBITS

def FixedDiv(a, b):
    if b == 0:
        return INT_MAX if a >= 0 else -INT_MAX
    # Truncate towards zero natively
    return int((a << FRACBITS) / b)

REDS         = (256 - 5 * 16)
REDRANGE     = 16
BLUES        = (256 - 4 * 16 + 8)
BLUERANGE    = 8
GREENS       = (7 * 16)
GREENRANGE   = 16
GRAYS        = (6 * 16)
GRAYSRANGE   = 16
BROWNS       = (4 * 16)
BROWNRANGE   = 16
YELLOWS      = (256 - 32 + 7)
YELLOWRANGE  = 1
BLACK        = 0
WHITE        = (256 - 47)

BACKGROUND       = BLACK
YOURCOLORS       = WHITE
YOURRANGE        = 0
WALLCOLORS       = REDS
WALLRANGE        = REDRANGE
TSWALLCOLORS     = GRAYS
TSWALLRANGE      = GRAYSRANGE
FDWALLCOLORS     = BROWNS
FDWALLRANGE      = BROWNRANGE
CDWALLCOLORS     = YELLOWS
CDWALLRANGE      = YELLOWRANGE
THINGCOLORS      = GREENS
THINGRANGE       = GREENRANGE
SECRETWALLCOLORS = WALLCOLORS
SECRETWALLRANGE  = WALLRANGE
GRIDCOLORS       = (GRAYS + GRAYSRANGE // 2)
GRIDRANGE        = 0
XHAIRCOLORS      = GRAYS

AM_NUMMARKPOINTS = 10
INITSCALEMTOF    = int(0.2 * FRACUNIT)
F_PANINC         = 4
M_ZOOMIN         = int(1.02 * FRACUNIT)
M_ZOOMOUT        = int(FRACUNIT / 1.02)

# Ensure ML_DONTDRAW is captured for lines we shouldn't map. 
# Defaults to DOOM's 16 (often defined in doomdata.h)
try:
    LINE_NEVERSEE = ML_DONTDRAW
except NameError:
    LINE_NEVERSEE = 16
    ML_DONTDRAW = 16
    ML_MAPPED = 32
    ML_SECRET = 32

# ----------------------------------------------------------------------------
# Structures
# ----------------------------------------------------------------------------

class fpoint_t:
    __slots__ = ['x', 'y']
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y

class fline_t:
    __slots__ = ['a', 'b']
    def __init__(self, a=None, b=None):
        self.a = a if a else fpoint_t()
        self.b = b if b else fpoint_t()

class mpoint_t:
    __slots__ = ['x', 'y']
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y

class mline_t:
    __slots__ = ['a', 'b']
    def __init__(self, a=None, b=None):
        self.a = a if a else mpoint_t()
        self.b = b if b else mpoint_t()

class islope_t:
    __slots__ = ['slp', 'islp']
    def __init__(self, slp=0, islp=0):
        self.slp, self.islp = slp, islp

def make_mlines(coords):
    return [mline_t(mpoint_t(int(ax), int(ay)), mpoint_t(int(bx), int(by))) for (ax, ay), (bx, by) in coords]

R = (8 * PLAYERRADIUS) // 7
player_arrow = make_mlines([
    ((-R + R // 8, 0), (R, 0)),
    ((R, 0), (R - R // 2, R // 4)),
    ((R, 0), (R - R // 2, -R // 4)),
    ((-R + R // 8, 0), (-R - R // 8, R // 4)),
    ((-R + R // 8, 0), (-R - R // 8, -R // 4)),
    ((-R + 3 * R // 8, 0), (-R + R // 8, R // 4)),
    ((-R + 3 * R // 8, 0), (-R + R // 8, -R // 4))
])

cheat_player_arrow = make_mlines([
    ((-R + R // 8, 0), (R, 0)),
    ((R, 0), (R - R // 2, R // 6)),
    ((R, 0), (R - R // 2, -R // 6)),
    ((-R + R // 8, 0), (-R - R // 8, R // 6)),
    ((-R + R // 8, 0), (-R - R // 8, -R // 6)),
    ((-R + 3 * R // 8, 0), (-R + R // 8, R // 6)),
    ((-R + 3 * R // 8, 0), (-R + R // 8, -R // 6)),
    ((-R // 2, 0), (-R // 2, -R // 6)),
    ((-R // 2, -R // 6), (-R // 2 + R // 6, -R // 6)),
    ((-R // 2 + R // 6, -R // 6), (-R // 2 + R // 6, R // 4)),
    ((-R // 6, 0), (-R // 6, -R // 6)),
    ((-R // 6, -R // 6), (0, -R // 6)),
    ((0, -R // 6), (0, R // 4)),
    ((R // 6, R // 4), (R // 6, -R // 7)),
    ((R // 6, -R // 7), (R // 6 + R // 32, -R // 7 - R // 32)),
    ((R // 6 + R // 32, -R // 7 - R // 32), (R // 6 + R // 10, -R // 7))
])

R = FRACUNIT
triangle_guy = make_mlines([
    ((-0.867 * R, -0.5 * R), (0.867 * R, -0.5 * R)),
    ((0.867 * R, -0.5 * R), (0, R)),
    ((0, R), (-0.867 * R, -0.5 * R))
])

thintriangle_guy = make_mlines([
    ((-0.5 * R, -0.7 * R), (R, 0)),
    ((R, 0), (-0.5 * R, 0.7 * R)),
    ((-0.5 * R, 0.7 * R), (-0.5 * R, -0.7 * R))
])

# ----------------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------------

cheating      = 0
grid          = 0
automapactive = False
finit_width   = SCREENWIDTH
finit_height  = SCREENHEIGHT - st_stuff.ST_HEIGHT

f_x = f_y = f_w = f_h = 0
lightlev = 0
fb       = None
amclock  = 0

m_paninc     = mpoint_t(0, 0)
mtof_zoommul = FRACUNIT
ftom_zoommul = FRACUNIT

m_x = m_y = m_x2 = m_y2 = 0
m_w = m_h = 0

min_x = min_y = max_x = max_y = 0
max_w = max_h = min_w = min_h = 0
min_scale_mtof = max_scale_mtof = 0

old_m_w = old_m_h = old_m_x = old_m_y = 0
f_oldloc = mpoint_t(0, 0)

scale_mtof = INITSCALEMTOF
scale_ftom = 0

plr          = None
marknums     = [None] * 10
markpoints   = [mpoint_t(-1, 0) for _ in range(AM_NUMMARKPOINTS)]
markpointnum = 0
followplayer = 1
stopped      = True

# Function-locals carrying static-state
_bigstate = 0
_lastlevel = -1
_lastepisode = -1


# ----------------------------------------------------------------------------
# Core coordinate translation helpers
# ----------------------------------------------------------------------------

def FTOM(x): return FixedMul(x << FRACBITS, scale_ftom)
def MTOF(x): return FixedMul(x, scale_mtof) >> FRACBITS
def CXMTOF(x): return f_x + MTOF(x - m_x)
def CYMTOF(y): return f_y + (f_h - MTOF(y - m_y))


def AM_getIslope(ml, is_obj):
    dy = ml.a.y - ml.b.y
    dx = ml.b.x - ml.a.x
    if not dy:
        is_obj.islp = -INT_MAX if dx < 0 else INT_MAX
    else:
        is_obj.islp = FixedDiv(dx, dy)
        
    if not dx:
        is_obj.slp = -INT_MAX if dy < 0 else INT_MAX
    else:
        is_obj.slp = FixedDiv(dy, dx)


def AM_activateNewScale():
    global m_x, m_y, m_w, m_h, m_x2, m_y2
    m_x += m_w // 2
    m_y += m_h // 2
    m_w = FTOM(f_w)
    m_h = FTOM(f_h)
    m_x -= m_w // 2
    m_y -= m_h // 2
    m_x2 = m_x + m_w
    m_y2 = m_y + m_h

def AM_saveScaleAndLoc():
    global old_m_x, old_m_y, old_m_w, old_m_h
    old_m_x, old_m_y = m_x, m_y
    old_m_w, old_m_h = m_w, m_h

def AM_restoreScaleAndLoc():
    global m_w, m_h, m_x, m_y, m_x2, m_y2, scale_mtof, scale_ftom
    m_w = old_m_w
    m_h = old_m_h
    
    if not followplayer:
        m_x = old_m_x
        m_y = old_m_y
    else:
        m_x = plr.mo.x - m_w // 2
        m_y = plr.mo.y - m_h // 2
        
    m_x2 = m_x + m_w
    m_y2 = m_y + m_h
    
    scale_mtof = FixedDiv(f_w << FRACBITS, m_w)
    scale_ftom = FixedDiv(FRACUNIT, scale_mtof)

def AM_addMark():
    global markpointnum
    markpoints[markpointnum].x = m_x + m_w // 2
    markpoints[markpointnum].y = m_y + m_h // 2
    markpointnum = (markpointnum + 1) % AM_NUMMARKPOINTS

def AM_findMinMaxBoundaries():
    global min_x, min_y, max_x, max_y, max_w, max_h, min_w, min_h
    global min_scale_mtof, max_scale_mtof
    
    min_x = min_y = INT_MAX
    max_x = max_y = -INT_MAX
    
    for i in range(p_setup.numvertexes):
        vx = p_setup.vertexes[i].x
        vy = p_setup.vertexes[i].y
        if vx < min_x: min_x = vx
        elif vx > max_x: max_x = vx
        if vy < min_y: min_y = vy
        elif vy > max_y: max_y = vy
        
    max_w = max_x - min_x
    max_h = max_y - min_y
    
    min_w = 2 * PLAYERRADIUS
    min_h = 2 * PLAYERRADIUS
    
    a = FixedDiv(f_w << FRACBITS, max_w)
    b = FixedDiv(f_h << FRACBITS, max_h)
    
    min_scale_mtof = a if a < b else b
    max_scale_mtof = FixedDiv(f_h << FRACBITS, 2 * PLAYERRADIUS)

def AM_changeWindowLoc():
    global followplayer, f_oldloc, m_x, m_y, m_x2, m_y2
    
    if m_paninc.x or m_paninc.y:
        followplayer = 0
        f_oldloc.x = INT_MAX
        
    m_x += m_paninc.x
    m_y += m_paninc.y
    
    if m_x + m_w // 2 > max_x:
        m_x = max_x - m_w // 2
    elif m_x + m_w // 2 < min_x:
        m_x = min_x - m_w // 2
        
    if m_y + m_h // 2 > max_y:
        m_y = max_y - m_h // 2
    elif m_y + m_h // 2 < min_y:
        m_y = min_y - m_h // 2
        
    m_x2 = m_x + m_w
    m_y2 = m_y + m_h

def AM_initVariables():
    global automapactive, fb, f_oldloc, amclock, lightlev
    global m_paninc, ftom_zoommul, mtof_zoommul, m_w, m_h
    global plr, m_x, m_y, old_m_x, old_m_y, old_m_w, old_m_h
    
    automapactive = True
    fb = v_video.I_VideoBuffer
    
    f_oldloc.x = INT_MAX
    amclock = 0
    lightlev = 0
    
    m_paninc.x = m_paninc.y = 0
    ftom_zoommul = FRACUNIT
    mtof_zoommul = FRACUNIT
    
    m_w = FTOM(f_w)
    m_h = FTOM(f_h)
    
    if playeringame[consoleplayer]:
        plr = players[consoleplayer]
    else:
        plr = players[0]
        for pnum in range(MAXPLAYERS):
            if playeringame[pnum]:
                plr = players[pnum]
                break
                
    m_x = plr.mo.x - m_w // 2
    m_y = plr.mo.y - m_h // 2
    AM_changeWindowLoc()
    
    old_m_x = m_x
    old_m_y = m_y
    old_m_w = m_w
    old_m_h = m_h
    
    st_notify = event_t()
    st_notify.type = ev_keyup
    st_notify.data1 = AM_MSGENTERED
    st_stuff.ST_Responder(st_notify)

def AM_loadPics():
    for i in range(10):
        namebuf = f"AMMNUM{i}"
        marknums[i] = w_wad.W_CacheLumpName(DEH_String(namebuf), PU_STATIC)

def AM_unloadPics():
    for i in range(10):
        namebuf = f"AMMNUM{i}"
        w_wad.W_ReleaseLumpName(DEH_String(namebuf))

def AM_clearMarks():
    global markpointnum
    for i in range(AM_NUMMARKPOINTS):
        markpoints[i].x = -1
    markpointnum = 0

def AM_LevelInit():
    global f_x, f_y, f_w, f_h, scale_mtof, scale_ftom
    f_x = f_y = 0
    f_w = finit_width
    f_h = finit_height
    
    AM_clearMarks()
    AM_findMinMaxBoundaries()
    
    scale_mtof = FixedDiv(min_scale_mtof, int(0.7 * FRACUNIT))
    if scale_mtof > max_scale_mtof:
        scale_mtof = min_scale_mtof
    scale_ftom = FixedDiv(FRACUNIT, scale_mtof)

def AM_Stop():
    global automapactive, stopped
    AM_unloadPics()
    automapactive = False
    st_notify = event_t()
    st_notify.type = ev_keyup
    st_notify.data1 = AM_MSGEXITED
    st_stuff.ST_Responder(st_notify)
    stopped = True

def AM_Start():
    global stopped, _lastlevel, _lastepisode
    if not stopped:
        AM_Stop()
    stopped = False
    
    if _lastlevel != gamemap or _lastepisode != gameepisode:
        AM_LevelInit()
        _lastlevel = gamemap
        _lastepisode = gameepisode
        
    AM_initVariables()
    AM_loadPics()

def AM_minOutWindowScale():
    global scale_mtof, scale_ftom
    scale_mtof = min_scale_mtof
    scale_ftom = FixedDiv(FRACUNIT, scale_mtof)
    AM_activateNewScale()

def AM_maxOutWindowScale():
    global scale_mtof, scale_ftom
    scale_mtof = max_scale_mtof
    scale_ftom = FixedDiv(FRACUNIT, scale_mtof)
    AM_activateNewScale()

def AM_Responder(ev):
    global automapactive, viewactive, cheating, followplayer, grid
    global m_paninc, mtof_zoommul, ftom_zoommul, joywait, _bigstate
    
    rc = False
    
    if ev.type == ev_joystick and joybautomap >= 0 and (ev.data1 & (1 << joybautomap)) != 0:
        joywait = i_timer.I_GetTime() + 5
        if not automapactive:
            AM_Start()
            viewactive = False
        else:
            _bigstate = 0
            viewactive = True
            AM_Stop()
        return True
        
    if not automapactive:
        if ev.type == ev_keydown and ev.data1 == key_map_toggle:
            AM_Start()
            viewactive = False
            rc = True
            
    elif ev.type == ev_keydown:
        rc = True
        key = ev.data1
        
        if key == key_map_east:
            if not followplayer: m_paninc.x = FTOM(F_PANINC)
            else: rc = False
        elif key == key_map_west:
            if not followplayer: m_paninc.x = -FTOM(F_PANINC)
            else: rc = False
        elif key == key_map_north:
            if not followplayer: m_paninc.y = FTOM(F_PANINC)
            else: rc = False
        elif key == key_map_south:
            if not followplayer: m_paninc.y = -FTOM(F_PANINC)
            else: rc = False
        elif key == key_map_zoomout:
            mtof_zoommul = M_ZOOMOUT
            ftom_zoommul = M_ZOOMIN
        elif key == key_map_zoomin:
            mtof_zoommul = M_ZOOMIN
            ftom_zoommul = M_ZOOMOUT
        elif key == key_map_toggle:
            _bigstate = 0
            viewactive = True
            AM_Stop()
        elif key == key_map_maxzoom:
            _bigstate = not _bigstate
            if _bigstate:
                AM_saveScaleAndLoc()
                AM_minOutWindowScale()
            else:
                AM_restoreScaleAndLoc()
        elif key == key_map_follow:
            followplayer = not followplayer
            f_oldloc.x = INT_MAX
            plr.message = DEH_String(AMSTR_FOLLOWON if followplayer else AMSTR_FOLLOWOFF)
        elif key == key_map_grid:
            grid = not grid
            plr.message = DEH_String(AMSTR_GRIDON if grid else AMSTR_GRIDOFF)
        elif key == key_map_mark:
            plr.message = f"{DEH_String(AMSTR_MARKEDSPOT)} {markpointnum}"
            AM_addMark()
        elif key == key_map_clearmark:
            AM_clearMarks()
            plr.message = DEH_String(AMSTR_MARKSCLEARED)
        else:
            rc = False
            
        if (not deathmatch or gameversion <= exe_doom_1_8) and cht_CheckCheat(cheat_amap, ev.data2):
            rc = False
            cheating = (cheating + 1) % 3
            
    elif ev.type == ev_keyup:
        rc = False
        key = ev.data1
        if key == key_map_east and not followplayer: m_paninc.x = 0
        elif key == key_map_west and not followplayer: m_paninc.x = 0
        elif key == key_map_north and not followplayer: m_paninc.y = 0
        elif key == key_map_south and not followplayer: m_paninc.y = 0
        elif key == key_map_zoomout or key == key_map_zoomin:
            mtof_zoommul = FRACUNIT
            ftom_zoommul = FRACUNIT
            
    return rc

def AM_changeWindowScale():
    global scale_mtof, scale_ftom
    scale_mtof = FixedMul(scale_mtof, mtof_zoommul)
    scale_ftom = FixedDiv(FRACUNIT, scale_mtof)
    
    if scale_mtof < min_scale_mtof:
        AM_minOutWindowScale()
    elif scale_mtof > max_scale_mtof:
        AM_maxOutWindowScale()
    else:
        AM_activateNewScale()

def AM_doFollowPlayer():
    global m_x, m_y, m_x2, m_y2, f_oldloc
    if f_oldloc.x != plr.mo.x or f_oldloc.y != plr.mo.y:
        m_x = FTOM(MTOF(plr.mo.x)) - m_w // 2
        m_y = FTOM(MTOF(plr.mo.y)) - m_h // 2
        m_x2 = m_x + m_w
        m_y2 = m_y + m_h
        f_oldloc.x = plr.mo.x
        f_oldloc.y = plr.mo.y

def AM_updateLightLev():
    global lightlev, amclock
    pass

def AM_Ticker():
    global amclock
    if not automapactive:
        return
    amclock += 1
    if followplayer:
        AM_doFollowPlayer()
    if ftom_zoommul != FRACUNIT:
        AM_changeWindowScale()
    if m_paninc.x or m_paninc.y:
        AM_changeWindowLoc()

def AM_clearFB(color):
    if fb is not None:
        for i in range(f_w * f_h):
            fb[i] = color

def AM_clipMline(ml, fl):
    LEFT, RIGHT, BOTTOM, TOP = 1, 2, 4, 8
    
    def DOOUTCODE(mx, my):
        oc = 0
        if my < 0: oc |= TOP
        elif my >= f_h: oc |= BOTTOM
        if mx < 0: oc |= LEFT
        elif mx >= f_w: oc |= RIGHT
        return oc
        
    outcode1 = TOP if ml.a.y > m_y2 else (BOTTOM if ml.a.y < m_y else 0)
    outcode2 = TOP if ml.b.y > m_y2 else (BOTTOM if ml.b.y < m_y else 0)
    
    if outcode1 & outcode2: return False
    
    if ml.a.x < m_x: outcode1 |= LEFT
    elif ml.a.x > m_x2: outcode1 |= RIGHT
    if ml.b.x < m_x: outcode2 |= LEFT
    elif ml.b.x > m_x2: outcode2 |= RIGHT
    
    if outcode1 & outcode2: return False
    
    fl.a.x = CXMTOF(ml.a.x)
    fl.a.y = CYMTOF(ml.a.y)
    fl.b.x = CXMTOF(ml.b.x)
    fl.b.y = CYMTOF(ml.b.y)
    
    outcode1 = DOOUTCODE(fl.a.x, fl.a.y)
    outcode2 = DOOUTCODE(fl.b.x, fl.b.y)
    
    if outcode1 & outcode2: return False
    
    while outcode1 | outcode2:
        outside = outcode1 if outcode1 else outcode2
        
        if outside & TOP:
            dy = fl.a.y - fl.b.y
            dx = fl.b.x - fl.a.x
            tmpx = fl.a.x + int((dx * fl.a.y) / dy)
            tmpy = 0
        elif outside & BOTTOM:
            dy = fl.a.y - fl.b.y
            dx = fl.b.x - fl.a.x
            tmpx = fl.a.x + int((dx * (fl.a.y - f_h)) / dy)
            tmpy = f_h - 1
        elif outside & RIGHT:
            dy = fl.b.y - fl.a.y
            dx = fl.b.x - fl.a.x
            tmpy = fl.a.y + int((dy * (f_w - 1 - fl.a.x)) / dx)
            tmpx = f_w - 1
        elif outside & LEFT:
            dy = fl.b.y - fl.a.y
            dx = fl.b.x - fl.a.x
            tmpy = fl.a.y + int((dy * (-fl.a.x)) / dx)
            tmpx = 0
        else:
            tmpx = tmpy = 0
            
        if outside == outcode1:
            fl.a.x, fl.a.y = tmpx, tmpy
            outcode1 = DOOUTCODE(fl.a.x, fl.a.y)
        else:
            fl.b.x, fl.b.y = tmpx, tmpy
            outcode2 = DOOUTCODE(fl.b.x, fl.b.y)
            
        if outcode1 & outcode2: return False
        
    return True

def AM_drawFline(fl, color):
    if (fl.a.x < 0 or fl.a.x >= f_w or fl.a.y < 0 or fl.a.y >= f_h or
        fl.b.x < 0 or fl.b.x >= f_w or fl.b.y < 0 or fl.b.y >= f_h):
        return
        
    dx = fl.b.x - fl.a.x
    ax = 2 * (-dx if dx < 0 else dx)
    sx = -1 if dx < 0 else 1
    
    dy = fl.b.y - fl.a.y
    ay = 2 * (-dy if dy < 0 else dy)
    sy = -1 if dy < 0 else 1
    
    x = fl.a.x
    y = fl.a.y
    
    if ax > ay:
        d = ay - ax // 2
        while True:
            fb[y * f_w + x] = color
            if x == fl.b.x: return
            if d >= 0:
                y += sy
                d -= ax
            x += sx
            d += ay
    else:
        d = ax - ay // 2
        while True:
            fb[y * f_w + x] = color
            if y == fl.b.y: return
            if d >= 0:
                x += sx
                d -= ay
            y += sy
            d += ax

_draw_fl = fline_t()
def AM_drawMline(ml, color):
    if AM_clipMline(ml, _draw_fl):
        AM_drawFline(_draw_fl, color)

def AM_drawGrid(color):
    ml = mline_t()
    
    start = m_x
    rem = int(math.fmod(start - p_setup.bmaporgx, MAPBLOCKUNITS << FRACBITS))
    if rem: start += (MAPBLOCKUNITS << FRACBITS) - rem
    end = m_x + m_w
    
    ml.a.y = m_y
    ml.b.y = m_y + m_h
    x = start
    while x < end:
        ml.a.x = ml.b.x = x
        AM_drawMline(ml, color)
        x += (MAPBLOCKUNITS << FRACBITS)
        
    start = m_y
    rem = int(math.fmod(start - p_setup.bmaporgy, MAPBLOCKUNITS << FRACBITS))
    if rem: start += (MAPBLOCKUNITS << FRACBITS) - rem
    end = m_y + m_h
    
    ml.a.x = m_x
    ml.b.x = m_x + m_w
    y = start
    while y < end:
        ml.a.y = ml.b.y = y
        AM_drawMline(ml, color)
        y += (MAPBLOCKUNITS << FRACBITS)

_wall_ml = mline_t()
def AM_drawWalls():
    try:
        pw_allmap = 5  # Standard p_local.h constant for allmap powerup index
    except NameError:
        pw_allmap = 5

    for i in range(p_setup.numlines):
        line = p_setup.lines[i]
        _wall_ml.a.x = line.v1.x
        _wall_ml.a.y = line.v1.y
        _wall_ml.b.x = line.v2.x
        _wall_ml.b.y = line.v2.y
        
        if cheating or (line.flags & ML_MAPPED):
            if (line.flags & LINE_NEVERSEE) and not cheating:
                continue
            if not line.backsector:
                AM_drawMline(_wall_ml, WALLCOLORS + lightlev)
            else:
                if line.special == 39:
                    AM_drawMline(_wall_ml, WALLCOLORS + WALLRANGE // 2)
                elif line.flags & ML_SECRET:
                    AM_drawMline(_wall_ml, SECRETWALLCOLORS + lightlev if cheating else WALLCOLORS + lightlev)
                elif line.backsector.floorheight != line.frontsector.floorheight:
                    AM_drawMline(_wall_ml, FDWALLCOLORS + lightlev)
                elif line.backsector.ceilingheight != line.frontsector.ceilingheight:
                    AM_drawMline(_wall_ml, CDWALLCOLORS + lightlev)
                elif cheating:
                    AM_drawMline(_wall_ml, TSWALLCOLORS + lightlev)
        elif plr.powers[pw_allmap]:
            if not (line.flags & LINE_NEVERSEE):
                AM_drawMline(_wall_ml, GRAYS + 3)

def AM_rotate(x, y, a):
    idx = a >> ANGLETOFINESHIFT
    c = finecosine[idx]
    s = finesine[idx]
    tmpx = FixedMul(x, c) - FixedMul(y, s)
    tmpy = FixedMul(x, s) + FixedMul(y, c)
    return tmpx, tmpy

_char_ml = mline_t()
def AM_drawLineCharacter(lineguy, scale, angle, color, x, y):
    for line in lineguy:
        lax, lay = line.a.x, line.a.y
        if scale:
            lax, lay = FixedMul(scale, lax), FixedMul(scale, lay)
        if angle:
            lax, lay = AM_rotate(lax, lay, angle)
        lax += x
        lay += y
        
        lbx, lby = line.b.x, line.b.y
        if scale:
            lbx, lby = FixedMul(scale, lbx), FixedMul(scale, lby)
        if angle:
            lbx, lby = AM_rotate(lbx, lby, angle)
        lbx += x
        lby += y
        
        _char_ml.a.x, _char_ml.a.y = lax, lay
        _char_ml.b.x, _char_ml.b.y = lbx, lby
        AM_drawMline(_char_ml, color)

def AM_drawPlayers():
    their_colors = [GREENS, GRAYS, BROWNS, REDS]
    their_color = -1
    
    try:
        pw_invisibility = 2 # Usually DOOM constant for invisibility
    except NameError:
        pw_invisibility = 2

    if not netgame:
        if cheating:
            AM_drawLineCharacter(cheat_player_arrow, 0, plr.mo.angle, WHITE, plr.mo.x, plr.mo.y)
        else:
            AM_drawLineCharacter(player_arrow, 0, plr.mo.angle, WHITE, plr.mo.x, plr.mo.y)
        return
        
    for i in range(MAXPLAYERS):
        their_color += 1
        p = players[i]
        
        if (deathmatch and not singledemo) and p != plr:
            continue
        if not playeringame[i]:
            continue
            
        color = 246 if p.powers[pw_invisibility] else their_colors[their_color]
        AM_drawLineCharacter(player_arrow, 0, p.mo.angle, color, p.mo.x, p.mo.y)

def AM_drawThings(colors, colorrange):
    for i in range(p_setup.numsectors):
        t = p_setup.sectors[i].thinglist
        while t:
            AM_drawLineCharacter(thintriangle_guy, 16 << FRACBITS, t.angle, colors + lightlev, t.x, t.y)
            t = t.snext

def AM_drawMarks():
    w = 5
    h = 6
    for i in range(AM_NUMMARKPOINTS):
        if markpoints[i].x != -1:
            fx = CXMTOF(markpoints[i].x)
            fy = CYMTOF(markpoints[i].y)
            if fx >= f_x and fx <= f_w - w and fy >= f_y and fy <= f_h - h:
                v_video.V_DrawPatch(fx, fy, marknums[i])

def AM_drawCrosshair(color):
    if fb is not None:
        idx = (f_w * (f_h + 1)) // 2
        fb[idx] = color

def AM_Drawer():
    if not automapactive: return
    
    AM_clearFB(BACKGROUND)
    if grid: AM_drawGrid(GRIDCOLORS)
    AM_drawWalls()
    AM_drawPlayers()
    if cheating == 2: AM_drawThings(THINGCOLORS, THINGRANGE)
    AM_drawCrosshair(XHAIRCOLORS)
    AM_drawMarks()
    
    v_video.V_MarkRect(f_x, f_y, f_w, f_h)
