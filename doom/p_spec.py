import p_ceilng
import p_floor
import p_tick
# p_spec.py
# Sector specials, texture animation, switches, doors, floors,
# ceilings, platforms, lighting, teleports
# Ported from p_spec.c / p_spec.h

from doomdef import (
    FRACBITS, FRACUNIT, TICRATE, MAXPLAYERS,
    ML_TWOSIDED, ML_SOUNDBLOCK,
    fixed_mul, fixed_div,
)
from d_think import Thinker

# ------------------------------------------------------------------
# Animation definitions
# ------------------------------------------------------------------
_animdefs = [
    (False, 'NUKAGE3',  'NUKAGE1',  8),
    (False, 'FWATER4',  'FWATER1',  8),
    (False, 'SWATER4',  'SWATER1',  8),
    (False, 'LAVA4',    'LAVA1',    8),
    (False, 'BLOOD3',   'BLOOD1',   8),
    (False, 'RROCK08',  'RROCK05',  8),
    (False, 'SLIME04',  'SLIME01',  8),
    (False, 'SLIME08',  'SLIME05',  8),
    (False, 'SLIME12',  'SLIME09',  8),
    (True,  'BLODGR4',  'BLODGR1',  8),
    (True,  'SLADRIP3', 'SLADRIP1', 8),
    (True,  'BLODRIP4', 'BLODRIP1', 8),
    (True,  'FIREWALL', 'FIREWALA', 8),
    (True,  'GSTFONT3', 'GSTFONT1', 8),
    (True,  'FIRELAVA', 'FIRELAV3', 8),
    (True,  'FIREMAG3', 'FIREMAG1', 8),
    (True,  'FIREBLU2', 'FIREBLU1', 8),
    (True,  'ROCKRED3', 'ROCKRED1', 8),
    (True,  'BFALL4',   'BFALL1',   8),
    (True,  'SFALL4',   'SFALL1',   8),
    (True,  'WFALL4',   'WFALL1',   8),
    (True,  'DBRAIN4',  'DBRAIN1',  8),
]

class _Anim:
    __slots__ = ('istexture', 'picnum', 'basepic', 'numpics', 'speed')
    def __init__(self, ist, pic, base, num, spd):
        self.istexture = ist
        self.picnum    = pic
        self.basepic   = base
        self.numpics   = num
        self.speed     = spd

anims: list = []

MAXLINEANIMS = 64
linespeciallist: list = []
numlinespecials: int  = 0

levelTimer:     bool = False
levelTimeCount: int  = 0

# ------------------------------------------------------------------
# Switch texture list
# ------------------------------------------------------------------
MAXSWITCHES = 50
MAXBUTTONS  = 16
BUTTONTIME  = 35

class _Button:
    __slots__ = ('line', 'where', 'btexture', 'btimer', 'soundorg')
    def __init__(self):
        self.line     = None
        self.where    = 0
        self.btexture = 0
        self.btimer   = 0
        self.soundorg = None

buttonlist: list = [_Button() for _ in range(MAXBUTTONS)]

_alphSwitchList = [
    # (name1, name2, episode)
    ('SW1BRCOM', 'SW2BRCOM', 1),
    ('SW1BRN1',  'SW2BRN1',  1),
    ('SW1BRN2',  'SW2BRN2',  1),
    ('SW1BRNGN', 'SW2BRNGN', 1),
    ('SW1BROWN', 'SW2BROWN', 1),
    ('SW1COMM',  'SW2COMM',  1),
    ('SW1COMP',  'SW2COMP',  1),
    ('SW1DIRT',  'SW2DIRT',  1),
    ('SW1EXIT',  'SW2EXIT',  1),
    ('SW1GRAY',  'SW2GRAY',  1),
    ('SW1GRAY1', 'SW2GRAY1', 1),
    ('SW1METAL', 'SW2METAL', 1),
    ('SW1PIPE',  'SW2PIPE',  1),
    ('SW1SLAD',  'SW2SLAD',  1),
    ('SW1STARG', 'SW2STARG', 1),
    ('SW1STON1', 'SW2STON1', 1),
    ('SW1STON2', 'SW2STON2', 1),
    ('SW1STONE', 'SW2STONE', 1),
    ('SW1STRTN', 'SW2STRTN', 1),
    ('SW1BLUE',  'SW2BLUE',  2),
    ('SW1CMT',   'SW2CMT',   2),
    ('SW1GARG',  'SW2GARG',  2),
    ('SW1GSTON', 'SW2GSTON', 2),
    ('SW1HOT',   'SW2HOT',   2),
    ('SW1LION',  'SW2LION',  2),
    ('SW1SATYR', 'SW2SATYR', 2),
    ('SW1SKIN',  'SW2SKIN',  2),
    ('SW1VINE',  'SW2VINE',  2),
    ('SW1WOOD',  'SW2WOOD',  2),
    ('SW1PANEL', 'SW2PANEL', 3),
    ('SW1ROCK',  'SW2ROCK',  3),
    ('SW1MET2',  'SW2MET2',  3),
    ('SW1WDMET', 'SW2WDMET', 3),
    ('SW1BRIK',  'SW2BRIK',  3),
    ('SW1MOD1',  'SW2MOD1',  3),
    ('SW1ZIM',   'SW2ZIM',   3),
    ('SW1STON6', 'SW2STON6', 3),
    ('SW1TEK',   'SW2TEK',   3),
    ('SW1MARB',  'SW2MARB',  3),
    ('SW1SKULL', 'SW2SKULL', 3),
]

switchlist: list = []   # list of (tex1_idx, tex2_idx) pairs

# ------------------------------------------------------------------
# Platform, ceiling, door pool
# ------------------------------------------------------------------
MAXPLATS    = 30
MAXCEILINGS = 30
CEILSPEED   = FRACUNIT
CEILWAIT    = 150
PLATWAIT    = 3
PLATSPEED   = FRACUNIT
FLOORSPEED  = FRACUNIT
VDOORSPEED  = FRACUNIT * 2
VDOORWAIT   = 150
GLOWSPEED   = 8
STROBEBRIGHT = 5
FASTDARK    = 15
SLOWDARK    = 35

activeplats:    list = [None] * MAXPLATS
activeceilings: list = [None] * MAXCEILINGS

# Result codes for p_floor.T_MovePlane
RESULT_OK       = 0
RESULT_CRUSHED  = 1
RESULT_PASTDEST = 2

# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------
def getSide(currSector: int, line: int, side: int):
    import p_setup
    return p_setup.sides[p_setup.sectors[currSector].lines[line].sidenum[side]]

def getSector(currSector: int, line: int, side: int):
    import p_setup
    return p_setup.sides[p_setup.sectors[currSector].lines[line].sidenum[side]].sector

def twoSided(sector: int, line: int) -> bool:
    import p_setup
    return bool(p_setup.sectors[sector].lines[line].flags & ML_TWOSIDED)

def getNextSector(line, sec):
    if not (line.flags & ML_TWOSIDED):
        return None
    if line.frontsector is sec:
        return line.backsector
    return line.frontsector

def P_FindLowestFloorSurrounding(sec):
    floor = sec.floorheight
    for ld in sec.lines:
        other = getNextSector(ld, sec)
        if other and other.floorheight < floor:
            floor = other.floorheight
    return floor

def P_FindHighestFloorSurrounding(sec):
    floor = -500 * FRACUNIT
    for ld in sec.lines:
        other = getNextSector(ld, sec)
        if other and other.floorheight > floor:
            floor = other.floorheight
    return floor

def P_FindNextHighestFloor(sec, currentheight: int) -> int:
    heights = []
    for ld in sec.lines:
        other = getNextSector(ld, sec)
        if other and other.floorheight > currentheight:
            heights.append(other.floorheight)
    return min(heights) if heights else currentheight

def P_FindLowestCeilingSurrounding(sec):
    height = 0x7FFFFFFF
    for ld in sec.lines:
        other = getNextSector(ld, sec)
        if other and other.ceilingheight < height:
            height = other.ceilingheight
    return height

def P_FindHighestCeilingSurrounding(sec):
    height = 0
    for ld in sec.lines:
        other = getNextSector(ld, sec)
        if other and other.ceilingheight > height:
            height = other.ceilingheight
    return height

