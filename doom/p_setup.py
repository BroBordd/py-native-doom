import p_ceilng
import p_floor
import p_tick
import p_spec
# p_setup.py
# Level setup: load all map lumps and build runtime geometry
# Ported from p_setup.c / p_setup.h

import struct
from doomdef import (
    FRACBITS, FRACUNIT, MAXRADIUS,
    ML_THINGS, ML_LINEDEFS, ML_SIDEDEFS, ML_VERTEXES,
    ML_SEGS, ML_SSECTORS, ML_NODES, ML_SECTORS,
    ML_REJECT, ML_BLOCKMAP,
    ML_TWOSIDED, ML_SECRET,
    NF_SUBSECTOR,
    GameMode, MAXPLAYERS,
)
from doomdata import (
    MapVertex, MapSeg, MapSubsector, MapNode,
    MapSector, MapSidedef, MapLinedef, MapThing,
    load_lump_array,
)
from r_defs import (
    Vertex, Sector, Side, Line, Subsector, Seg, Node,
    SlopeType,
    BOXTOP, BOXBOTTOM, BOXLEFT, BOXRIGHT,
)
from d_think import thinkercap
from doomdef import fixed_mul

# ------------------------------------------------------------------
# Map geometry globals  (equivalents of the C globals in p_setup.c)
# ------------------------------------------------------------------
vertexes:   list  = []
segs:       list  = []
sectors:    list  = []
subsectors: list  = []
nodes:      list  = []
lines:      list  = []
sides:      list  = []

# Blockmap
bmapwidth  = 0
bmapheight = 0
bmaporgx   = 0
bmaporgy   = 0
blockmap: list = []          # list of lists of line indices per cell
blockmaplump: list = []      # raw signed shorts (header + offsets + lists)
blocklinks: list = []        # list[Mobj|None], one per block cell

# Reject matrix
rejectmatrix: bytes = b''

MAPBLOCKSHIFT = FRACBITS + 7   # = 23  (128 map units per block)
MAPBLOCKUNITS = 128


# ------------------------------------------------------------------
# Forward-declared callbacks (filled by r_data.py / r_main.py)
# ------------------------------------------------------------------
def _stub(name):
    def f(*a):
        raise RuntimeError(f'{name} not initialised — check import order')
    f.__name__ = name
    return f

R_FlatNumForName    = _stub('R_FlatNumForName')
R_TextureNumForName = _stub('R_TextureNumForName')
R_PrecacheLevel     = _stub('R_PrecacheLevel')
R_InitSprites       = _stub('R_InitSprites')
P_InitSwitchList    = _stub('P_InitSwitchList')
P_InitPicAnims      = _stub('P_InitPicAnims')
P_SpawnSpecials     = _stub('P_SpawnSpecials')
P_SpawnMapThing     = _stub('P_SpawnMapThing')
G_DeathMatchSpawnPlayer = _stub('G_DeathMatchSpawnPlayer')
S_Start             = _stub('S_Start')


# ------------------------------------------------------------------
# Bounding box helpers  (m_bbox.h equivalent)
# ------------------------------------------------------------------
_MAXINT = 0x7FFFFFFF
_MININT = -0x80000000

def M_ClearBox(bbox: list):
    bbox[BOXTOP]    = _MININT
    bbox[BOXBOTTOM] = _MAXINT
    bbox[BOXLEFT]   = _MAXINT
    bbox[BOXRIGHT]  = _MININT

def M_AddToBox(bbox: list, x: int, y: int):
    if x < bbox[BOXLEFT]:   bbox[BOXLEFT]   = x
    if x > bbox[BOXRIGHT]:  bbox[BOXRIGHT]  = x
    if y < bbox[BOXBOTTOM]: bbox[BOXBOTTOM] = y
    if y > bbox[BOXTOP]:    bbox[BOXTOP]    = y


# ------------------------------------------------------------------
# "Null sector" for glass-hack sidedefs with invalid indices
# ------------------------------------------------------------------
_null_sector = Sector()


# ------------------------------------------------------------------
# P_LoadVertexes
# ------------------------------------------------------------------
def P_LoadVertexes(lump_data: bytes):
    global vertexes
    raw_verts = load_lump_array(lump_data, MapVertex)
    vertexes = []
    for mv in raw_verts:
        v = Vertex(mv.x << FRACBITS, mv.y << FRACBITS)
        vertexes.append(v)


