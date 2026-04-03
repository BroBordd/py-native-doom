# d_net.py
#
# DESCRIPTION:
#   DOOM Network game communication and protocol,
#   all OS independent parts.

import sys

import doomstat
from doomdef import MAXPLAYERS, ANG90, ANG270
import m_argv
import g_game
import p_tick

# --- Data Structures ---

class NetGameSettings:
    def __init__(self):
        self.deathmatch = 0
        self.episode = 1
        self.map = 1
        self.skill = 2
        self.loadgame = False
        self.gameversion = 0
        self.nomonsters = False
        self.fast_monsters = False
        self.respawn_monsters = False
        self.timelimit = 0
        self.lowres_turn = False
        self.consoleplayer = 0
        self.num_players = 1

class NetConnectData:
    def __init__(self):
        self.max_players = MAXPLAYERS
        self.drone = False
        self.gamemode = 0
        self.gamemission = 0
        self.lowres_turn = False
        self.wad_sha1sum = ""
        self.deh_sha1sum = ""
        self.is_freedoom = False

# --- Global Variables ---

netcmds = None

# --- Functions ---

def PlayerQuitGame(player):
    # Determine player number by finding the object reference in the players list
    player_num = 0
    for i in range(MAXPLAYERS):
        if doomstat.players[i] == player:
            player_num = i
            break

    exitmsg = f"Player {player_num + 1} left the game"

    doomstat.playeringame[player_num] = False
    doomstat.players[doomstat.consoleplayer].message = exitmsg

    if doomstat.demorecording:
        g_game.G_CheckDemoStatus()

def RunTic(cmds, ingame):
    global netcmds
    import d_main # Localized to prevent circular import

    # Check for player quits.
    for i in range(MAXPLAYERS):
        if not doomstat.demoplayback and doomstat.playeringame[i] and not ingame[i]:
            PlayerQuitGame(doomstat.players[i])

    netcmds = cmds

    # check that there are players in the game. if not, we cannot run a tic.
    if doomstat.advancedemo:
        d_main.D_DoAdvanceDemo()

    g_game.G_Ticker()

# In Chocolate Doom, this interface is passed to the d_loop network layer.
# We map it to the python functions.
doom_loop_interface = {
    'ProcessEvents': None,  # Mapped later in engine or stubbed
    'BuildTiccmd': g_game.G_BuildTiccmd,
    'RunTic': RunTic,
    'Ticker': None          # Usually m_menu.M_Ticker
}

def LoadGameSettings(settings):
    doomstat.deathmatch = settings.deathmatch
    doomstat.startepisode = settings.episode
    doomstat.startmap = settings.map
    doomstat.startskill = settings.skill
    doomstat.startloadgame = settings.loadgame
    doomstat.lowres_turn = settings.lowres_turn
    doomstat.nomonsters = settings.nomonsters
    doomstat.fastparm = settings.fast_monsters
    doomstat.respawnparm = settings.respawn_monsters
    doomstat.timelimit = settings.timelimit
    doomstat.consoleplayer = settings.consoleplayer

    if doomstat.lowres_turn:
        print("NOTE: Turning resolution is reduced; this is probably "
              "because there is a client recording a Vanilla demo.")

    for i in range(MAXPLAYERS):
        doomstat.playeringame[i] = (i < settings.num_players)

def SaveGameSettings(settings):
    settings.deathmatch = doomstat.deathmatch
    settings.episode = doomstat.startepisode
    settings.map = doomstat.startmap
    settings.skill = doomstat.startskill
    settings.loadgame = doomstat.startloadgame
    settings.gameversion = doomstat.gameversion
    settings.nomonsters = doomstat.nomonsters
    settings.fast_monsters = doomstat.fastparm
    settings.respawn_monsters = doomstat.respawnparm
    settings.timelimit = doomstat.timelimit

    settings.lowres_turn = (m_argv.M_ParmExists("-record") and not m_argv.M_ParmExists("-longtics")) or m_argv.M_ParmExists("-shorttics")

def InitConnectData(connect_data):
    connect_data.max_players = MAXPLAYERS
    connect_data.drone = False

    # Run as the left screen in three screen mode.
    if m_argv.M_CheckParm("-left") > 0:
        doomstat.viewangleoffset = ANG90
        connect_data.drone = True

    # Run as the right screen in three screen mode.
    if m_argv.M_CheckParm("-right") > 0:
        doomstat.viewangleoffset = ANG270
        connect_data.drone = True

    connect_data.gamemode = doomstat.gamemode
    connect_data.gamemission = doomstat.gamemission

    # Play with low turning resolution to emulate demo recording.
    shorttics = m_argv.M_ParmExists("-shorttics")
    connect_data.lowres_turn = (m_argv.M_ParmExists("-record") and not m_argv.M_ParmExists("-longtics")) or shorttics

    # Note: Skipping checksum and Freedoom checks for a minimal Python boot
    connect_data.wad_sha1sum = ""
    connect_data.deh_sha1sum = ""
    connect_data.is_freedoom = False