def P_FindSectorFromLineTag(line, start: int) -> int:
    import p_setup
    for i in range(start + 1, len(p_setup.sectors)):
        if p_setup.sectors[i].tag == line.tag:
            return i
    return -1

def P_FindMinSurroundingLight(sector, max_light: int) -> int:
    min_l = max_light
    for ld in sector.lines:
        other = getNextSector(ld, sector)
        if other and other.lightlevel < min_l:
            min_l = other.lightlevel
    return min_l


# ------------------------------------------------------------------
# P_InitPicAnims
# ------------------------------------------------------------------
def P_InitPicAnims():
    from r_data import R_CheckTextureNumForName, R_TextureNumForName, R_FlatNumForName
    from wad import get_wad

    anims.clear()
    wad = get_wad()

    for (ist, endname, startname, speed) in _animdefs:
        if ist:
            if R_CheckTextureNumForName(startname) == -1:
                continue
            picnum  = R_TextureNumForName(endname)
            basepic = R_TextureNumForName(startname)
        else:
            try:
                wad.get_lump(startname)
            except KeyError:
                continue
            try:
                picnum  = R_FlatNumForName(endname)
                basepic = R_FlatNumForName(startname)
            except KeyError:
                continue

        numpics = picnum - basepic + 1
        if numpics >= 2:
            anims.append(_Anim(ist, picnum, basepic, numpics, speed))


# ------------------------------------------------------------------
# P_InitSwitchList
# ------------------------------------------------------------------
def P_InitSwitchList():
    import doomstat
    from r_data import R_CheckTextureNumForName
    from doomdef import GameMode

    switchlist.clear()
    ep = (1 if doomstat.gamemode == GameMode.SHAREWARE else
          2 if doomstat.gamemode == GameMode.REGISTERED else 3)

    for n1, n2, swe in _alphSwitchList:
        if swe <= ep:
            t1 = R_CheckTextureNumForName(n1)
            t2 = R_CheckTextureNumForName(n2)
            if t1 != -1 and t2 != -1:
                switchlist.append((t1, t2))


# ------------------------------------------------------------------
# P_ChangeSwitchTexture
# ------------------------------------------------------------------
def P_ChangeSwitchTexture(line, useagain: bool):
    import p_setup
    from p_mobj import S_StartSound
    import info as info_mod

    sd = p_setup.sides[line.sidenum[0]]

    for t1, t2 in switchlist:
        for tex_on, tex_off in ((t1, t2), (t2, t1)):
            if sd.toptexture == tex_on:
                where = 0  # top
                sd.toptexture = tex_off
            elif sd.midtexture == tex_on:
                where = 1  # middle
                sd.midtexture = tex_off
            elif sd.bottomtexture == tex_on:
                where = 2  # bottom
                sd.bottomtexture = tex_off
            else:
                continue

            S_StartSound(None, info_mod.sfx_swtchn)

            if useagain:
                for btn in buttonlist:
                    if not btn.btimer:
                        btn.line     = line
                        btn.where    = where
                        btn.btexture = tex_on
                        btn.btimer   = BUTTONTIME
                        btn.soundorg = sd.sector.soundorg
                        break
            return


# ------------------------------------------------------------------
# p_floor.T_MovePlane  — generic floor/ceiling mover
# ------------------------------------------------------------------
def T_MovePlane(sector, speed: int, dest: int, crush: bool,
                floorOrCeiling: int, direction: int) -> int:
    from p_map import P_ChangeSector

    if floorOrCeiling == 0:   # floor
        if direction == -1:   # down
            newheight = sector.floorheight - speed
            if newheight < dest:
                sector.floorheight = dest
                if P_ChangeSector(sector, crush):
                    sector.floorheight = sector.floorheight  # no-op; already set
                return RESULT_PASTDEST
            else:
                sector.floorheight = newheight
                P_ChangeSector(sector, crush)
        else:                  # up
            newheight = sector.floorheight + speed
            if newheight > dest:
                sector.floorheight = dest
                if P_ChangeSector(sector, crush):
                    sector.floorheight -= speed
                    P_ChangeSector(sector, crush)
                    return RESULT_CRUSHED
                return RESULT_PASTDEST
            else:
                sector.floorheight = newheight
                if P_ChangeSector(sector, crush):
                    sector.floorheight -= speed
                    P_ChangeSector(sector, crush)
                    return RESULT_CRUSHED
    else:                      # ceiling
        if direction == -1:   # down
            newheight = sector.ceilingheight - speed
            if newheight < dest:
                sector.ceilingheight = dest
                if P_ChangeSector(sector, crush):
                    sector.ceilingheight += speed
                    P_ChangeSector(sector, crush)
                    return RESULT_CRUSHED
                return RESULT_PASTDEST
            else:
                sector.ceilingheight = newheight
                if P_ChangeSector(sector, crush):
                    sector.ceilingheight += speed
                    P_ChangeSector(sector, crush)
                    return RESULT_CRUSHED
        else:                  # up
            newheight = sector.ceilingheight + speed
            if newheight > dest:
                sector.ceilingheight = dest
                P_ChangeSector(sector, crush)
                return RESULT_PASTDEST
            else:
                sector.ceilingheight = newheight
                P_ChangeSector(sector, crush)

    return RESULT_OK


# ------------------------------------------------------------------
# Door thinker
# ------------------------------------------------------------------
class VLDoor(Thinker):
    __slots__ = ('type', 'sector', 'topheight', 'speed',
                 'direction', 'topwait', 'topcountdown')
    def __init__(self):
        super().__init__()
        self.type = 0; self.sector = None; self.topheight = 0
        self.speed = VDOORSPEED; self.direction = 0
        self.topwait = VDOORWAIT; self.topcountdown = 0

# vldoor_e values
VLD_NORMAL       = 0
VLD_CLOSE30THENOPEN = 1
VLD_CLOSE        = 2
VLD_OPEN         = 3
VLD_RAISEIN5MINS = 4
VLD_BLAZERAISE   = 5
VLD_BLAZEOPEN    = 6
VLD_BLAZECLOSE   = 7

def T_VerticalDoor(door: VLDoor):
    import info as info_mod
    from p_mobj import S_StartSound

    if door.direction == 0:   # waiting
        door.topcountdown -= 1
        if door.topcountdown == 0:
            if door.type in (VLD_BLAZEOPEN, VLD_NORMAL):
                door.direction = -1
                S_StartSound(door.sector.soundorg, info_mod.sfx_dorcls)
            elif door.type == VLD_CLOSE30THENOPEN:
                door.direction = 1
                S_StartSound(door.sector.soundorg, info_mod.sfx_doropn)

    elif door.direction == 2:  # initial wait
        door.topcountdown -= 1
        if door.topcountdown == 0:
            if door.type == VLD_RAISEIN5MINS:
                door.direction = 1
                door.type = VLD_NORMAL
                S_StartSound(door.sector.soundorg, info_mod.sfx_doropn)

    elif door.direction == -1:  # going down
        res = p_floor.T_MovePlane(door.sector, door.speed,
                          door.sector.floorheight, False, 1, -1)
        if res == RESULT_PASTDEST:
            if door.type in (VLD_BLAZEOPEN, VLD_BLAZECLOSE, VLD_CLOSE):
                door.sector.specialdata = None
                door.mark_removed()
                S_StartSound(door.sector.soundorg, info_mod.sfx_bdcls)
            elif door.type in (VLD_NORMAL, VLD_CLOSE30THENOPEN):
                door.direction    = 0
                door.topcountdown = door.topwait
        elif res == RESULT_CRUSHED:
            if door.type != VLD_BLAZEOPEN:
                door.direction = 1
                S_StartSound(door.sector.soundorg, info_mod.sfx_doropn)

    elif door.direction == 1:   # going up
        res = p_floor.T_MovePlane(door.sector, door.speed,
                          door.topheight, False, 1, 1)
        if res == RESULT_PASTDEST:
            if door.type in (VLD_BLAZEOPEN, VLD_OPEN):
                door.sector.specialdata = None
                door.mark_removed()
            elif door.type in (VLD_NORMAL, VLD_BLAZERAISE, VLD_CLOSE30THENOPEN):
                door.direction    = 0
                door.topcountdown = door.topwait


