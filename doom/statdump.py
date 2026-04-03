#
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
# --
#
# Functions for presenting the information captured from the statistics
# buffer to a file.
#

import sys
import copy

# Attempt to import necessary constants.
from doomdef import TICRATE, MAXPLAYERS

# -----------------------------------------------------------------------------
# Resilient argv handling
# -----------------------------------------------------------------------------
try:
    from m_argv import M_ParmExists, M_CheckParmWithArgs, myargv
except ImportError:
    # Fallback if m_argv is incomplete or missing specific functions
    try:
        from m_argv import M_CheckParm, myargv
        def M_ParmExists(param):
            return M_CheckParm(param) > 0
            
        def M_CheckParmWithArgs(param, num_args):
            idx = M_CheckParm(param)
            if idx > 0 and idx + num_args < len(myargv):
                return idx
            return 0
    except ImportError:
        myargv = sys.argv
        
        def M_ParmExists(param):
            return param in myargv
            
        def M_CheckParmWithArgs(param, num_args):
            if param in myargv:
                idx = myargv.index(param)
                if idx + num_args < len(myargv):
                    return idx
            return 0

# -----------------------------------------------------------------------------
# Enums & Constants
# -----------------------------------------------------------------------------

# GameMission_t equivalent
MISSION_NONE  = 0
MISSION_DOOM  = 1
MISSION_DOOM2 = 2

# Par times for E1M1-E1M9.
doom1_par_times = [
    30, 75, 120, 90, 165, 180, 180, 30, 165
]

# Par times for MAP01-MAP09.
doom2_par_times = [
    30, 90, 120, 120, 90, 150, 120, 120, 270
]

# Player colors.
player_colors = [
    "Green", "Indigo", "Brown", "Red"
]

MAX_CAPTURES = 32

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

captured_stats = []
num_captured_stats = 0
discovered_gamemission = MISSION_NONE

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def is_player_in(player):
    """
    Python 'in' is a keyword, so the C struct member 'in' is typically 
    renamed to 'in_', 'ingame', or similar in the Python structure. 
    This provides safe access.
    """
    return getattr(player, "in_", getattr(player, "ingame", getattr(player, "in", False)))

def DiscoverGamemode(stats_list):
    """
    Try to work out whether this is a Doom 1 or Doom 2 game, by looking
    at the episode and map, and the par times.
    """
    global discovered_gamemission

    if discovered_gamemission != MISSION_NONE:
        return

    for stats in stats_list:
        level = stats.last

        # If episode 2, 3 or 4, this is Doom 1.
        if stats.epsd > 0:
            discovered_gamemission = MISSION_DOOM
            return

        # This is episode 1. If this is level 10 or higher, it must be Doom 2.
        # (Level is 0-indexed in wbstartstruct_t, meaning stats.last >= 9)
        if level >= 9:
            discovered_gamemission = MISSION_DOOM2
            return

        # Try to work out if this is Doom 1 or Doom 2 by looking at the par time.
        partime = stats.partime

        if partime == doom1_par_times[level] * TICRATE and partime != doom2_par_times[level] * TICRATE:
            discovered_gamemission = MISSION_DOOM
            return

        if partime != doom1_par_times[level] * TICRATE and partime == doom2_par_times[level] * TICRATE:
            discovered_gamemission = MISSION_DOOM2
            return

def GetNumPlayers(stats):
    """ Returns the number of players active in the given stats buffer. """
    num_players = 0
    for i in range(MAXPLAYERS):
        if is_player_in(stats.plyr[i]):
            num_players += 1
    return num_players

def PrintBanner(stream):
    stream.write("===========================================\n")

def PrintPercentage(stream, amount, total):
    if total == 0:
        stream.write("0")
    else:
        # statdump.exe is a 16-bit program, so very occasionally an
        # integer overflow can occur when doing this calculation with
        # a large value. Therefore, cast to short to give the same output.
        val = amount * 100
        # Cast to 16-bit signed integer (short) natively
        short_val = (val & 0xFFFF)
        if short_val >= 0x8000:
            short_val -= 0x10000
            
        # C-style integer division (truncate towards zero)
        perc = int(short_val / total) 
        stream.write(f"{amount} / {total} ({perc}%)")