# ------------------------------------------------------------------
# P_LoadSectors
# ------------------------------------------------------------------
def P_LoadSectors(lump_data: bytes):
    global sectors
    raw = load_lump_array(lump_data, MapSector)
    sectors = []
    for ms in raw:
        s = Sector()
        s.floorheight   = ms.floorheight   << FRACBITS
        s.ceilingheight = ms.ceilingheight << FRACBITS
        s.floorpic      = R_FlatNumForName(ms.floorpic)
        s.ceilingpic    = R_FlatNumForName(ms.ceilingpic)
        s.lightlevel    = ms.lightlevel
        s.special       = ms.special
        s.tag           = ms.tag
        s.thinglist     = None
        sectors.append(s)


# ------------------------------------------------------------------
# P_LoadSideDefs
# ------------------------------------------------------------------
def P_LoadSideDefs(lump_data: bytes):
    global sides
    raw = load_lump_array(lump_data, MapSidedef)
    sides = []
    for msd in raw:
        sd = Side()
        sd.textureoffset = msd.textureoffset << FRACBITS
        sd.rowoffset     = msd.rowoffset     << FRACBITS
        sd.toptexture    = R_TextureNumForName(msd.toptexture)
        sd.bottomtexture = R_TextureNumForName(msd.bottomtexture)
        sd.midtexture    = R_TextureNumForName(msd.midtexture)
        sd.sector        = sectors[msd.sector]
        sides.append(sd)


# ------------------------------------------------------------------
# P_LoadLineDefs
# ------------------------------------------------------------------
def P_LoadLineDefs(lump_data: bytes):
    global lines
    from doomdef import fixed_mul as _fm
    raw = load_lump_array(lump_data, MapLinedef)
    lines = []
    for mld in raw:
        ld = Line()
        ld.flags   = mld.flags
        ld.special = mld.special
        ld.tag     = mld.tag

        v1 = vertexes[mld.v1]
        v2 = vertexes[mld.v2]
        ld.v1 = v1
        ld.v2 = v2
        ld.dx  = v2.x - v1.x
        ld.dy  = v2.y - v1.y

        # slope type
        if ld.dx == 0:
            ld.slopetype = SlopeType.VERTICAL
        elif ld.dy == 0:
            ld.slopetype = SlopeType.HORIZONTAL
        else:
            from doomdef import fixed_div
            if fixed_div(ld.dy, ld.dx) > 0:
                ld.slopetype = SlopeType.POSITIVE
            else:
                ld.slopetype = SlopeType.NEGATIVE

        # bounding box
        if v1.x < v2.x:
            ld.bbox[BOXLEFT]  = v1.x;  ld.bbox[BOXRIGHT] = v2.x
        else:
            ld.bbox[BOXLEFT]  = v2.x;  ld.bbox[BOXRIGHT] = v1.x
        if v1.y < v2.y:
            ld.bbox[BOXBOTTOM] = v1.y; ld.bbox[BOXTOP]   = v2.y
        else:
            ld.bbox[BOXBOTTOM] = v2.y; ld.bbox[BOXTOP]   = v1.y

        ld.sidenum = (mld.sidenum[0], mld.sidenum[1])

        ld.frontsector = sides[mld.sidenum[0]].sector if mld.sidenum[0] != -1 else None
        ld.backsector  = sides[mld.sidenum[1]].sector if mld.sidenum[1] != -1 else None

        lines.append(ld)

    # count secret lines for doomstat
    import doomstat
    doomstat.totalsecret = sum(1 for l in lines if l.flags & ML_SECRET)


# ------------------------------------------------------------------
# P_LoadSubsectors
# ------------------------------------------------------------------
def P_LoadSubsectors(lump_data: bytes):
    global subsectors
    raw = load_lump_array(lump_data, MapSubsector)
    subsectors = []
    for ms in raw:
        ss = Subsector()
        ss.numlines  = ms.numsegs
        ss.firstline = ms.firstseg
        subsectors.append(ss)


# ------------------------------------------------------------------
# P_LoadNodes
# ------------------------------------------------------------------
def P_LoadNodes(lump_data: bytes):
    global nodes
    raw = load_lump_array(lump_data, MapNode)
    nodes = []
    for mn in raw:
        no = Node()
        no.x  = mn.x  << FRACBITS
        no.y  = mn.y  << FRACBITS
        no.dx = mn.dx << FRACBITS
        no.dy = mn.dy << FRACBITS
        for j in range(2):
            no.children[j] = mn.children[j]
            for k in range(4):
                no.bbox[j][k] = mn.bbox[j][k] << FRACBITS
        nodes.append(no)