def EV_DoDoor(line, dtype: int) -> int:
    import p_setup
    rtn = 0
    secnum = -1
    speed  = (VDOORSPEED * 4 if dtype in (VLD_BLAZERAISE, VLD_BLAZEOPEN, VLD_BLAZECLOSE)
              else VDOORSPEED)

    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        sec = p_setup.sectors[secnum]
        if sec.specialdata: continue

        rtn = 1
        door = VLDoor()
        door.type   = dtype
        door.sector = sec
        door.speed  = speed
        door.topwait = VDOORWAIT
        sec.specialdata = door

        door.topheight = p_spec.P_FindLowestCeilingSurrounding(sec) - 4 * FRACUNIT

        if dtype == VLD_NORMAL:
            door.direction = 1
        elif dtype == VLD_OPEN:
            door.direction = 1
        elif dtype == VLD_BLAZEOPEN:
            door.direction = 1
        elif dtype == VLD_BLAZERAISE:
            door.direction = 1
        elif dtype == VLD_CLOSE:
            door.direction    = -1
            door.topcountdown = VDOORWAIT
        elif dtype == VLD_BLAZECLOSE:
            door.direction    = -1
            door.topcountdown = VDOORWAIT
        elif dtype == VLD_CLOSE30THENOPEN:
            door.direction    = -1
            door.topwait      = 35 * 30

        door.function = T_VerticalDoor
        p_tick.P_AddThinker(door)

    return rtn


def EV_VerticalDoor(line, thing):
    """Player-activated door on the line."""
    import p_setup, info as info_mod
    from p_mobj import S_StartSound
    from doomdef import CardType

    # Key check
    _keymap = {
        26: (CardType.BLUECARD,   CardType.BLUESKULL,   "You need a blue key to open this door"),
        27: (CardType.YELLOWCARD, CardType.YELLOWSKULL, "You need a yellow key to open this door"),
        28: (CardType.REDCARD,    CardType.REDSKULL,    "You need a red key to open this door"),
        32: (CardType.BLUECARD,   CardType.BLUESKULL,   "You need a blue key to open this door"),
        33: (CardType.REDCARD,    CardType.REDSKULL,    "You need a red key to open this door"),
        34: (CardType.YELLOWCARD, CardType.YELLOWSKULL, "You need a yellow key to open this door"),
        99: (CardType.BLUECARD,   CardType.BLUESKULL,   "You need a blue key to open this door"),
        134: (CardType.REDCARD,   CardType.REDSKULL,    "You need a red key to open this door"),
        136: (CardType.YELLOWCARD,CardType.YELLOWSKULL, "You need a yellow key to open this door"),
    }
    if line.special in _keymap and thing.player:
        k1, k2, msg = _keymap[line.special]
        if not (thing.player.cards[k1] or thing.player.cards[k2]):
            thing.player.message = msg
            S_StartSound(thing, info_mod.sfx_oof)
            return

    sec = (p_setup.sides[line.sidenum[1]].sector
           if line.sidenum[1] != -1 else None)
    if sec is None: return

    if sec.specialdata:
        door = sec.specialdata
        if isinstance(door, VLDoor):
            if door.direction == -1:
                door.direction = 1
                return
            elif thing.player:
                door.direction = -1
                return

    door = VLDoor()
    door.sector   = sec
    door.topwait  = VDOORWAIT

    if line.special in (1, 26, 27, 28):
        door.type  = VLD_NORMAL
        door.speed = VDOORSPEED
    elif line.special in (31, 32, 33, 34):
        door.type  = VLD_OPEN
        door.speed = VDOORSPEED
        line.special = 0
    elif line.special in (117, 118):
        door.type  = VLD_BLAZERAISE if line.special == 117 else VLD_BLAZEOPEN
        door.speed = VDOORSPEED * 4

    door.topheight  = p_spec.P_FindLowestCeilingSurrounding(sec) - 4 * FRACUNIT
    door.direction  = 1
    sec.specialdata = door
    door.function   = T_VerticalDoor
    p_tick.P_AddThinker(door)
    S_StartSound(sec.soundorg, info_mod.sfx_doropn)


def EV_DoLockedDoor(line, dtype: int, thing) -> int:
    import info as info_mod
    from p_mobj import S_StartSound
    from doomdef import CardType

    _locks = {
        99:  (CardType.BLUECARD,   CardType.BLUESKULL,   "You need a blue key to open this door"),
        133: (CardType.BLUECARD,   CardType.BLUESKULL,   "You need a blue key to open this door"),
        134: (CardType.REDCARD,    CardType.REDSKULL,    "You need a red key to open this door"),
        135: (CardType.REDCARD,    CardType.REDSKULL,    "You need a red key to open this door"),
        136: (CardType.YELLOWCARD, CardType.YELLOWSKULL, "You need a yellow key to open this door"),
        137: (CardType.YELLOWCARD, CardType.YELLOWSKULL, "You need a yellow key to open this door"),
    }
    if line.special in _locks and thing.player:
        k1, k2, msg = _locks[line.special]
        if not (thing.player.cards[k1] or thing.player.cards[k2]):
            thing.player.message = msg
            S_StartSound(thing, info_mod.sfx_oof)
            return 0
    return p_doors.EV_DoDoor(line, dtype)


def P_SpawnDoorCloseIn30(sec):
    door = VLDoor()
    door.sector       = sec
    door.direction    = 0
    door.type         = VLD_NORMAL
    door.speed        = VDOORSPEED
    door.topwait      = VDOORWAIT
    door.topcountdown = 35 * 30
    sec.specialdata   = door
    door.function     = T_VerticalDoor
    p_tick.P_AddThinker(door)


def P_SpawnDoorRaiseIn5Mins(sec, secnum: int):
    door = VLDoor()
    door.sector       = sec
    door.direction    = 2
    door.type         = VLD_RAISEIN5MINS
    door.speed        = VDOORSPEED
    door.topwait      = VDOORWAIT
    door.topcountdown = 35 * 60 * 5 // 8
    door.topheight    = p_spec.P_FindLowestCeilingSurrounding(sec) - 4 * FRACUNIT
    sec.specialdata   = door
    door.function     = T_VerticalDoor
    p_tick.P_AddThinker(door)


# ------------------------------------------------------------------
# Floor thinker
# ------------------------------------------------------------------
class FloorMove(Thinker):
    __slots__ = ('type', 'crush', 'sector', 'direction',
                 'newspecial', 'texture', 'floordestheight', 'speed')
    def __init__(self):
        super().__init__()
        self.type = 0; self.crush = False; self.sector = None
        self.direction = 0; self.newspecial = 0; self.texture = 0
        self.floordestheight = 0; self.speed = FLOORSPEED

# floor_e
LOWER_FLOOR         = 0
LOWER_FLOOR_LOWEST  = 1
TURBO_LOWER         = 2
RAISE_FLOOR         = 3
RAISE_FLOOR_NEAREST = 4
RAISE_TO_TEXTURE    = 5
LOWER_AND_CHANGE    = 6
RAISE_FLOOR_24      = 7
RAISE_FLOOR_24_CHANGE = 8
RAISE_FLOOR_CRUSH   = 9
RAISE_FLOOR_TURBO   = 10
DONUT_RAISE         = 11
RAISE_FLOOR_512     = 12

def T_MoveFloor(floor: FloorMove):
    res = p_floor.T_MovePlane(floor.sector, floor.speed,
                      floor.floordestheight, floor.crush, 0, floor.direction)
    if res == RESULT_PASTDEST:
        floor.sector.specialdata = None
        if floor.direction == 1:
            if floor.type in (RAISE_FLOOR_24_CHANGE, LOWER_AND_CHANGE):
                floor.sector.floorpic   = floor.texture
                floor.sector.special    = floor.newspecial
        floor.mark_removed()


