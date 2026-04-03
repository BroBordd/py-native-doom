# wi_stuff.py
# Ported from wi_stuff.c / wi_stuff.h

import doomdef
import doomstat
import g_game
import w_wad
import v_video
import s_sound
import m_random
import deh_main
import sounds

# --- CONSTANTS ---

NUMEPISODES = 4
NUMMAPS = 9

WI_TITLEY = 2
WI_SPACINGY = 33

SP_STATSX = 50
SP_STATSY = 50
SP_TIMEX = 16
SP_TIMEY = (doomdef.SCREENHEIGHT - 32)

NG_STATSY = 50
NG_SPACINGX = 64

DM_MATRIXX = 42
DM_MATRIXY = 68
DM_SPACINGX = 40
DM_TOTALSX = 269
DM_KILLERSX = 10
DM_KILLERSY = 100
DM_VICTIMSX = 5
DM_VICTIMSY = 50

# States for single-player
SP_KILLS = 0
SP_ITEMS = 2
SP_SECRET = 4
SP_FRAGS = 6
SP_TIME = 8
SP_PAR = 8 # SP_TIME in C
SP_PAUSE = 1

SHOWNEXTLOCDELAY = 4

# --- ENUMS ---

class stateenum_t:
    NoState = -1
    StatCount = 0
    ShowNextLoc = 1

class animenum_t:
    ANIM_ALWAYS = 0
    ANIM_RANDOM = 1
    ANIM_LEVEL = 2

# --- DATA STRUCTURES ---

class point_t:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class anim_t:
    def __init__(self, type, period, nanims, x, y, nexttic, data1=0, data2=0):
        self.type = type
        self.period = period
        self.nanims = nanims
        self.loc = point_t(x, y)
        self.data1 = data1
        self.data2 = data2
        self.p = [None, None, None]
        self.nexttic = nexttic
        self.lastdrawn = 0
        self.ctr = -1
        self.state = 0

# --- HELPER MACROS ---
# In Python ports, patch dimensions are integers. We simulate the C SHORT macro.
def SHORT(val):
    return val

# --- GLOBAL VARIABLES (Static state in C) ---

state = stateenum_t.NoState
acceleratestage = 0
wbs = None
plrs = None
me = 0
cnt = 0
bcnt = 0
firstrefresh = 1
NUMCMAPS = 0

cnt_kills = [0] * doomdef.MAXPLAYERS
cnt_items = [0] * doomdef.MAXPLAYERS
cnt_secret = [0] * doomdef.MAXPLAYERS
cnt_time = 0
cnt_par = 0
cnt_pause = 0

dm_state = 0
dm_frags = [[0]*doomdef.MAXPLAYERS for _ in range(doomdef.MAXPLAYERS)]
dm_totals = [0] * doomdef.MAXPLAYERS

cnt_frags = [0] * doomdef.MAXPLAYERS
dofrags = 0
ng_state = 0
sp_state = 0
snl_pointeron = False

# Graphics
yah = [None, None, None]
splat = [None, None]
percent = None
colon = None
num = [None] * 10
wiminus = None
finished = None
entering = None
sp_secret = None
kills = None
secret = None
items = None
frags = None
timepatch = None
par = None
sucks = None
killers = None
victims = None
total = None
star = None
bstar = None
p = [None] * doomdef.MAXPLAYERS
bp = [None] * doomdef.MAXPLAYERS
lnames = []
background = None

# --- ANIMATION MAP DATA ---

lnodes = [
    [ point_t(185, 164), point_t(148, 143), point_t(69, 122), point_t(209, 102),
      point_t(116, 89), point_t(166, 55), point_t(71, 56), point_t(135, 29), point_t(71, 24) ],
    [ point_t(254, 25), point_t(97, 50), point_t(188, 64), point_t(128, 78),
      point_t(214, 92), point_t(133, 130), point_t(208, 136), point_t(148, 140), point_t(235, 158) ],
    [ point_t(156, 168), point_t(48, 154), point_t(174, 95), point_t(265, 75),
      point_t(130, 48), point_t(279, 23), point_t(198, 48), point_t(140, 25), point_t(281, 136) ],
    [ point_t(0,0) for _ in range(NUMMAPS) ] # Dummy episode 4 array
]