# --- Mocks for missing Client/Server backend (d_client.c / d_loop.c) ---

def D_InitNetGame(connect_data):
    """
    Stubs the hardware network initialization. 
    Returns True if a network game is successfully started, False for single player.
    """
    return False

def D_StartNetGame(settings, something=None):
    """
    Stubs the network game start. 
    Forces a single-player environment setup.
    """
    settings.num_players = 1
    settings.consoleplayer = 0

def D_RegisterLoopCallbacks(interface):
    """
    Stubs the d_loop.c callback registration.
    """
    pass

# --- Main API ---

def D_ConnectNetGame():
    connect_data = NetConnectData()

    InitConnectData(connect_data)
    doomstat.netgame = D_InitNetGame(connect_data)

    # Start the game playing as though in a netgame with a single player.
    if m_argv.M_CheckParm("-solo-net") > 0:
        doomstat.netgame = True

def D_CheckNetGame():
    if doomstat.netgame:
        doomstat.autostart = True

    D_RegisterLoopCallbacks(doom_loop_interface)

    settings = NetGameSettings()
    SaveGameSettings(settings)
    D_StartNetGame(settings, None)
    LoadGameSettings(settings)

    print(f"startskill {doomstat.startskill}  deathmatch: {doomstat.deathmatch}  startmap: {doomstat.startmap}  startepisode: {doomstat.startepisode}")
    print(f"player {doomstat.consoleplayer + 1} of {settings.num_players} ({settings.num_players} nodes)")

    if doomstat.timelimit > 0 and doomstat.deathmatch:
        if doomstat.timelimit == 20 and m_argv.M_CheckParm("-avg"):
            print("Austin Virtual Gaming: Levels will end after 20 minutes")
        else:
            s = "s" if doomstat.timelimit > 1 else ""
            print(f"Levels will end after {doomstat.timelimit} minute{s}.")

def I_BindNetVariables():
    pass

# --- Auto-generated Network Stubs ---

def NET_Init():
    pass

def NetUpdate():
    pass

oldentertics = 0

def TryRunTics():
    global oldentertics
    import d_main
    import doomstat
    import g_game
    import m_menu
    import i_timer

    # Safely fetch timing scalars
    ticdup = getattr(doomstat, 'ticdup', 1)
    backuptics = getattr(doomstat, 'BACKUPTICS', 128)

    # Synchronize game tics with real time
    entertic = i_timer.I_GetTime() // ticdup
    realtics = entertic - oldentertics
    oldentertics = entertic

    counts = realtics
    if counts < 1:
        counts = 1  # Force at least 1 tick

    for _ in range(counts):
        # 1. Process all pending inputs from Bombsquad
        d_main.D_ProcessEvents()

        # 2. Compile inputs into the player's TicCmd for this frame
        maketic = doomstat.maketic
        consoleplayer = doomstat.consoleplayer

        cmd = doomstat.netcmds[consoleplayer][maketic % backuptics]
        
        # FIX: Pass maketic to G_BuildTiccmd alongside cmd
        g_game.G_BuildTiccmd(cmd, maketic)
        
        doomstat.maketic += 1

        # 3. Apply the commands and advance the engine state
        while doomstat.gametic < doomstat.maketic:
            gametic = doomstat.gametic
            
            for i in range(doomstat.MAXPLAYERS):
                if doomstat.playeringame[i]:
                    doomstat.players[i].cmd = doomstat.netcmds[i][gametic % backuptics]

            # Advance Demo / Menus / Game
            if getattr(d_main, 'advancedemo', False) and hasattr(d_main, 'D_DoAdvanceDemo'):
                d_main.D_DoAdvanceDemo()

            if hasattr(m_menu, 'M_Ticker'):
                m_menu.M_Ticker()
                
            g_game.G_Ticker()
            
            doomstat.gametic += 1

def D_QuitNetGame():
    pass

# Event queue for input handling
_event_queue = []

def D_PostEvent(ev):
    _event_queue.append(ev)

def D_PopEvent():
    if _event_queue:
        return _event_queue.pop(0)
    return None