def EV_DoFloor(line, floortype: int) -> int:
    import p_setup
    rtn    = 0
    secnum = -1

    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        sec = p_setup.sectors[secnum]
        if sec.specialdata: continue
        rtn = 1

        floor = FloorMove()
        floor.type   = floortype
        floor.crush  = False
        floor.sector = sec
        floor.speed  = FLOORSPEED
        sec.specialdata = floor

        if floortype == LOWER_FLOOR:
            floor.direction      = -1
            floor.floordestheight = p_spec.P_FindHighestFloorSurrounding(sec)
        elif floortype == LOWER_FLOOR_LOWEST:
            floor.direction      = -1
            floor.floordestheight = p_spec.P_FindLowestFloorSurrounding(sec)
        elif floortype == TURBO_LOWER:
            floor.direction      = -1
            floor.speed          = FLOORSPEED * 4
            floor.floordestheight = p_spec.P_FindHighestFloorSurrounding(sec) + 8 * FRACUNIT
        elif floortype == RAISE_FLOOR:
            floor.direction      = 1
            floor.floordestheight = p_spec.P_FindLowestCeilingSurrounding(sec)
            if floor.floordestheight > sec.ceilingheight:
                floor.floordestheight = sec.ceilingheight
        elif floortype == RAISE_FLOOR_NEAREST:
            floor.direction      = 1
            floor.floordestheight = p_spec.P_FindNextHighestFloor(sec, sec.floorheight)
        elif floortype == RAISE_TO_TEXTURE:
            floor.direction = 1
            from r_data import textureheight
            minsize = 0x7FFFFFFF
            for ld in sec.lines:
                if ld.flags & 4:  # ML_TWOSIDED
                    if ld.sidenum[0] != -1:
                        import p_setup as ps
                        texnum = ps.sides[ld.sidenum[0]].bottomtexture
                        if texnum < len(textureheight) and textureheight[texnum] < minsize:
                            minsize = textureheight[texnum]
                    if ld.sidenum[1] != -1:
                        texnum = ps.sides[ld.sidenum[1]].bottomtexture
                        if texnum < len(textureheight) and textureheight[texnum] < minsize:
                            minsize = textureheight[texnum]
            floor.floordestheight = sec.floorheight + minsize
        elif floortype == LOWER_AND_CHANGE:
            floor.direction      = -1
            floor.floordestheight = p_spec.P_FindLowestFloorSurrounding(sec)
            floor.texture        = sec.floorpic
            # inherit neighbouring sector's texture
            for ld in sec.lines:
                other = getNextSector(ld, sec)
                if other and other.floorheight == floor.floordestheight:
                    floor.texture    = other.floorpic
                    floor.newspecial = other.special
                    break
        elif floortype == RAISE_FLOOR_24:
            floor.direction      = 1
            floor.floordestheight = sec.floorheight + 24 * FRACUNIT
        elif floortype == RAISE_FLOOR_24_CHANGE:
            floor.direction      = 1
            floor.floordestheight = sec.floorheight + 24 * FRACUNIT
            floor.texture        = line.frontsector.floorpic if line.frontsector else sec.floorpic
            floor.newspecial     = line.frontsector.special  if line.frontsector else 0
        elif floortype == RAISE_FLOOR_CRUSH:
            floor.direction      = 1
            floor.crush          = True
            floor.floordestheight = p_spec.P_FindLowestCeilingSurrounding(sec) - 8 * FRACUNIT
        elif floortype == RAISE_FLOOR_TURBO:
            floor.direction      = 1
            floor.speed          = FLOORSPEED * 4
            floor.floordestheight = p_spec.P_FindNextHighestFloor(sec, sec.floorheight)
        elif floortype == DONUT_RAISE:
            floor.direction = 1
        elif floortype == RAISE_FLOOR_512:
            floor.direction      = 1
            floor.floordestheight = sec.floorheight + 512 * FRACUNIT

        floor.function = T_MoveFloor
        p_tick.P_AddThinker(floor)

    return rtn


def EV_BuildStairs(line, stype: int) -> int:
    import p_setup
    rtn    = 0
    secnum = -1
    speed  = FLOORSPEED * 4 if stype == 1 else FLOORSPEED   # turbo16 / build8
    stairsize = 16 * FRACUNIT if stype == 1 else 8 * FRACUNIT

    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        sec = p_setup.sectors[secnum]
        if sec.specialdata: continue
        rtn = 1

        height = sec.floorheight + stairsize
        while True:
            floor = FloorMove()
            floor.type           = RAISE_FLOOR
            floor.direction      = 1
            floor.sector         = sec
            floor.speed          = speed
            floor.floordestheight = height
            sec.specialdata      = floor
            floor.function       = T_MoveFloor
            p_tick.P_AddThinker(floor)

            # find next stair sector
            texture = sec.floorpic
            ok = False
            for ld in sec.lines:
                if not (ld.flags & 4): continue  # ML_TWOSIDED
                tsec = ld.backsector if ld.frontsector is sec else ld.frontsector
                if tsec and tsec.floorpic == texture and not tsec.specialdata:
                    sec    = tsec
                    height += stairsize
                    ok = True
                    break
            if not ok:
                break

    return rtn


# ------------------------------------------------------------------
# Ceiling thinker
# ------------------------------------------------------------------
class CeilingMove(Thinker):
    __slots__ = ('type', 'sector', 'bottomheight', 'topheight', 'speed',
                 'crush', 'direction', 'tag', 'olddirection')
    def __init__(self):
        super().__init__()
        self.type = 0; self.sector = None
        self.bottomheight = 0; self.topheight = 0; self.speed = CEILSPEED
        self.crush = False; self.direction = 0; self.tag = 0; self.olddirection = 0

# ceiling_e
LOWER_TO_FLOOR       = 0
RAISE_TO_HIGHEST     = 1
LOWER_AND_CRUSH      = 2
CRUSH_AND_RAISE      = 3
FAST_CRUSH_AND_RAISE = 4
SILENT_CRUSH_AND_RAISE = 5

def T_MoveCeiling(ceiling: CeilingMove):
    import info as info_mod
    from p_mobj import S_StartSound

    if ceiling.direction == 1:
        res = p_floor.T_MovePlane(ceiling.sector, ceiling.speed,
                          ceiling.topheight, ceiling.crush, 1, 1)
        if ceiling.type in (SILENT_CRUSH_AND_RAISE,) and not (ceiling.sector.soundtraversed):
            pass  # no sound every step for silent
        if res == RESULT_PASTDEST:
            if ceiling.type == RAISE_TO_HIGHEST:
                ceiling.sector.specialdata = None
                ceiling.mark_removed()
                P_RemoveActiveCeiling(ceiling)
            elif ceiling.type in (CRUSH_AND_RAISE, FAST_CRUSH_AND_RAISE, SILENT_CRUSH_AND_RAISE):
                ceiling.direction = -1
        elif res == RESULT_CRUSHED:
            if ceiling.type not in (FAST_CRUSH_AND_RAISE,):
                ceiling.speed = CEILSPEED // 8
    elif ceiling.direction == -1:
        res = p_floor.T_MovePlane(ceiling.sector, ceiling.speed,
                          ceiling.bottomheight, ceiling.crush, 1, -1)
        if res == RESULT_PASTDEST:
            if ceiling.type in (LOWER_TO_FLOOR, LOWER_AND_CRUSH):
                ceiling.sector.specialdata = None
                ceiling.mark_removed()
                P_RemoveActiveCeiling(ceiling)
            elif ceiling.type in (CRUSH_AND_RAISE, FAST_CRUSH_AND_RAISE, SILENT_CRUSH_AND_RAISE):
                ceiling.speed    = ceiling.speed * 2
                ceiling.direction = 1
        else:
            if ceiling.type in (CRUSH_AND_RAISE, FAST_CRUSH_AND_RAISE, SILENT_CRUSH_AND_RAISE):
                if ceiling.speed < CEILSPEED:
                    ceiling.speed = CEILSPEED


def P_AddActiveCeiling(c: CeilingMove):
    for i in range(MAXCEILINGS):
        if activeceilings[i] is None:
            activeceilings[i] = c
            return


def P_RemoveActiveCeiling(c: CeilingMove):
    for i in range(MAXCEILINGS):
        if activeceilings[i] is c:
            activeceilings[i] = None
            return


