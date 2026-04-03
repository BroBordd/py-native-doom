# doomstat.py
# All global game-state variables
# Ported from doomstat.h / doomstat.c

from doomdef import (
    GameMode, GameMission, GameVersion, GameVariant,
    GameState, Skill, MAXPLAYERS,
)

# --- SOUND & VOLUMES (Fixes S_Start / S_Init crashes) ---
snd_SfxDevice = 1
snd_MusicDevice = 1
sfxVolume = 8
musicVolume = 8
mus_runnin = 1  # Base index for Doom 2 music

# --- ENGINE CONSTANTS & ALIASES (Matches d_main.py grep) ---
NF_SUBSECTOR = 0x8000
exe_ultimate = 119
exe_final    = 119
# Some modules look for lower-case GameMode names
shareware    = 0 
registered   = 1
commercial   = 2
retail       = 3

# --- GEOMETRY & MAP DATA (Required by p_setup.py and p_sight.py) ---
sectors = []
numsectors = 0
lines = []
sides = []
nodes = []
numnodes = 0
subsectors = []
segs = []
rejectmatrix = None
validcount = 0
skyflatnum = 0

# --- BLOCKMAP DATA (Required by p_maputl.py) ---
bmaporgx = 0
bmaporgy = 0
bmapwidth = 0
bmapheight = 0
blocklinks = []
blockmap = []
blockmaplump = []

# --- MISC STATE ---
paused = False
menuactive = False
automapactive = False
viewactive = True
nodrawers = False
screenvisible = True
setsizeneeded = False
testcontrols = False
testcontrols_mousespeed = 10
mouseSensitivity = 10
showMessages = True
screenblocks = 10
detailLevel = 0
advancedemo = False
players = [None] * 4  # Assuming MAXPLAYERS is 4
playeringame = [False] * 4
playerstartsingame = [False] * 4
playerstarts = [None] * 4
deathmatchstarts = []
deathmatch_p = 0
leveltime = 0
totalkills = 0
totalitems = 0
totalsecret = 0
bodyqueslot = 0
wminfo = None
netcmds = None
chat_macros = [""] * 10
key_multi_msgplayer = [0] * 4

# Game behavior flags
exe_chex     = False
exe_heretic  = False
exe_strife   = False
exe_doom     = True

# Common missing state variables
viewactive   = False
menuactive   = False
paused       = False
nodraw       = False
noblit       = False

# These are usually populated by P_SetupLevel in p_setup.py
sectors = []
numsectors = 0
lines = []
sides = []
nodes = []
numnodes = 0
subsectors = []
segs = []
rejectmatrix = None
validcount = 0

# --- MISSING BLOCKMAP GLOBALS ---
bmaporgx = 0
bmaporgy = 0
bmapwidth = 0
bmapheight = 0
blocklinks = []
blockmap = []
blockmaplump = []

# --- UI & CONFIG BINDINGS ---
showMessages = True
screenblocks = 10
detailLevel = 0
advancedemo = False

# --- CONSTANT ALIASES (to match d_main.py / p_telept.py grep) ---
NF_SUBSECTOR = 0x8000
exe_ultimate = 119  # Alias for GameVersion.EXE_FINAL2
exe_final = 119

# --- MISSING STATE FLAGS ---
wipegamestate = GameState.DEMOSCREEN # Your grep shows d_main using this

# -----------------------------------------------------------------------------
# gameaction_t
# -----------------------------------------------------------------------------
ga_nothing      = 0
ga_loadlevel    = 1
ga_newgame      = 2
ga_loadgame     = 3
ga_savegame     = 4
ga_playdemo     = 5
ga_completed    = 6
ga_victory      = 7
ga_worlddone    = 8
ga_screenshot   = 9

# -----------------------------------------------
# Command-line flags
# -----------------------------------------------
nomonsters  = False   # -nomonsters
respawnparm = False   # -respawn
fastparm    = False   # -fast
devparm     = False   # -devparm

# -----------------------------------------------
# Game mode / mission
# -----------------------------------------------
gamemode     = GameMode.INDETERMINED
gamemission  = GameMission.DOOM
gameversion  = GameVersion.EXE_FINAL2
gamevariant  = GameVariant.VANILLA
modifiedgame = False   # PWAD loaded

def logical_gamemission() -> int:
    """Collapse pack_chex → doom, pack_hacx → doom2."""
    if gamemission == GameMission.PACK_CHEX:
        return GameMission.DOOM
    if gamemission == GameMission.PACK_HACX:
        return GameMission.DOOM2
    return gamemission

# -----------------------------------------------
# Skill / episode / map selection
# -----------------------------------------------
startskill    = Skill.MEDIUM
startepisode  = 1
startmap      = 1
startloadgame = -1    # -1 = not set
autostart     = False