epsd0animinfo = [
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 224, 104, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 184, 160, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 112, 136, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 72, 112, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 88, 96, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 64, 48, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 192, 40, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 136, 16, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 80, 16, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 64, 24, 0),
]

epsd1animinfo = [
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 1, 1),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 2, 2),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 3, 3),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 4, 4),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 5, 5),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 6, 6),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 7, 7),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 3, 192, 144, 8, 8),
    anim_t(animenum_t.ANIM_LEVEL, doomdef.TICRATE//3, 1, 128, 136, 8, 8),
]

epsd2animinfo = [
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 104, 168, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 40, 136, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 160, 96, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 104, 80, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//3, 3, 120, 32, 0),
    anim_t(animenum_t.ANIM_ALWAYS, doomdef.TICRATE//4, 3, 40, 0, 0),
]

NUMANIMS = [len(epsd0animinfo), len(epsd1animinfo), len(epsd2animinfo), 0]
anims = [epsd0animinfo, epsd1animinfo, epsd2animinfo, []]

# --- LOGIC ---

def WI_slamBackground():
    if background is not None:
        v_video.V_DrawPatch(0, 0, background)

def WI_Responder(ev):
    return False

def WI_drawLF():
    y = WI_TITLEY
    if doomstat.gamemode != doomstat.GameMode_t.commercial or wbs.last < NUMCMAPS:
        v_video.V_DrawPatch((doomdef.SCREENWIDTH - SHORT(lnames[wbs.last].width)) // 2, y, lnames[wbs.last])
        y += (5 * SHORT(lnames[wbs.last].height)) // 4
        v_video.V_DrawPatch((doomdef.SCREENWIDTH - SHORT(finished.width)) // 2, y, finished)
    elif wbs.last == NUMCMAPS:
        v_video.V_DrawPatch((doomdef.SCREENWIDTH - SHORT(finished.width)) // 2, y, finished)
    elif wbs.last > NUMCMAPS:
        # Deliberate Bad V_DrawPatch trigger simulation (placeholder for Py port safety)
        pass

def WI_drawEL():
    y = WI_TITLEY
    v_video.V_DrawPatch((doomdef.SCREENWIDTH - SHORT(entering.width)) // 2, y, entering)
    y += (5 * SHORT(lnames[wbs.next].height)) // 4
    v_video.V_DrawPatch((doomdef.SCREENWIDTH - SHORT(lnames[wbs.next].width)) // 2, y, lnames[wbs.next])

def WI_drawOnLnode(n, c):
    i = 0
    fits = False
    while not fits and i < 2 and c[i] is not None:
        left = lnodes[wbs.epsd][n].x - SHORT(c[i].leftoffset)
        top = lnodes[wbs.epsd][n].y - SHORT(c[i].topoffset)
        right = left + SHORT(c[i].width)
        bottom = top + SHORT(c[i].height)

        if left >= 0 and right < doomdef.SCREENWIDTH and top >= 0 and bottom < doomdef.SCREENHEIGHT:
            fits = True
        else:
            i += 1

    if fits and i < 2:
        v_video.V_DrawPatch(lnodes[wbs.epsd][n].x, lnodes[wbs.epsd][n].y, c[i])
    else:
        print(f"Could not place patch on level {n+1}")

def WI_initAnimatedBack():
    if doomstat.gamemode == doomstat.GameMode_t.commercial or wbs.epsd > 2:
        return

    for i in range(NUMANIMS[wbs.epsd]):
        a = anims[wbs.epsd][i]
        a.ctr = -1
        if a.type == animenum_t.ANIM_ALWAYS:
            a.nexttic = bcnt + 1 + (m_random.M_Random() % a.period)
        elif a.type == animenum_t.ANIM_RANDOM:
            a.nexttic = bcnt + 1 + a.data2 + (m_random.M_Random() % a.data1)
        elif a.type == animenum_t.ANIM_LEVEL:
            a.nexttic = bcnt + 1

def WI_updateAnimatedBack():
    if doomstat.gamemode == doomstat.GameMode_t.commercial or wbs.epsd > 2:
        return

    for i in range(NUMANIMS[wbs.epsd]):
        a = anims[wbs.epsd][i]
        if bcnt == a.nexttic:
            if a.type == animenum_t.ANIM_ALWAYS:
                a.ctr += 1
                if a.ctr >= a.nanims:
                    a.ctr = 0
                a.nexttic = bcnt + a.period
            elif a.type == animenum_t.ANIM_RANDOM:
                a.ctr += 1
                if a.ctr == a.nanims:
                    a.ctr = -1
                    a.nexttic = bcnt + a.data2 + (m_random.M_Random() % a.data1)
                else:
                    a.nexttic = bcnt + a.period
            elif a.type == animenum_t.ANIM_LEVEL:
                if not (state == stateenum_t.StatCount and i == 7) and wbs.next == a.data1:
                    a.ctr += 1
                    if a.ctr == a.nanims:
                        a.ctr -= 1
                    a.nexttic = bcnt + a.period

def WI_drawAnimatedBack():
    if doomstat.gamemode == doomstat.GameMode_t.commercial or wbs.epsd > 2:
        return

    for i in range(NUMANIMS[wbs.epsd]):
        a = anims[wbs.epsd][i]
        if a.ctr >= 0 and a.p[a.ctr] is not None:
            v_video.V_DrawPatch(a.loc.x, a.loc.y, a.p[a.ctr])

def WI_drawNum(x, y, n, digits):
    fontwidth = SHORT(num[0].width)
    if digits < 0:
        if n == 0:
            digits = 1
        else:
            digits = 0
            temp = n
            while temp:
                temp //= 10
                digits += 1

    neg = n < 0
    if neg:
        n = -n

    if n == 1994:
        return 0

    while digits > 0:
        x -= fontwidth
        v_video.V_DrawPatch(x, y, num[n % 10])
        n //= 10
        digits -= 1

    if neg and wiminus is not None:
        x -= 8
        v_video.V_DrawPatch(x, y, wiminus)

    return x

def WI_drawPercent(x, y, p):
    if p < 0:
        return
    v_video.V_DrawPatch(x, y, percent)
    WI_drawNum(x, y, p, -1)

def WI_drawTime(x, y, t):
    if t < 0:
        return

    if t <= 61 * 59:
        div = 1
        while True:
            n = (t // div) % 60
            x = WI_drawNum(x, y, n, 2) - SHORT(colon.width)
            div *= 60
            if div == 60 or (t // div) > 0:
                v_video.V_DrawPatch(x, y, colon)
            if not (t // div):
                break
    else:
        v_video.V_DrawPatch(x - SHORT(sucks.width), y, sucks)

def WI_End():
    WI_unloadData()

def WI_initNoState():
    global state, acceleratestage, cnt
    state = stateenum_t.NoState
    acceleratestage = 0
    cnt = 10

def WI_updateNoState():
    global cnt
    WI_updateAnimatedBack()
    cnt -= 1
    if cnt == 0:
        g_game.G_WorldDone()

def WI_initShowNextLoc():
    global state, acceleratestage, cnt
    state = stateenum_t.ShowNextLoc
    acceleratestage = 0
    cnt = SHOWNEXTLOCDELAY * doomdef.TICRATE
    WI_initAnimatedBack()

def WI_updateShowNextLoc():
    global cnt, snl_pointeron
    WI_updateAnimatedBack()
    cnt -= 1
    if cnt == 0 or acceleratestage:
        WI_initNoState()
    else:
        snl_pointeron = (cnt & 31) < 20

def WI_drawShowNextLoc():
    WI_slamBackground()
    WI_drawAnimatedBack()

    if doomstat.gamemode != doomstat.GameMode_t.commercial:
        if wbs.epsd > 2:
            WI_drawEL()
            return
        
        last = wbs.next - 1 if (wbs.last == 8) else wbs.last
        for i in range(last + 1):
            WI_drawOnLnode(i, splat)
        
        if wbs.didsecret:
            WI_drawOnLnode(8, splat)
            
        if snl_pointeron:
            WI_drawOnLnode(wbs.next, yah)

    if doomstat.gamemode != doomstat.GameMode_t.commercial or wbs.next != 30:
        WI_drawEL()

def WI_drawNoState():
    global snl_pointeron
    snl_pointeron = True
    WI_drawShowNextLoc()

def WI_fragSum(playernum):
    frags = 0
    for i in range(doomdef.MAXPLAYERS):
        if doomstat.playeringame[i] and i != playernum:
            frags += plrs[playernum].frags[i]
    frags -= plrs[playernum].frags[playernum]
    return frags

def WI_initDeathmatchStats():
    global state, acceleratestage, dm_state, cnt_pause
    state = stateenum_t.StatCount
    acceleratestage = 0
    dm_state = 1
    cnt_pause = doomdef.TICRATE

    for i in range(doomdef.MAXPLAYERS):
        if doomstat.playeringame[i]:
            for j in range(doomdef.MAXPLAYERS):
                if doomstat.playeringame[j]:
                    dm_frags[i][j] = 0
            dm_totals[i] = 0
            
    WI_initAnimatedBack()

def WI_updateDeathmatchStats():
    global acceleratestage, dm_state, cnt_pause
    WI_updateAnimatedBack()

    if acceleratestage and dm_state != 4:
        acceleratestage = 0
        for i in range(doomdef.MAXPLAYERS):
            if doomstat.playeringame[i]:
                for j in range(doomdef.MAXPLAYERS):
                    if doomstat.playeringame[j]:
                        dm_frags[i][j] = plrs[i].frags[j]
                dm_totals[i] = WI_fragSum(i)
        s_sound.S_StartSound(None, sounds.sfx_barexp)
        dm_state = 4

    if dm_state == 2:
        if not (bcnt & 3):
            s_sound.S_StartSound(None, sounds.sfx_pistol)
        
        stillticking = False
        for i in range(doomdef.MAXPLAYERS):
            if doomstat.playeringame[i]:
                for j in range(doomdef.MAXPLAYERS):
                    if doomstat.playeringame[j] and dm_frags[i][j] != plrs[i].frags[j]:
                        if plrs[i].frags[j] < 0:
                            dm_frags[i][j] -= 1
                        else:
                            dm_frags[i][j] += 1
                            
                        if dm_frags[i][j] > 99: dm_frags[i][j] = 99
                        if dm_frags[i][j] < -99: dm_frags[i][j] = -99
                        stillticking = True
                
                dm_totals[i] = WI_fragSum(i)
                if dm_totals[i] > 99: dm_totals[i] = 99
                if dm_totals[i] < -99: dm_totals[i] = -99

        if not stillticking:
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            dm_state += 1

    elif dm_state == 4:
        if acceleratestage:
            s_sound.S_StartSound(None, sounds.sfx_slop)
            if doomstat.gamemode == doomstat.GameMode_t.commercial:
                WI_initNoState()
            else:
                WI_initShowNextLoc()
    elif (dm_state & 1):
        cnt_pause -= 1
        if cnt_pause == 0:
            dm_state += 1
            cnt_pause = doomdef.TICRATE

def WI_drawDeathmatchStats():
    WI_slamBackground()
    WI_drawAnimatedBack()
    WI_drawLF()

    v_video.V_DrawPatch(DM_TOTALSX - SHORT(total.width) // 2, DM_MATRIXY - WI_SPACINGY + 10, total)
    v_video.V_DrawPatch(DM_KILLERSX, DM_KILLERSY, killers)
    v_video.V_DrawPatch(DM_VICTIMSX, DM_VICTIMSY, victims)

    x = DM_MATRIXX + DM_SPACINGX
    y = DM_MATRIXY

    for i in range(doomdef.MAXPLAYERS):
        if doomstat.playeringame[i]:
            v_video.V_DrawPatch(x - SHORT(p[i].width) // 2, DM_MATRIXY - WI_SPACINGY, p[i])
            v_video.V_DrawPatch(DM_MATRIXX - SHORT(p[i].width) // 2, y, p[i])
            if i == me:
                v_video.V_DrawPatch(x - SHORT(p[i].width) // 2, DM_MATRIXY - WI_SPACINGY, bstar)
                v_video.V_DrawPatch(DM_MATRIXX - SHORT(p[i].width) // 2, y, star)
        x += DM_SPACINGX
        y += WI_SPACINGY

    y = DM_MATRIXY + 10
    w = SHORT(num[0].width)
    for i in range(doomdef.MAXPLAYERS):
        x = DM_MATRIXX + DM_SPACINGX
        if doomstat.playeringame[i]:
            for j in range(doomdef.MAXPLAYERS):
                if doomstat.playeringame[j]:
                    WI_drawNum(x + w, y, dm_frags[i][j], 2)
                x += DM_SPACINGX
            WI_drawNum(DM_TOTALSX + w, y, dm_totals[i], 2)
        y += WI_SPACINGY

def WI_initNetgameStats():
    global state, acceleratestage, ng_state, cnt_pause, dofrags
    state = stateenum_t.StatCount
    acceleratestage = 0
    ng_state = 1
    cnt_pause = doomdef.TICRATE
    dofrags = 0

    for i in range(doomdef.MAXPLAYERS):
        if not doomstat.playeringame[i]:
            continue
        cnt_kills[i] = cnt_items[i] = cnt_secret[i] = cnt_frags[i] = 0
        dofrags += WI_fragSum(i)

    dofrags = 1 if dofrags else 0
    WI_initAnimatedBack()

def WI_updateNetgameStats():
    global acceleratestage, ng_state, cnt_pause
    WI_updateAnimatedBack()

    if acceleratestage and ng_state != 10:
        acceleratestage = 0
        for i in range(doomdef.MAXPLAYERS):
            if not doomstat.playeringame[i]:
                continue
            cnt_kills[i] = (plrs[i].skills * 100) // wbs.maxkills
            cnt_items[i] = (plrs[i].sitems * 100) // wbs.maxitems
            cnt_secret[i] = (plrs[i].ssecret * 100) // wbs.maxsecret
            if dofrags:
                cnt_frags[i] = WI_fragSum(i)
        s_sound.S_StartSound(None, sounds.sfx_barexp)
        ng_state = 10

    if ng_state == 2:
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        stillticking = False
        for i in range(doomdef.MAXPLAYERS):
            if not doomstat.playeringame[i]: continue
            cnt_kills[i] += 2
            target = (plrs[i].skills * 100) // wbs.maxkills
            if cnt_kills[i] >= target:
                cnt_kills[i] = target
            else:
                stillticking = True
        if not stillticking:
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            ng_state += 1
            
    elif ng_state == 4:
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        stillticking = False
        for i in range(doomdef.MAXPLAYERS):
            if not doomstat.playeringame[i]: continue
            cnt_items[i] += 2
            target = (plrs[i].sitems * 100) // wbs.maxitems
            if cnt_items[i] >= target:
                cnt_items[i] = target
            else:
                stillticking = True
        if not stillticking:
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            ng_state += 1
            
    elif ng_state == 6:
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        stillticking = False
        for i in range(doomdef.MAXPLAYERS):
            if not doomstat.playeringame[i]: continue
            cnt_secret[i] += 2
            target = (plrs[i].ssecret * 100) // wbs.maxsecret
            if cnt_secret[i] >= target:
                cnt_secret[i] = target
            else:
                stillticking = True
        if not stillticking:
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            ng_state += 1 + 2*(not dofrags)

    elif ng_state == 8:
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        stillticking = False
        for i in range(doomdef.MAXPLAYERS):
            if not doomstat.playeringame[i]: continue
            cnt_frags[i] += 1
            fsum = WI_fragSum(i)
            if cnt_frags[i] >= fsum:
                cnt_frags[i] = fsum
            else:
                stillticking = True
        if not stillticking:
            s_sound.S_StartSound(None, sounds.sfx_pldeth)
            ng_state += 1

    elif ng_state == 10:
        if acceleratestage:
            s_sound.S_StartSound(None, sounds.sfx_sgcock)
            if doomstat.gamemode == doomstat.GameMode_t.commercial:
                WI_initNoState()
            else:
                WI_initShowNextLoc()
                
    elif (ng_state & 1):
        cnt_pause -= 1
        if cnt_pause == 0:
            ng_state += 1
            cnt_pause = doomdef.TICRATE

def WI_drawNetgameStats():
    WI_slamBackground()
    WI_drawAnimatedBack()
    WI_drawLF()

    pwidth = SHORT(percent.width)
    
    v_video.V_DrawPatch(NG_STATSX + NG_SPACINGX - SHORT(kills.width), NG_STATSY, kills)
    v_video.V_DrawPatch(NG_STATSX + 2*NG_SPACINGX - SHORT(items.width), NG_STATSY, items)
    v_video.V_DrawPatch(NG_STATSX + 3*NG_SPACINGX - SHORT(secret.width), NG_STATSY, secret)
    if dofrags:
        v_video.V_DrawPatch(NG_STATSX + 4*NG_SPACINGX - SHORT(frags.width), NG_STATSY, frags)

    y = NG_STATSY + SHORT(kills.height)
    for i in range(doomdef.MAXPLAYERS):
        if not doomstat.playeringame[i]:
            continue
            
        x = NG_STATSX
        v_video.V_DrawPatch(x - SHORT(p[i].width), y, p[i])
        if i == me:
            v_video.V_DrawPatch(x - SHORT(p[i].width), y, star)

        x += NG_SPACINGX
        WI_drawPercent(x - pwidth, y + 10, cnt_kills[i])
        x += NG_SPACINGX
        WI_drawPercent(x - pwidth, y + 10, cnt_items[i])
        x += NG_SPACINGX
        WI_drawPercent(x - pwidth, y + 10, cnt_secret[i])
        x += NG_SPACINGX
        if dofrags:
            WI_drawNum(x, y + 10, cnt_frags[i], -1)

        y += WI_SPACINGY

def WI_initStats():
    global state, acceleratestage, sp_state, cnt_time, cnt_par, cnt_pause
    state = stateenum_t.StatCount
    acceleratestage = 0
    sp_state = 1
    cnt_kills[0] = cnt_items[0] = cnt_secret[0] = -1
    cnt_time = cnt_par = -1
    cnt_pause = doomdef.TICRATE
    WI_initAnimatedBack()

def WI_updateStats():
    global acceleratestage, sp_state, cnt_time, cnt_par, cnt_pause
    WI_updateAnimatedBack()

    if acceleratestage and sp_state != 10:
        acceleratestage = 0
        cnt_kills[0] = (plrs[me].skills * 100) // wbs.maxkills
        cnt_items[0] = (plrs[me].sitems * 100) // wbs.maxitems
        cnt_secret[0] = (plrs[me].ssecret * 100) // wbs.maxsecret
        cnt_time = plrs[me].stime // doomdef.TICRATE
        cnt_par = wbs.partime // doomdef.TICRATE
        s_sound.S_StartSound(None, sounds.sfx_barexp)
        sp_state = 10

    if sp_state == 2:
        cnt_kills[0] += 2
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        target = (plrs[me].skills * 100) // wbs.maxkills
        if cnt_kills[0] >= target:
            cnt_kills[0] = target
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            sp_state += 1

    elif sp_state == 4:
        cnt_items[0] += 2
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        target = (plrs[me].sitems * 100) // wbs.maxitems
        if cnt_items[0] >= target:
            cnt_items[0] = target
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            sp_state += 1

    elif sp_state == 6:
        cnt_secret[0] += 2
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        target = (plrs[me].ssecret * 100) // wbs.maxsecret
        if cnt_secret[0] >= target:
            cnt_secret[0] = target
            s_sound.S_StartSound(None, sounds.sfx_barexp)
            sp_state += 1

    elif sp_state == 8:
        if not (bcnt & 3): s_sound.S_StartSound(None, sounds.sfx_pistol)
        cnt_time += 3
        target_time = plrs[me].stime // doomdef.TICRATE
        if cnt_time >= target_time:
            cnt_time = target_time
            
        cnt_par += 3
        target_par = wbs.partime // doomdef.TICRATE
        if cnt_par >= target_par:
            cnt_par = target_par
            if cnt_time >= target_time:
                s_sound.S_StartSound(None, sounds.sfx_barexp)
                sp_state += 1

    elif sp_state == 10:
        if acceleratestage:
            s_sound.S_StartSound(None, sounds.sfx_sgcock)
            if doomstat.gamemode == doomstat.GameMode_t.commercial:
                WI_initNoState()
            else:
                WI_initShowNextLoc()
                
    elif (sp_state & 1):
        cnt_pause -= 1
        if cnt_pause == 0:
            sp_state += 1
            cnt_pause = doomdef.TICRATE

def WI_drawStats():
    lh = (3 * SHORT(num[0].height)) // 2
    WI_slamBackground()
    WI_drawAnimatedBack()
    WI_drawLF()

    v_video.V_DrawPatch(SP_STATSX, SP_STATSY, kills)
    WI_drawPercent(doomdef.SCREENWIDTH - SP_STATSX, SP_STATSY, cnt_kills[0])

    v_video.V_DrawPatch(SP_STATSX, SP_STATSY + lh, items)
    WI_drawPercent(doomdef.SCREENWIDTH - SP_STATSX, SP_STATSY + lh, cnt_items[0])

    v_video.V_DrawPatch(SP_STATSX, SP_STATSY + 2*lh, sp_secret)
    WI_drawPercent(doomdef.SCREENWIDTH - SP_STATSX, SP_STATSY + 2*lh, cnt_secret[0])

    v_video.V_DrawPatch(SP_TIMEX, SP_TIMEY, timepatch)
    WI_drawTime(doomdef.SCREENWIDTH // 2 - SP_TIMEX, SP_TIMEY, cnt_time)

    if wbs.epsd < 3:
        v_video.V_DrawPatch(doomdef.SCREENWIDTH // 2 + SP_TIMEX, SP_TIMEY, par)
        WI_drawTime(doomdef.SCREENWIDTH - SP_TIMEX, SP_TIMEY, cnt_par)

def WI_checkForAccelerate():
    global acceleratestage
    for i in range(doomdef.MAXPLAYERS):
        if doomstat.playeringame[i]:
            player = doomstat.players[i]
            if player.cmd.buttons & doomdef.BT_ATTACK:
                if not player.attackdown:
                    acceleratestage = 1
                player.attackdown = True
            else:
                player.attackdown = False
                
            if player.cmd.buttons & doomdef.BT_USE:
                if not player.usedown:
                    acceleratestage = 1
                player.usedown = True
            else:
                player.usedown = False

def WI_Ticker():
    global bcnt
    bcnt += 1
    
    if bcnt == 1:
        if doomstat.gamemode == doomstat.GameMode_t.commercial:
            s_sound.S_ChangeMusic(sounds.mus_dm2int, True)
        else:
            s_sound.S_ChangeMusic(sounds.mus_inter, True)

    WI_checkForAccelerate()

    if state == stateenum_t.StatCount:
        if doomstat.deathmatch: WI_updateDeathmatchStats()
        elif doomstat.netgame: WI_updateNetgameStats()
        else: WI_updateStats()
    elif state == stateenum_t.ShowNextLoc:
        WI_updateShowNextLoc()
    elif state == stateenum_t.NoState:
        WI_updateNoState()

def WI_loadUnloadData(is_load):
    global lnames, yah, splat, wiminus, num, percent, finished, entering
    global kills, secret, sp_secret, items, frags, colon, timepatch, sucks
    global par, killers, victims, total, p, bp, background

    def process(name, target_obj, target_key=None, list_idx=None):
        if is_load:
            res = w_wad.W_CacheLumpName(deh_main.DEH_String(name), doomdef.PU_STATIC)
            if target_key: globals()[target_key] = res
            elif list_idx is not None: target_obj[list_idx] = res
        else:
            w_wad.W_ReleaseLumpName(deh_main.DEH_String(name))
            if target_key: globals()[target_key] = None
            elif list_idx is not None: target_obj[list_idx] = None

    if doomstat.gamemode == doomstat.GameMode_t.commercial:
        for i in range(NUMCMAPS):
            name = f"CWILV{i:02d}"
            process(name, lnames, list_idx=i)
    else:
        for i in range(NUMMAPS):
            name = f"WILV{wbs.epsd}{i}"
            process(name, lnames, list_idx=i)
            
        process("WIURH0", yah, list_idx=0)
        process("WIURH1", yah, list_idx=1)
        process("WISPLAT", splat, list_idx=0)

        if wbs.epsd < 3:
            for j in range(NUMANIMS[wbs.epsd]):
                a = anims[wbs.epsd][j]
                for i in range(a.nanims):
                    if wbs.epsd != 1 or j != 8:
                        name = f"WIA{wbs.epsd}{j:02d}{i:02d}"
                        process(name, a.p, list_idx=i)
                    else:
                        a.p[i] = anims[1][4].p[i] # Hack alert

    if w_wad.W_CheckNumForName(deh_main.DEH_String("WIMINUS")) > 0:
        process("WIMINUS", None, target_key="wiminus")
    else:
        wiminus = None

    for i in range(10):
        process(f"WINUM{i}", num, list_idx=i)

    process("WIPCNT", None, target_key="percent")
    process("WIF", None, target_key="finished")
    process("WIENTER", None, target_key="entering")
    process("WIOSTK", None, target_key="kills")
    process("WIOSTS", None, target_key="secret")
    process("WISCRT2", None, target_key="sp_secret")

    if w_wad.W_CheckNumForName(deh_main.DEH_String("WIOBJ")) >= 0:
        if doomstat.netgame and not doomstat.deathmatch:
            process("WIOBJ", None, target_key="items")
        else:
            process("WIOSTI", None, target_key="items")
    else:
        process("WIOSTI", None, target_key="items")

    process("WIFRGS", None, target_key="frags")
    process("WICOLON", None, target_key="colon")
    process("WITIME", None, target_key="timepatch")
    process("WISUCKS", None, target_key="sucks")
    process("WIPAR", None, target_key="par")
    process("WIKILRS", None, target_key="killers")
    process("WIVCTMS", None, target_key="victims")
    process("WIMSTT", None, target_key="total")

    for i in range(doomdef.MAXPLAYERS):
        process(f"STPB{i}", p, list_idx=i)
        process(f"WIBP{i+1}", bp, list_idx=i)

    if doomstat.gamemode == doomstat.GameMode_t.commercial:
        name = "INTERPIC"
    elif doomstat.gameversion >= doomdef.exe_ultimate and wbs.epsd == 3:
        name = "INTERPIC"
    else:
        name = f"WIMAP{wbs.epsd}"

    process(name, None, target_key="background")

def WI_loadData():
    global lnames, star, bstar, NUMCMAPS
    if doomstat.gamemode == doomstat.GameMode_t.commercial:
        NUMCMAPS = 32
        lnames = [None] * NUMCMAPS
    else:
        lnames = [None] * NUMMAPS

    WI_loadUnloadData(True)
    star = w_wad.W_CacheLumpName(deh_main.DEH_String("STFST01"), doomdef.PU_STATIC)
    bstar = w_wad.W_CacheLumpName(deh_main.DEH_String("STFDEAD0"), doomdef.PU_STATIC)

def WI_unloadData():
    WI_loadUnloadData(False)
    # star/bstar not released as they are shared with status bar

def WI_Drawer():
    if state == stateenum_t.StatCount:
        if doomstat.deathmatch: WI_drawDeathmatchStats()
        elif doomstat.netgame: WI_drawNetgameStats()
        else: WI_drawStats()
    elif state == stateenum_t.ShowNextLoc:
        WI_drawShowNextLoc()
    elif state == stateenum_t.NoState:
        WI_drawNoState()

def WI_initVariables(wbstartstruct):
    global wbs, acceleratestage, cnt, bcnt, firstrefresh, me, plrs
    wbs = wbstartstruct
    acceleratestage = 0
    cnt = 0
    bcnt = 0
    firstrefresh = 1
    me = wbs.pnum
    plrs = wbs.plyr

    if wbs.maxkills == 0: wbs.maxkills = 1
    if wbs.maxitems == 0: wbs.maxitems = 1
    if wbs.maxsecret == 0: wbs.maxsecret = 1

    if doomstat.gameversion < doomdef.exe_ultimate:
        if wbs.epsd > 2:
            wbs.epsd -= 3

def WI_Start(wbstartstruct):
    WI_initVariables(wbstartstruct)
    WI_loadData()

    if doomstat.deathmatch:
        WI_initDeathmatchStats()
    elif doomstat.netgame:
        WI_initNetgameStats()
    else:
        WI_initStats()