def EV_DoCeiling(line, ctype: int) -> int:
    import p_setup
    rtn    = 0
    secnum = -1

    if ctype == FAST_CRUSH_AND_RAISE:
        for i in range(MAXCEILINGS):
            if (activeceilings[i] and
                    activeceilings[i].tag == line.tag and
                    activeceilings[i].direction == -1):
                activeceilings[i].olddirection = activeceilings[i].direction
                activeceilings[i].direction     = 0

    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        sec = p_setup.sectors[secnum]
        if sec.specialdata: continue
        rtn = 1

        ceiling = CeilingMove()
        ceiling.type    = ctype
        ceiling.sector  = sec
        ceiling.crush   = False
        ceiling.tag     = sec.tag
        sec.specialdata = ceiling

        if ctype == LOWER_TO_FLOOR:
            ceiling.direction    = -1
            ceiling.topheight    = sec.ceilingheight
            ceiling.bottomheight = sec.floorheight + (8 * FRACUNIT if ceiling.crush else 0)
            ceiling.speed        = CEILSPEED
        elif ctype == RAISE_TO_HIGHEST:
            ceiling.direction = 1
            ceiling.topheight = p_spec.P_FindHighestCeilingSurrounding(sec)
            ceiling.speed     = CEILSPEED
        elif ctype == LOWER_AND_CRUSH:
            ceiling.direction    = -1
            ceiling.crush        = True
            ceiling.topheight    = sec.ceilingheight
            ceiling.bottomheight = sec.floorheight + 8 * FRACUNIT
            ceiling.speed        = CEILSPEED
        elif ctype in (CRUSH_AND_RAISE, SILENT_CRUSH_AND_RAISE):
            ceiling.crush        = True
            ceiling.topheight    = sec.ceilingheight
            ceiling.bottomheight = sec.floorheight + 8 * FRACUNIT
            ceiling.direction    = -1
            ceiling.speed        = CEILSPEED
        elif ctype == FAST_CRUSH_AND_RAISE:
            ceiling.crush        = True
            ceiling.topheight    = sec.ceilingheight
            ceiling.bottomheight = sec.floorheight + 8 * FRACUNIT
            ceiling.direction    = -1
            ceiling.speed        = CEILSPEED * 2

        ceiling.function = T_MoveCeiling
        p_tick.P_AddThinker(ceiling)
        P_AddActiveCeiling(ceiling)

    return rtn


def EV_CeilingCrushStop(line) -> int:
    rtn = 0
    for i in range(MAXCEILINGS):
        if activeceilings[i] and activeceilings[i].tag == line.tag:
            activeceilings[i].olddirection = activeceilings[i].direction
            activeceilings[i].direction    = 0
            rtn = 1
    return rtn


def P_ActivateInStasisCeiling(line):
    for i in range(MAXCEILINGS):
        if (activeceilings[i] and
                activeceilings[i].tag == line.tag and
                activeceilings[i].direction == 0):
            activeceilings[i].direction = activeceilings[i].olddirection


# ------------------------------------------------------------------
# Platform thinker
# ------------------------------------------------------------------
class Plat(Thinker):
    __slots__ = ('sector', 'speed', 'low', 'high', 'wait', 'count',
                 'status', 'oldstatus', 'crush', 'tag', 'type')
    def __init__(self):
        super().__init__()
        self.sector = None; self.speed = PLATSPEED
        self.low = 0; self.high = 0; self.wait = 0; self.count = 0
        self.status = 1; self.oldstatus = 1; self.crush = False
        self.tag = 0; self.type = 0

# plat_e
PLAT_UP = 0; PLAT_DOWN = 1; PLAT_WAITING = 2; PLAT_IN_STASIS = 3
# plattype_e
PERPETUAL_RAISE = 0; DOWN_WAIT_UP_STAY = 1; RAISE_AND_CHANGE = 2
RAISE_TO_NEAREST_AND_CHANGE = 3; BLAZE_DWUS = 4

def T_PlatRaise(plat: Plat):
    import info as info_mod
    from p_mobj import S_StartSound

    if plat.status == PLAT_UP:
        res = p_floor.T_MovePlane(plat.sector, plat.speed, plat.high,
                          plat.crush, 0, 1)
        if plat.type == PERPETUAL_RAISE and res == RESULT_CRUSHED:
            plat.count   = plat.wait
            plat.status  = PLAT_DOWN
            S_StartSound(plat.sector.soundorg, info_mod.sfx_pstart)
        elif res == RESULT_PASTDEST:
            plat.count  = plat.wait
            plat.status = PLAT_WAITING
            S_StartSound(plat.sector.soundorg, info_mod.sfx_pstop)
            if plat.type in (DOWN_WAIT_UP_STAY, BLAZE_DWUS):
                P_RemoveActivePlat(plat)

    elif plat.status == PLAT_DOWN:
        res = p_floor.T_MovePlane(plat.sector, plat.speed, plat.low, False, 0, -1)
        if res == RESULT_PASTDEST:
            plat.count  = plat.wait
            plat.status = PLAT_WAITING
            S_StartSound(plat.sector.soundorg, info_mod.sfx_pstop)

    elif plat.status == PLAT_WAITING:
        plat.count -= 1
        if plat.count == 0:
            plat.status = (PLAT_DOWN if plat.sector.floorheight == plat.low
                           else PLAT_UP)
            S_StartSound(plat.sector.soundorg, info_mod.sfx_pstart)


def P_AddActivePlat(plat: Plat):
    for i in range(MAXPLATS):
        if activeplats[i] is None:
            activeplats[i] = plat
            return


def P_RemoveActivePlat(plat: Plat):
    for i in range(MAXPLATS):
        if activeplats[i] is plat:
            activeplats[i] = None
            plat.sector.specialdata = None
            plat.mark_removed()
            return


def P_ActivateInStasis(tag: int):
    for i in range(MAXPLATS):
        if activeplats[i] and activeplats[i].tag == tag and activeplats[i].status == PLAT_IN_STASIS:
            activeplats[i].status = activeplats[i].oldstatus
            activeplats[i].function = T_PlatRaise


def EV_StopPlat(line):
    for i in range(MAXPLATS):
        if activeplats[i] and activeplats[i].status != PLAT_IN_STASIS and activeplats[i].tag == line.tag:
            activeplats[i].oldstatus = activeplats[i].status
            activeplats[i].status    = PLAT_IN_STASIS
            activeplats[i].function  = None


def EV_DoPlat(line, ptype: int, amount: int) -> int:
    import p_setup, info as info_mod
    from p_mobj import S_StartSound
    rtn    = 0
    secnum = -1

    P_ActivateInStasis(line.tag)

    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        sec = p_setup.sectors[secnum]
        if sec.specialdata: continue
        rtn = 1

        plat = Plat()
        plat.type   = ptype
        plat.sector = sec
        plat.crush  = False
        plat.tag    = line.tag
        sec.specialdata = plat

        if ptype == PERPETUAL_RAISE:
            plat.low   = p_spec.P_FindLowestFloorSurrounding(sec)
            if plat.low > sec.floorheight: plat.low = sec.floorheight
            plat.high  = p_spec.P_FindHighestFloorSurrounding(sec)
            if plat.high < sec.floorheight: plat.high = sec.floorheight
            plat.wait  = 35 * PLATWAIT
            plat.speed = PLATSPEED
            plat.status = PLAT_UP if (p_setup.rndindex & 1) else PLAT_DOWN
        elif ptype == DOWN_WAIT_UP_STAY:
            plat.speed = PLATSPEED * 4
            plat.low   = p_spec.P_FindLowestFloorSurrounding(sec)
            if plat.low > sec.floorheight: plat.low = sec.floorheight
            plat.high  = sec.floorheight
            plat.wait  = 35 * PLATWAIT
            plat.status = PLAT_DOWN
        elif ptype == RAISE_AND_CHANGE:
            plat.speed  = PLATSPEED / 2
            plat.high   = sec.floorheight + amount * FRACUNIT
            plat.wait   = 0
            plat.status = PLAT_UP
        elif ptype == RAISE_TO_NEAREST_AND_CHANGE:
            plat.speed  = PLATSPEED / 2
            plat.high   = p_spec.P_FindNextHighestFloor(sec, sec.floorheight)
            plat.wait   = 0
            plat.status = PLAT_UP
            sec.special = line.frontsector.special if line.frontsector else 0
            sec.floorpic = line.frontsector.floorpic if line.frontsector else sec.floorpic
        elif ptype == BLAZE_DWUS:
            plat.speed = PLATSPEED * 8
            plat.low   = p_spec.P_FindLowestFloorSurrounding(sec)
            if plat.low > sec.floorheight: plat.low = sec.floorheight
            plat.high  = sec.floorheight
            plat.wait  = 35 * PLATWAIT
            plat.status = PLAT_DOWN

        S_StartSound(sec.soundorg, info_mod.sfx_pstart)
        plat.function = T_PlatRaise
        p_tick.P_AddThinker(plat)
        P_AddActivePlat(plat)

    return rtn


