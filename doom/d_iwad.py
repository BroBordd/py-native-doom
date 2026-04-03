import sys
import os

# Emulate GameMission_t from Chocolate Doom
class GameMission_t:
    doom = 0
    doom2 = 1
    pack_tnt = 2
    pack_plut = 3
    none = 4

# Emulate GameMode_t from Chocolate Doom
class GameMode_t:
    shareware = 0
    registered = 1
    commercial = 2
    retail = 3
    indetermined = 4

def D_FindIWAD():
    """
    Finds the IWAD file path, replicating Chocolate Doom's D_FindIWAD logic.
    """
    iwadparm = None
    
    # Check command line args for -iwad
    if "-iwad" in sys.argv:
        try:
            idx = sys.argv.index("-iwad")
            iwadparm = sys.argv[idx + 1]
        except IndexError:
            pass

    # If an IWAD was specified and it exists, return it
    if iwadparm and os.path.exists(iwadparm):
        return iwadparm

    # Standard fallbacks if no argument was provided
    fallbacks = [
        "DOOM2.WAD", "PLUTONIA.WAD", "TNT.WAD", 
        "DOOM.WAD", "DOOM1.WAD",
        "doom2.wad", "plutonia.wad", "tnt.wad", 
        "doom.wad", "doom1.wad"
    ]
    
    for f in fallbacks:
        if os.path.exists(f):
            return f

    print("Error: Could not find an IWAD file. Please use -iwad <file>")
    sys.exit(1)

def IdentifyIWAD(wad_name):
    """
    Basic identification of the IWAD mission/mode.
    """
    name = wad_name.upper()
    
    if "DOOM2" in name or "PLUTONIA" in name or "TNT" in name:
        return GameMode_t.commercial, GameMission_t.doom2
    elif "DOOM1" in name:
        return GameMode_t.shareware, GameMission_t.doom
    else:
        # DOOM.WAD defaults to retail
        return GameMode_t.retail, GameMission_t.doom

# --- Added by Claude to fix missing IWAD masks ---
IWAD_MASK_DOOM      = 1 << 0
IWAD_MASK_DOOM2     = 1 << 1
IWAD_MASK_PLUT      = 1 << 2
IWAD_MASK_TNT       = 1 << 3
IWAD_MASK_CHEX      = 1 << 4
IWAD_MASK_HACX      = 1 << 5
IWAD_MASK_FREEDM    = 1 << 6
IWAD_MASK_FREEDOOM1 = 1 << 7
IWAD_MASK_FREEDOOM2 = 1 << 8
# -----------------------------------------------

# --- Added by Claude to fix D_FindIWAD signature and logic ---
import sys
import os
import doomstat

def D_FindIWAD(mask, mission_ref):
    """
    Finds the main IWAD file and sets the game mode.
    """
    iwad = "DOOM1.WAD" # Default fallback
    
    # Check if the user passed -iwad in the terminal
    if "-iwad" in sys.argv:
        try:
            idx = sys.argv.index("-iwad")
            iwad = sys.argv[idx + 1]
        except IndexError:
            pass
            
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(iwad):
        iwad = os.path.join(script_dir, iwad)
    if not os.path.exists(iwad):
        print(f"Error: IWAD file '{iwad}' not found!")
        sys.exit(-1)
        
    # In C, this sets variables like gamemode and gamemission via pointer.
    # We'll set reasonable defaults for Doom 1 Shareware directly on doomstat.
    # 1 = shareware, 0 = doom
    doomstat.gamemode = 1 
    doomstat.gamemission = 0
    
    print(f"IWAD found: {iwad}")
    return iwad
# -----------------------------------------------

def D_SaveGameIWADName(mission, variant):
    return "doom"