# ------------------------------------------------------------------
# P_LoadSegs
# ------------------------------------------------------------------
def P_LoadSegs(lump_data: bytes):
    global segs
    raw = load_lump_array(lump_data, MapSeg)
    segs = []
    for ms in raw:
        seg = Seg()
        seg.v1     = vertexes[ms.v1]
        seg.v2     = vertexes[ms.v2]
        seg.angle  = ms.angle  << FRACBITS
        seg.offset = ms.offset << FRACBITS

        ldef = lines[ms.linedef]
        seg.linedef = ldef
        side = ms.side

        if not (0 <= ldef.sidenum[side] < len(sides)):
            raise ValueError(
                f'P_LoadSegs: linedef {ms.linedef} seg {len(segs)} '
                f'references non-existent sidedef {ldef.sidenum[side]}')

        seg.sidedef     = sides[ldef.sidenum[side]]
        seg.frontsector = sides[ldef.sidenum[side]].sector

        if ldef.flags & ML_TWOSIDED:
            other = ldef.sidenum[side ^ 1]
            if other < 0 or other >= len(sides):
                seg.backsector = _null_sector
            else:
                seg.backsector = sides[other].sector
        else:
            seg.backsector = None

        segs.append(seg)


# ------------------------------------------------------------------
# P_LoadBlockMap
# ------------------------------------------------------------------
def P_LoadBlockMap(lump_data: bytes):
    global bmaporgx, bmaporgy, bmapwidth, bmapheight
    global blockmaplump, blockmap, blocklinks

    count = len(lump_data) // 2
    # unpack as signed shorts
    raw = list(struct.unpack_from(f'<{count}h', lump_data))

    blockmaplump = raw
    bmaporgx  = raw[0] << FRACBITS
    bmaporgy  = raw[1] << FRACBITS
    bmapwidth  = raw[2]
    bmapheight = raw[3]

    # blockmap[cell] = raw offset list starting at that offset
    # We keep a flat array; collision code will index via offset lists.
    # For Python we build a list-of-lists: each cell → list of linedef indices.
    total_cells = bmapwidth * bmapheight
    blockmap = []
    for i in range(total_cells):
        ofs = raw[4 + i]       # offset from start of blockmaplump
        cell_lines = []
        j = ofs + 1            # skip the 0 header
        while raw[j] != -1:
            cell_lines.append(raw[j])
            j += 1
        blockmap.append(cell_lines)

    blocklinks = [None] * total_cells


# ------------------------------------------------------------------
# P_LoadReject
# ------------------------------------------------------------------
def P_LoadReject(lump_data: bytes):
    global rejectmatrix
    min_len = (len(sectors) * len(sectors) + 7) // 8
    if len(lump_data) >= min_len:
        rejectmatrix = lump_data
    else:
        # pad with zeros  (safe default — nothing rejected)
        rejectmatrix = lump_data + b'\x00' * (min_len - len(lump_data))


def P_RejectLookup(s1: int, s2: int) -> bool:
    """Return True if LOS between sectors s1 and s2 is rejected."""
    if not rejectmatrix:
        return False
    pnum = s1 * len(sectors) + s2
    return bool(rejectmatrix[pnum >> 3] & (1 << (pnum & 7)))


# ------------------------------------------------------------------
# P_LoadThings
# ------------------------------------------------------------------
_DOOM2_ONLY = {68, 64, 88, 89, 69, 67, 71, 65, 66, 84}

def P_LoadThings(lump_data: bytes):
    import doomstat

    raw = load_lump_array(lump_data, MapThing)

    for mt in raw:
        spawn = True

        if doomstat.gamemode != GameMode.COMMERCIAL:
            if mt.type in _DOOM2_ONLY:
                spawn = False

        if not spawn:
            continue

        P_SpawnMapThing(mt)

    # validate player starts
    if not doomstat.deathmatch:
        for i in range(MAXPLAYERS):
            if doomstat.playeringame[i] and not doomstat.playerstartsingame[i]:
                raise RuntimeError(
                    f'P_LoadThings: Player {i+1} start missing')
            doomstat.playerstartsingame[i] = False