# ------------------------------------------------------------------
# Lighting thinkers
# ------------------------------------------------------------------
class FireFlicker(Thinker):
    __slots__ = ('sector', 'count', 'maxlight', 'minlight')
    def __init__(self): super().__init__(); self.sector=None; self.count=0; self.maxlight=0; self.minlight=0

class LightFlash(Thinker):
    __slots__ = ('sector', 'count', 'maxlight', 'minlight', 'maxtime', 'mintime')
    def __init__(self): super().__init__(); self.sector=None; self.count=0; self.maxlight=0; self.minlight=0; self.maxtime=0; self.mintime=0

class Strobe(Thinker):
    __slots__ = ('sector', 'count', 'minlight', 'maxlight', 'darktime', 'brighttime')
    def __init__(self): super().__init__(); self.sector=None; self.count=0; self.minlight=0; self.maxlight=0; self.darktime=0; self.brighttime=0

class Glow(Thinker):
    __slots__ = ('sector', 'minlight', 'maxlight', 'direction')
    def __init__(self): super().__init__(); self.sector=None; self.minlight=0; self.maxlight=0; self.direction=0


def T_FireFlicker(flicker: FireFlicker):
    from m_random import P_Random
    if flicker.count > 0:
        flicker.count -= 1
        return
    amount = (P_Random() & 3) * 16
    if flicker.sector.lightlevel - amount < flicker.minlight:
        flicker.sector.lightlevel = flicker.minlight
    else:
        flicker.sector.lightlevel = flicker.maxlight - amount
    flicker.count = 4

def P_SpawnFireFlicker(sector):
    ff = FireFlicker()
    ff.sector   = sector
    ff.maxlight = sector.lightlevel
    ff.minlight = P_FindMinSurroundingLight(sector, sector.lightlevel) + 16
    ff.count    = 4
    ff.function = T_FireFlicker
    p_tick.P_AddThinker(ff)