gameskill   = Skill.MEDIUM
gameepisode = 1
gamemap     = 1

timelimit        = 0      # 0 = no limit
respawnmonsters  = False  # nightmare mode

# -----------------------------------------------
# Netgame
# -----------------------------------------------
netgame    = False
deathmatch = 0    # 0=coop, 1=dm, 2=altdeath

# -----------------------------------------------
# Sound
# -----------------------------------------------
sfxVolume   = 8
musicVolume = 8
snd_MusicDevice        = 0
snd_SfxDevice          = 0
snd_DesiredMusicDevice = 0
snd_DesiredSfxDevice   = 0

# -----------------------------------------------
# Status flags for refresh
# -----------------------------------------------
statusbaractive = False
automapactive   = False
menuactive      = False
paused          = False
viewactive      = True
nodrawers       = False
testcontrols         = False
testcontrols_mousespeed = 0

viewangleoffset = 0
consoleplayer   = 0
displayplayer   = 0

# -----------------------------------------------
# Scores / statistics
# -----------------------------------------------
totalkills   = 0
totalitems   = 0
totalsecret  = 0
levelstarttic = 0
leveltime     = 0

# -----------------------------------------------
# Demo
# -----------------------------------------------
usergame      = False
demoplayback  = False
demorecording = False
lowres_turn   = False
singledemo    = False

# -----------------------------------------------
# Game state
# -----------------------------------------------
gamestate     = GameState.DEMOSCREEN
wipegamestate = GameState.DEMOSCREEN

# -----------------------------------------------
# Players
# -----------------------------------------------
# Imported lazily to avoid circular imports; player_t is defined in d_player.py
# and depends on p_mobj.py which depends on doomstat.py in the full build.
# We store players as a plain list; p_main.py will populate it.
players         = [None] * MAXPLAYERS
playeringame    = [False] * MAXPLAYERS

# Deathmatch spawn points
MAX_DM_STARTS   = 10
deathmatchstarts = []   # list of MapThing
deathmatch_p     = 0    # index into deathmatchstarts (replaces pointer)

# Player spawn spots
playerstarts       = [None] * MAXPLAYERS   # MapThing or None
playerstartsingame = [False] * MAXPLAYERS

# Intermission info  (wbstartstruct_t); set by G_WorldDone
wminfo = None

# -----------------------------------------------
# Engine internals
# -----------------------------------------------
savegamedir = '.'
precache    = True

mouseSensitivity = 5
bodyqueslot      = 0
skyflatnum       = 0    # set by P_LoadSectors

rndindex = 0            # also tracked in m_random; kept here for save/load

# --- Added by Claude to fix missing chat_macros ---
chat_macros = [""] * 10
# -----------------------------------------------

# --- Added by Claude to fix GameMission / GameMode enums ---
# GameMission_t enum equivalents
doom = 0
doom2 = 1
pack_tnt = 2
pack_plut = 3
none = 4

# GameMode_t enum equivalents
shareware = 0
registered = 1
commercial = 2
retail = 3
indetermined = 4
# -----------------------------------------------

# --- Added by Claude to fix Chex/Hacx enums ---
pack_chex = 5
pack_hacx = 6
# -----------------------------------------------

# Game variant definitions (Chocolate Doom GameVariant_t enum)
freedoom = 1
freedm = 2
bfa = 3

# Default to standard doom
gamevariant = doom
bfgedition = 3

# --- Auto-generated Game Versions ---
exe_doom_1_2 = 102
exe_doom_1_666 = 166
exe_doom_1_7 = 107
exe_doom_1_8 = 108
exe_doom_1_9 = 109
exe_final = 119
exe_hacx = 120
screenvisible = True
setsizeneeded = False

# --- Missing state variables ---
BACKUPTICS      = 128 # The size of the circular ticcmd buffer
ticdup          = 1   # Game ticks per input
inhelpscreens   = False
fullscreen      = False
noblit          = False
scaledviewwidth = 0
viewheight      = 0
viewwindowx     = 0
viewwindowy     = 0
gametic         = 0
maketic         = 0   
maketick        = 0   
drone           = False
forwardmove     = [0x19, 0x32]
sidemove        = [0x18, 0x28]
key_multi_msgplayer = [0] * 8
playeringame    = [False] * MAXPLAYERS

class MockTiccmd:
    def __init__(self):
        self.forwardmove = 0
        self.sidemove = 0
        self.angleturn = 0
        self.consistancy = 0
        self.chatchar = 0
        self.buttons = 0

# ticcmd buffer for netgame initialized safely to MockTiccmds
netcmds = [[MockTiccmd() for _ in range(BACKUPTICS)] for _ in range(MAXPLAYERS)]