# ------------------------------------------------------------------
# P_GroupLines  — link subsectors→sectors, sectors→lines, compute bbox
# ------------------------------------------------------------------
def P_GroupLines():
    # 1. link each subsector to its sector (via first seg's sidedef)
    for ss in subsectors:
        seg = segs[ss.firstline]
        ss.sector = seg.sidedef.sector

    # 2. count lines per sector
    for s in sectors:
        s.linecount = 0
        s.lines     = []

    for ld in lines:
        if ld.frontsector:
            ld.frontsector.linecount += 1
        if ld.backsector and ld.backsector is not ld.frontsector:
            ld.backsector.linecount += 1

    # 3. assign lines to sectors
    for ld in lines:
        if ld.frontsector:
            ld.frontsector.lines.append(ld)
        if ld.backsector and ld.backsector is not ld.frontsector:
            ld.backsector.lines.append(ld)

    # 4. bounding boxes + blockbox + soundorg
    for sector in sectors:
        bbox = [0, 0, 0, 0]
        M_ClearBox(bbox)

        for ld in sector.lines:
            M_AddToBox(bbox, ld.v1.x, ld.v1.y)
            M_AddToBox(bbox, ld.v2.x, ld.v2.y)

        # sound origin at centre of bbox
        sector.soundorg.x = (bbox[BOXRIGHT]  + bbox[BOXLEFT])   // 2
        sector.soundorg.y = (bbox[BOXTOP]    + bbox[BOXBOTTOM]) // 2

        # blockmap-aligned bounding box
        blk = (bbox[BOXTOP] - bmaporgy + MAXRADIUS) >> MAPBLOCKSHIFT
        sector.blockbox[BOXTOP]    = min(blk, bmapheight - 1)

        blk = (bbox[BOXBOTTOM] - bmaporgy - MAXRADIUS) >> MAPBLOCKSHIFT
        sector.blockbox[BOXBOTTOM] = max(blk, 0)

        blk = (bbox[BOXRIGHT] - bmaporgx + MAXRADIUS) >> MAPBLOCKSHIFT
        sector.blockbox[BOXRIGHT]  = min(blk, bmapwidth - 1)

        blk = (bbox[BOXLEFT] - bmaporgx - MAXRADIUS) >> MAPBLOCKSHIFT
        sector.blockbox[BOXLEFT]   = max(blk, 0)


# ------------------------------------------------------------------
# P_SetupLevel  — main entry point
# ------------------------------------------------------------------
def P_SetupLevel(episode: int, map_: int, playermask: int, skill: int):
    import doomstat
    from d_think import thinkercap as _thinkercap

    # reset counters
    doomstat.totalkills = doomstat.totalitems = doomstat.totalsecret = 0
    if doomstat.wminfo:
        doomstat.wminfo.maxfrags = 0
        doomstat.wminfo.partime  = 180

    for i in range(MAXPLAYERS):
        if doomstat.players[i]:
            doomstat.players[i].killcount   = 0
            doomstat.players[i].secretcount = 0
            doomstat.players[i].itemcount   = 0

    if doomstat.players[doomstat.consoleplayer]:
        doomstat.players[doomstat.consoleplayer].viewz = 1

    S_Start()

    # reset thinker list
    _thinkercap.__init__()

    # build map name
    from wad import get_wad
    wad = get_wad()

    if doomstat.gamemode == GameMode.COMMERCIAL:
        map_name = f'MAP{map_:02d}'
    else:
        map_name = f'E{episode}M{map_}'

    map_lumps = wad.get_map_lumps(map_name)

    doomstat.leveltime = 0

    # Load order matters — mirrors p_setup.c exactly
    P_LoadBlockMap  (map_lumps[ML_BLOCKMAP].data)
    P_LoadVertexes  (map_lumps[ML_VERTEXES].data)
    P_LoadSectors   (map_lumps[ML_SECTORS].data)
    P_LoadSideDefs  (map_lumps[ML_SIDEDEFS].data)
    P_LoadLineDefs  (map_lumps[ML_LINEDEFS].data)
    P_LoadSubsectors(map_lumps[ML_SSECTORS].data)
    P_LoadNodes     (map_lumps[ML_NODES].data)
    P_LoadSegs      (map_lumps[ML_SEGS].data)
    P_GroupLines    ()
    P_LoadReject    (map_lumps[ML_REJECT].data)

    doomstat.bodyqueslot   = 0
    doomstat.deathmatch_p  = 0
    doomstat.deathmatchstarts = []

    P_LoadThings(map_lumps[ML_THINGS].data)

    if doomstat.deathmatch:
        for i in range(MAXPLAYERS):
            if doomstat.playeringame[i]:
                if doomstat.players[i]:
                    doomstat.players[i].mo = None
                G_DeathMatchSpawnPlayer(i)

    # reset item respawn queue (in p_mobj)
    import p_mobj
    p_mobj.iquehead = p_mobj.iquetail = 0

    P_SpawnSpecials()

    if doomstat.precache:
        R_PrecacheLevel()


# ------------------------------------------------------------------
# P_Init  — called once at startup
# ------------------------------------------------------------------
def P_Init():
    import r_things
    global R_InitSprites
    R_InitSprites = r_things.R_InitSprites

    import p_switch
    import p_spec
    
    global P_InitSwitchList, P_InitPicAnims
    P_InitSwitchList = p_switch.P_InitSwitchList
    P_InitPicAnims = p_spec.P_InitPicAnims

    import info as info_mod
    P_InitSwitchList()
    P_InitPicAnims()
    R_InitSprites(info_mod.sprnames)
