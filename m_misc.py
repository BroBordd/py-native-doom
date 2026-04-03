# m_misc.py
import sys
import os

def M_CheckParm(check):
    """
    Checks for the given parameter in the command line arguments.
    Returns its position index if found, otherwise returns 0.
    """
    try:
        return sys.argv.index(check)
    except ValueError:
        return 0

def M_FileExists(filename):
    """Checks if a file exists."""
    return os.path.exists(filename)

def M_ReadFile(name):
    """Reads a file and returns it as a bytearray."""
    try:
        with open(name, "rb") as f:
            return bytearray(f.read())
    except FileNotFoundError:
        return None

def M_WriteFile(name, data):
    """Writes bytes/bytearray data to a file."""
    try:
        with open(name, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False

def M_ExtractFileBase(path):
    """Extracts the base name of a file without the extension."""
    basename = os.path.basename(path)
    return os.path.splitext(basename)[0]

# --- Added by Claude to fix string duplication ---
def M_StringDuplicate(s):
    """Python equivalent of C's strdup."""
    return str(s) if s is not None else ""
# -----------------------------------------------

# --- Auto-generated Misc Stubs ---

def M_Init():
    pass
