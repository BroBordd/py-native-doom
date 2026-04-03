# deh_main.py
#
# DESCRIPTION:
#       DeHackEd main interface.
#       Handles string replacements and patch orchestration.

# -----------------------------------------------------------------------------
# GLOBALS
# -----------------------------------------------------------------------------

# Dictionary to hold DeHackEd string replacements.
# Keys are the original DOOM strings, values are the custom BEX/DeHackEd strings.
deh_strings = {}

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

def DEH_Init():
    """
    Initialize the DeHackEd subsystem.
    Called during d_main engine startup.
    """
    deh_strings.clear()


def DEH_String(s: str) -> str:
    """
    Returns the DeHackEd replacement for the given string.
    If no replacement is found, returns the original string.
    
    This is the exact equivalent to the C function:
    const char *DEH_String(const char *s);
    """
    # If a string has been modified by a loaded .deh or .bex patch, 
    # return the modified version.
    if s in deh_strings:
        return deh_strings[s]
    
    # Otherwise, return the original vanilla string.
    return s


def DEH_AddStringReplacement(original: str, replacement: str):
    """
    Adds a string replacement to the DeHackEd dictionary.
    Used by deh_str.py / deh_bexstr.py when parsing patches.
    """
    deh_strings[original] = replacement


def DEH_LoadPatch(filename: str):
    """
    Loads a .deh or .bex DeHackEd patch.
    (Full parsing logic hooks into deh_thing, deh_weapon, etc.)
    """
    pass