def T_LightFlash(flash: LightFlash):
    if flash.count > 0:
        flash.count -= 1
        return
    if flash.sector.lightlevel == flash.maxlight:
        flash.sector.lightlevel = flash.minlight
        flash.count = (flash.mintime // 4) + 1
    else:
        flash.sector.lightlevel = flash.maxlight
        flash.count = (flash.maxtime // 4) + 1

def P_SpawnLightFlash(sector):
    from m_random import P_Random
    lf = LightFlash()
    lf.sector   = sector
    lf.maxlight = sector.lightlevel
    lf.minlight = P_FindMinSurroundingLight(sector, sector.lightlevel)
    lf.maxtime  = 64
    lf.mintime  = 7
    lf.count    = (P_Random() & lf.maxtime) + 1
    lf.function = T_LightFlash
    p_tick.P_AddThinker(lf)


def T_StrobeFlash(flash: Strobe):
    if flash.count > 0:
        flash.count -= 1
        return
    if flash.sector.lightlevel == flash.minlight:
        flash.sector.lightlevel = flash.maxlight
        flash.count = flash.brighttime
    else:
        flash.sector.lightlevel = flash.minlight
        flash.count = flash.darktime

def P_SpawnStrobeFlash(sector, fastOrSlow: int, inSync: int):
    from m_random import P_Random
    ss = Strobe()
    ss.sector     = sector
    ss.darktime   = fastOrSlow
    ss.brighttime = STROBEBRIGHT
    ss.maxlight   = sector.lightlevel
    ss.minlight   = P_FindMinSurroundingLight(sector, sector.lightlevel)
    if ss.minlight == ss.maxlight:
        ss.minlight = 0
    ss.count    = 1 if inSync else (P_Random() & 7) + 1
    ss.function = T_StrobeFlash
    p_tick.P_AddThinker(ss)


def EV_StartLightStrobing(line):
    import p_setup
    secnum = -1
    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        sec = p_setup.sectors[secnum]
        if not sec.specialdata:
            P_SpawnStrobeFlash(sec, SLOWDARK, 0)


def EV_TurnTagLightsOff(line):
    import p_setup
    for i in range(len(p_setup.sectors)):
        if p_setup.sectors[i].tag == line.tag:
            min_l = p_setup.sectors[i].lightlevel
            for ld in p_setup.sectors[i].lines:
                other = getNextSector(ld, p_setup.sectors[i])
                if other and other.lightlevel < min_l:
                    min_l = other.lightlevel
            p_setup.sectors[i].lightlevel = min_l


def EV_LightTurnOn(line, bright: int):
    import p_setup
    for i in range(len(p_setup.sectors)):
        if p_setup.sectors[i].tag == line.tag:
            if bright == 0:
                bright = p_setup.sectors[i].lightlevel
                for ld in p_setup.sectors[i].lines:
                    other = getNextSector(ld, p_setup.sectors[i])
                    if other and other.lightlevel > bright:
                        bright = other.lightlevel
            p_setup.sectors[i].lightlevel = bright


def T_Glow(g: Glow):
    if g.direction == -1:
        g.sector.lightlevel -= GLOWSPEED
        if g.sector.lightlevel <= g.minlight:
            g.sector.lightlevel += GLOWSPEED
            g.direction = 1
    else:
        g.sector.lightlevel += GLOWSPEED
        if g.sector.lightlevel >= g.maxlight:
            g.sector.lightlevel -= GLOWSPEED
            g.direction = -1

def P_SpawnGlowingLight(sector):
    g = Glow()
    g.sector    = sector
    g.minlight  = P_FindMinSurroundingLight(sector, sector.lightlevel)
    g.maxlight  = sector.lightlevel
    g.direction = -1
    g.function  = T_Glow
    p_tick.P_AddThinker(g)


# ------------------------------------------------------------------
# Teleport
# ------------------------------------------------------------------
def EV_Teleport(line, side: int, thing) -> int:
    import p_setup
    from p_mobj import P_SpawnMobj, P_SetMobjState, S_StartSound
    from p_map import P_TeleportMove
    from r_main import R_PointToAngle2
    import info as info_mod
    from d_think import thinkercap
    from p_mobj import Mobj

    if side or not (thing.flags & 0x4):   # MF_SHOOTABLE shortcut
        pass  # always allow teleport

    for mo in thinkercap:
        if not isinstance(mo, Mobj): continue
        if mo.type != info_mod.MT_TELEPORTMAN: continue
        sec = mo.subsector.sector
        if sec.tag != line.tag: continue

        # Spawn fog at old position
        fog = P_SpawnMobj(thing.x, thing.y,
                          thing.subsector.sector.floorheight,
                          info_mod.MT_TFOG)
        S_StartSound(fog, info_mod.sfx_telept)

        if not P_TeleportMove(thing, mo.x, mo.y):
            return 0

        thing.z        = thing.floorz
        fog2 = P_SpawnMobj(mo.x, mo.y, thing.z, info_mod.MT_TFOG)
        S_StartSound(fog2, info_mod.sfx_telept)

        if thing.player:
            thing.player.viewz     = thing.z + thing.player.viewheight
            thing.player.attacker  = None
        thing.angle        = mo.angle
        thing.reactiontime = 18

        if thing.player:
            thing.momx = thing.momy = thing.momz = 0
        return 1

    return 0


# ------------------------------------------------------------------
# P_PlayerInSpecialSector
# ------------------------------------------------------------------
def P_PlayerInSpecialSector(player):
    import doomstat
    from p_inter import P_DamageMobj
    from m_random import P_Random
    from doomdef import PowerType, CheatFlags
    from g_game import G_ExitLevel

    sector = player.mo.subsector.sector
    if player.mo.z != sector.floorheight:
        return

    sp = sector.special
    if sp == 5:      # hell slime
        if not player.powers[PowerType.IRONFEET]:
            if not (doomstat.leveltime & 0x1f):
                P_DamageMobj(player.mo, None, None, 10)
    elif sp == 7:    # nukage
        if not player.powers[PowerType.IRONFEET]:
            if not (doomstat.leveltime & 0x1f):
                P_DamageMobj(player.mo, None, None, 5)
    elif sp in (4, 16):  # strobe hurt / super hell slime
        if (not player.powers[PowerType.IRONFEET] or P_Random() < 5):
            if not (doomstat.leveltime & 0x1f):
                P_DamageMobj(player.mo, None, None, 20)
    elif sp == 9:    # secret sector
        player.secretcount += 1
        sector.special = 0
    elif sp == 11:   # exit super damage
        player.cheats &= ~CheatFlags.GODMODE
        if not (doomstat.leveltime & 0x1f):
            P_DamageMobj(player.mo, None, None, 20)
        if player.health <= 10:
            G_ExitLevel()


# ------------------------------------------------------------------
# P_UpdateSpecials
# ------------------------------------------------------------------
def P_UpdateSpecials():
    import doomstat
    from r_data import texturetranslation, flattranslation
    from p_mobj import S_StartSound
    import info as info_mod
    from g_game import G_ExitLevel

    if levelTimer:
        global levelTimeCount
        levelTimeCount -= 1
        if not levelTimeCount:
            G_ExitLevel()

    for anim in anims:
        for i in range(anim.basepic, anim.basepic + anim.numpics):
            pic = anim.basepic + ((doomstat.leveltime // anim.speed + i) % anim.numpics)
            if anim.istexture:
                texturetranslation[i] = pic
            else:
                flattranslation[i] = pic

    import p_setup
    for ld in linespeciallist[:numlinespecials]:
        if ld.special == 48:
            p_setup.sides[ld.sidenum[0]].textureoffset += FRACUNIT

    for btn in buttonlist:
        if btn.btimer:
            btn.btimer -= 1
            if not btn.btimer:
                import p_setup as ps
                sd = ps.sides[btn.line.sidenum[0]]
                if btn.where == 0:   sd.toptexture    = btn.btexture
                elif btn.where == 1: sd.midtexture    = btn.btexture
                elif btn.where == 2: sd.bottomtexture = btn.btexture
                S_StartSound(btn.soundorg, info_mod.sfx_swtchn)
                btn.line = None; btn.btimer = 0


# ------------------------------------------------------------------
# P_CrossSpecialLine
# ------------------------------------------------------------------
def P_CrossSpecialLine(linenum: int, side: int, thing):
    import p_setup, doomstat
    from doomdef import GameVersion
    import info as info_mod

    line = p_setup.lines[linenum]

    if doomstat.gameversion <= GameVersion.EXE_DOOM_1_7:
        if line.special > 98 and line.special != 104:
            return
    else:
        if not thing.player:
            skip = {info_mod.MT_ROCKET, info_mod.MT_PLASMA, info_mod.MT_BFG,
                    info_mod.MT_TROOPSHOT, info_mod.MT_HEADSHOT, info_mod.MT_BRUISERSHOT}
            if thing.type in skip:
                return

    if not thing.player:
        ok = line.special in (39, 97, 125, 126, 4, 10, 88)
        if not ok:
            return

    sp = line.special
    # One-shot triggers clear special after firing
    _one_shot = {
        2: (lambda: p_doors.EV_DoDoor(line, VLD_OPEN)),
        3: (lambda: p_doors.EV_DoDoor(line, VLD_CLOSE)),
        4: (lambda: p_doors.EV_DoDoor(line, VLD_NORMAL)),
        5: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR)),
        6: (lambda: p_ceilng.EV_DoCeiling(line, FAST_CRUSH_AND_RAISE)),
        8: (lambda: EV_BuildStairs(line, 0)),
        10: (lambda: p_plats.EV_DoPlat(line, DOWN_WAIT_UP_STAY, 0)),
        12: (lambda: EV_LightTurnOn(line, line.frontsector.lightlevel if line.frontsector else 0)),
        13: (lambda: EV_LightTurnOn(line, 255)),
        16: (lambda: p_doors.EV_DoDoor(line, VLD_CLOSE)),
        17: (lambda: EV_StartLightStrobing(line)),
        19: (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR)),
        22: (lambda: p_plats.EV_DoPlat(line, RAISE_AND_CHANGE, 0)),
        25: (lambda: p_ceilng.EV_DoCeiling(line, CRUSH_AND_RAISE)),
        30: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_24)),
        35: (lambda: EV_LightTurnOn(line, 35)),
        36: (lambda: p_floor.EV_DoFloor(line, TURBO_LOWER)),
        37: (lambda: p_floor.EV_DoFloor(line, LOWER_AND_CHANGE)),
        38: (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR_LOWEST)),
        39: (lambda: EV_Teleport(line, side, thing)),
        40: (lambda: p_ceilng.EV_DoCeiling(line, RAISE_TO_HIGHEST)),
        41: (lambda: p_ceilng.EV_DoCeiling(line, LOWER_TO_FLOOR)),
        44: (lambda: p_ceilng.EV_DoCeiling(line, LOWER_AND_CRUSH)),
        52: (lambda: _exit_level()),
        53: (lambda: p_plats.EV_DoPlat(line, PERPETUAL_RAISE, 0)),
        54: (lambda: EV_StopPlat(line)),
        56: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_CRUSH)),
        57: (lambda: EV_CeilingCrushStop(line)),
        58: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_24)),
        59: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_24_CHANGE)),
        104: (lambda: EV_TurnTagLightsOff(line)),
        108: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZERAISE)),
        109: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZEOPEN)),
        100: (lambda: EV_BuildStairs(line, 1)),
        110: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZECLOSE)),
        119: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_NEAREST)),
        121: (lambda: p_plats.EV_DoPlat(line, BLAZE_DWUS, 0)),
        124: (lambda: _secret_exit()),
        125: (lambda: EV_Teleport(line, side, thing) if not thing.player else None),
        130: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_TURBO)),
        141: (lambda: p_ceilng.EV_DoCeiling(line, SILENT_CRUSH_AND_RAISE)),
    }
    _retrigger = {
        72:  (lambda: p_ceilng.EV_DoCeiling(line, LOWER_AND_CRUSH)),
        73:  (lambda: p_ceilng.EV_DoCeiling(line, CRUSH_AND_RAISE)),
        74:  (lambda: EV_CeilingCrushStop(line)),
        75:  (lambda: p_doors.EV_DoDoor(line, VLD_CLOSE)),
        76:  (lambda: p_doors.EV_DoDoor(line, VLD_CLOSE)),
        77:  (lambda: p_ceilng.EV_DoCeiling(line, FAST_CRUSH_AND_RAISE)),
        79:  (lambda: EV_LightTurnOn(line, 35)),
        80:  (lambda: EV_LightTurnOn(line, line.frontsector.lightlevel if line.frontsector else 0)),
        81:  (lambda: EV_LightTurnOn(line, 255)),
        82:  (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR_LOWEST)),
        83:  (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR)),
        84:  (lambda: p_floor.EV_DoFloor(line, LOWER_AND_CHANGE)),
        86:  (lambda: p_doors.EV_DoDoor(line, VLD_OPEN)),
        87:  (lambda: p_plats.EV_DoPlat(line, PERPETUAL_RAISE, 0)),
        88:  (lambda: p_plats.EV_DoPlat(line, DOWN_WAIT_UP_STAY, 0)),
        89:  (lambda: EV_StopPlat(line)),
        90:  (lambda: p_doors.EV_DoDoor(line, VLD_NORMAL)),
        91:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR)),
        92:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_24)),
        93:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_24_CHANGE)),
        94:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_CRUSH)),
        95:  (lambda: p_plats.EV_DoPlat(line, RAISE_TO_NEAREST_AND_CHANGE, 0)),
        96:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_TURBO)),
        97:  (lambda: EV_Teleport(line, side, thing)),
        98:  (lambda: p_floor.EV_DoFloor(line, TURBO_LOWER)),
        105: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZERAISE)),
        106: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZEOPEN)),
        107: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZECLOSE)),
        120: (lambda: p_plats.EV_DoPlat(line, BLAZE_DWUS, 0)),
        126: (lambda: EV_Teleport(line, side, thing) if not thing.player else None),
        128: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_NEAREST)),
        129: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_TURBO)),
    }

    if sp in _one_shot:
        _one_shot[sp]()
        line.special = 0
    elif sp in _retrigger:
        _retrigger[sp]()


def _exit_level():
    from g_game import G_ExitLevel
    G_ExitLevel()

def _secret_exit():
    from g_game import G_SecretExitLevel
    G_SecretExitLevel()


