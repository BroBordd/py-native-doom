# deh_str.py

# A dictionary to store any DeHackEd string replacements
# (Empty for now since we aren't loading .deh files)
replaced_strings = {}

def DEH_String(s):
    """
    Checks if a string has been replaced by DeHackEd.
    If it has, returns the replacement. Otherwise, returns the original.
    """
    return replaced_strings.get(s, s)

def DEH_AddStringReplacement(original, replacement):
    """
    Registers a new string replacement (used if parsing a .deh file).
    """
    replaced_strings[original] = replacement

def DEH_ParseCommandLine():
    pass