def PrintPlayerStats(stream, stats, player_num):
    """ Display statistics for a single player. """
    player = stats.plyr[player_num]

    stream.write(f"Player {player_num + 1} ({player_colors[player_num]}):\n")

    # Kills percentage
    stream.write("\tKills: ")
    PrintPercentage(stream, player.skills, stats.maxkills)
    stream.write("\n")

    # Items percentage
    stream.write("\tItems: ")
    PrintPercentage(stream, player.sitems, stats.maxitems)
    stream.write("\n")

    # Secrets percentage
    stream.write("\tSecrets: ")
    PrintPercentage(stream, player.ssecret, stats.maxsecret)
    stream.write("\n")

def PrintFragsTable(stream, stats):
    """ Frags table for multiplayer games. """
    stream.write("Frags:\n")

    # Print header
    stream.write("\t\t")
    for x in range(MAXPLAYERS):
        if not is_player_in(stats.plyr[x]):
            continue
        stream.write(f"{player_colors[x]}\t")
    stream.write("\n")

    stream.write("\t\t-------------------------------- VICTIMS\n")

    # Print table
    for y in range(MAXPLAYERS):
        if not is_player_in(stats.plyr[y]):
            continue

        stream.write(f"\t{player_colors[y]}\t|")

        for x in range(MAXPLAYERS):
            if not is_player_in(stats.plyr[x]):
                continue
            
            stream.write(f"{stats.plyr[y].frags[x]}\t")

        stream.write("\n")

    stream.write("\t\t|\n")
    stream.write("\t     KILLERS\n")

def PrintLevelName(stream, episode, level):
    """ Displays the level name: MAPxy or ExMy, depending on game mode. """
    PrintBanner(stream)

    if discovered_gamemission == MISSION_DOOM:
        stream.write(f"E{episode + 1}M{level + 1}\n")
    elif discovered_gamemission == MISSION_DOOM2:
        stream.write(f"MAP{level + 1:02d}\n")
    else:
        stream.write(f"E{episode + 1}M{level + 1} / MAP{level + 1:02d}\n")

    PrintBanner(stream)

def PrintStats(stream, stats):
    """ Print details of a statistics buffer to the given file. """
    PrintLevelName(stream, stats.epsd, stats.last)
    stream.write("\n")

    # Emulating C integer division truncation for time calculation
    leveltime = int(stats.plyr[0].stime / TICRATE)
    partime = int(stats.partime / TICRATE)
    
    stream.write(f"Time: {leveltime // 60}:{leveltime % 60:02d}")
    stream.write(f" (par: {partime // 60}:{partime % 60:02d})\n")
    stream.write("\n")

    for i in range(MAXPLAYERS):
        if is_player_in(stats.plyr[i]):
            PrintPlayerStats(stream, stats, i)

    if GetNumPlayers(stats) >= 2:
        PrintFragsTable(stream, stats)

    stream.write("\n")

# -----------------------------------------------------------------------------
# Main Exposed API (statdump.h)
# -----------------------------------------------------------------------------

def StatCopy(stats):
    """
    Copies current level statistics to the captured array if `-statdump`
    is requested by the user.
    """
    global num_captured_stats
    if M_ParmExists("-statdump") and num_captured_stats < MAX_CAPTURES:
        captured_stats.append(copy.deepcopy(stats))
        num_captured_stats += 1

def StatDump():
    """
    Dump statistics information to the specified file on the levels
    that were played. The output from this option matches the output
    from statdump.exe.
    """
    i = M_CheckParmWithArgs("-statdump", 1)

    if i > 0:
        print(f"Statistics captured for {num_captured_stats} level(s)")

        # We actually know what the real gamemission is, but this has
        # to match the output from statdump.exe.
        DiscoverGamemode(captured_stats)

        filename = myargv[i + 1]

        # Allow "-" as output file, for stdout.
        if filename != "-":
            try:
                dumpfile = open(filename, "w")
                for stats in captured_stats:
                    PrintStats(dumpfile, stats)
                dumpfile.close()
            except Exception as e:
                print(f"Error writing stat dump: {e}")
        else:
            for stats in captured_stats:
                PrintStats(sys.stdout, stats)
                sys.stdout.flush()