# ------------------------------------------------------------------
# P_UseSpecialLine
# ------------------------------------------------------------------
def P_UseSpecialLine(thing, line, side: int) -> bool:
    import p_setup, info as info_mod
    from p_mobj import S_StartSound

    if not thing.player and line.special not in (1, 32, 33, 34, 117, 118):
        if line.special not in (46,):
            return False

    sp = line.special
    # Door actions by special number
    _door_map = {
        1:   (VLD_NORMAL,     False),
        26:  (VLD_NORMAL,     True),
        27:  (VLD_NORMAL,     True),
        28:  (VLD_NORMAL,     True),
        31:  (VLD_OPEN,       False),
        32:  (VLD_OPEN,       True),
        33:  (VLD_OPEN,       True),
        34:  (VLD_OPEN,       True),
        117: (VLD_BLAZERAISE, False),
        118: (VLD_BLAZEOPEN,  False),
    }
    if sp in _door_map:
        dtype, locked = _door_map[sp]
        if locked:
            return bool(EV_DoLockedDoor(line, dtype, thing))
        else:
            EV_VerticalDoor(line, thing)
            return True

    _use_map = {
        7:   (lambda: EV_BuildStairs(line, 0)),
        9:   (lambda: EV_DoDonut(line)),
        11:  (lambda: _exit_level()),
        14:  (lambda: p_plats.EV_DoPlat(line, RAISE_AND_CHANGE, 32)),
        15:  (lambda: p_plats.EV_DoPlat(line, RAISE_AND_CHANGE, 24)),
        18:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_NEAREST)),
        20:  (lambda: p_plats.EV_DoPlat(line, RAISE_TO_NEAREST_AND_CHANGE, 0)),
        21:  (lambda: p_plats.EV_DoPlat(line, DOWN_WAIT_UP_STAY, 0)),
        23:  (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR_LOWEST)),
        29:  (lambda: p_doors.EV_DoDoor(line, VLD_NORMAL)),
        30:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_24)),
        38:  (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR_LOWEST)),
        41:  (lambda: p_ceilng.EV_DoCeiling(line, LOWER_TO_FLOOR)),
        42:  (lambda: p_doors.EV_DoDoor(line, VLD_CLOSE)),
        43:  (lambda: p_ceilng.EV_DoCeiling(line, LOWER_TO_FLOOR)),
        45:  (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR)),
        49:  (lambda: p_ceilng.EV_DoCeiling(line, FAST_CRUSH_AND_RAISE)),
        50:  (lambda: p_doors.EV_DoDoor(line, VLD_CLOSE)),
        51:  (lambda: _secret_exit()),
        55:  (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_CRUSH)),
        101: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR)),
        102: (lambda: p_floor.EV_DoFloor(line, LOWER_FLOOR)),
        103: (lambda: p_doors.EV_DoDoor(line, VLD_OPEN)),
        111: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZERAISE)),
        112: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZEOPEN)),
        113: (lambda: p_doors.EV_DoDoor(line, VLD_BLAZECLOSE)),
        122: (lambda: p_plats.EV_DoPlat(line, BLAZE_DWUS, 0)),
        127: (lambda: EV_BuildStairs(line, 1)),
        131: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_TURBO)),
        133: (lambda: EV_DoLockedDoor(line, VLD_BLAZEOPEN, thing)),
        135: (lambda: EV_DoLockedDoor(line, VLD_BLAZEOPEN, thing)),
        137: (lambda: EV_DoLockedDoor(line, VLD_BLAZEOPEN, thing)),
        140: (lambda: p_floor.EV_DoFloor(line, RAISE_FLOOR_512)),
    }

    if sp in _use_map:
        result = _use_map[sp]()
        if result:
            P_ChangeSwitchTexture(line, sp in (
                9, 14, 15, 18, 20, 21, 23, 29, 30, 38, 41, 42,
                43, 45, 49, 50, 55, 101, 102, 103, 111, 112,
                113, 122, 127, 131, 133, 135, 137, 140))
        return bool(result)

    return False


# ------------------------------------------------------------------
# P_ShootSpecialLine
# ------------------------------------------------------------------
def P_ShootSpecialLine(thing, line):
    if not thing.player:
        if line.special != 46:
            return

    sp = line.special
    if sp == 24:
        p_floor.EV_DoFloor(line, RAISE_FLOOR)
        P_ChangeSwitchTexture(line, False)
    elif sp == 46:
        p_doors.EV_DoDoor(line, VLD_OPEN)
        P_ChangeSwitchTexture(line, True)
    elif sp == 47:
        p_plats.EV_DoPlat(line, RAISE_TO_NEAREST_AND_CHANGE, 0)
        P_ChangeSwitchTexture(line, False)


# ------------------------------------------------------------------
# EV_DoDonut
# ------------------------------------------------------------------
def EV_DoDonut(line) -> int:
    import p_setup
    secnum = -1
    rtn    = 0

    while True:
        secnum = p_spec.P_FindSectorFromLineTag(line, secnum)
        if secnum < 0: break
        s1 = p_setup.sectors[secnum]
        if s1.specialdata: continue
        rtn = 1

        s2 = getNextSector(s1.lines[0], s1)
        if s2 is None: break

        for ld in s2.lines:
            s3 = ld.backsector
            if s3 is s1: continue
            if s3 is None:
                s3_fh = 0; s3_fp = 0x16
            else:
                s3_fh = s3.floorheight
                s3_fp = s3.floorpic

            # Raise s2
            floor2 = FloorMove()
            floor2.sector        = s2
            floor2.type          = DONUT_RAISE
            floor2.crush         = False
            floor2.direction     = 1
            floor2.speed         = FLOORSPEED // 2
            floor2.texture       = s3_fp
            floor2.newspecial    = 0
            floor2.floordestheight = s3_fh
            s2.specialdata       = floor2
            floor2.function      = T_MoveFloor
            p_tick.P_AddThinker(floor2)

            # Lower s1 (donut hole)
            floor1 = FloorMove()
            floor1.sector        = s1
            floor1.type          = LOWER_FLOOR
            floor1.crush         = False
            floor1.direction     = -1
            floor1.speed         = FLOORSPEED // 2
            floor1.texture       = s1.floorpic
            floor1.newspecial    = 0
            floor1.floordestheight = s3_fh
            s1.specialdata       = floor1
            floor1.function      = T_MoveFloor
            p_tick.P_AddThinker(floor1)
            break

    return rtn


# ------------------------------------------------------------------
# P_SpawnSpecials  — called at level load
# ------------------------------------------------------------------
def P_SpawnSpecials():
    import p_setup, doomstat
    from doomdef import GameVersion

    global levelTimer, levelTimeCount, numlinespecials

    if doomstat.timelimit > 0 and doomstat.deathmatch:
        levelTimer     = True
        levelTimeCount = doomstat.timelimit * 60 * TICRATE
    else:
        levelTimer = False

    for i, sec in enumerate(p_setup.sectors):
        sp = sec.special
        if not sp: continue
        if sp == 1:   P_SpawnLightFlash(sec)
        elif sp == 2: P_SpawnStrobeFlash(sec, FASTDARK, 0)
        elif sp == 3: P_SpawnStrobeFlash(sec, SLOWDARK, 0)
        elif sp == 4:
            P_SpawnStrobeFlash(sec, FASTDARK, 0)
            sec.special = 4
        elif sp == 8: P_SpawnGlowingLight(sec)
        elif sp == 9: doomstat.totalsecret += 1
        elif sp == 10: P_SpawnDoorCloseIn30(sec)
        elif sp == 12: P_SpawnStrobeFlash(sec, SLOWDARK, 1)
        elif sp == 13: P_SpawnStrobeFlash(sec, FASTDARK, 1)
        elif sp == 14: P_SpawnDoorRaiseIn5Mins(sec, i)
        elif sp == 17:
            if doomstat.gameversion > GameVersion.EXE_DOOM_1_7:
                P_SpawnFireFlicker(sec)

    numlinespecials = 0
    linespeciallist.clear()
    for ld in p_setup.lines:
        if ld.special == 48:
            if numlinespecials < MAXLINEANIMS:
                linespeciallist.append(ld)
                numlinespecials += 1

    for i in range(MAXCEILINGS):
        activeceilings[i] = None
    for i in range(MAXPLATS):
        activeplats[i] = None
    for btn in buttonlist:
        btn.line = None; btn.btimer = 0
