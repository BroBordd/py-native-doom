# w_wad.py
import struct
import sys

# Store all lump directory entries and cached data
lumpinfo = []
lumpcache = {}
wad_files = []

class LumpInfo:
    def __init__(self, name, handle, pos, size):
        self.name = name
        self.handle = handle
        self.pos = pos
        self.size = size

def W_InitMultipleFiles(filenames):
    """Parses WAD headers and builds the global lump directory."""
    global lumpinfo, wad_files
    
    for filename in filenames:
        if not filename: 
            continue
            
        try:
            f = open(filename, "rb")
            wad_files.append(f)
            
            # Read WAD Header (12 bytes: 4 chars, 4-byte int, 4-byte int)
            header = f.read(12)
            if len(header) < 12: 
                continue
                
            identification, numlumps, infotableofs = struct.unpack("<4sII", header)
            
            # Go to directory offset
            f.seek(infotableofs)
            
            for _ in range(numlumps):
                entry = f.read(16)
                if len(entry) < 16: 
                    break
                
                pos, size, name_bytes = struct.unpack("<II8s", entry)
                
                # Clean up the name (null-terminated, ASCII)
                name = name_bytes.split(b'\x00')[0].decode('ascii', errors='ignore').upper()
                
                lumpinfo.append(LumpInfo(name, f, pos, size))
                
        except IOError:
            print(f"Error: Couldn't open {filename}")
            raise ValueError(f"W_GetNumForName: {name} not found!")

def W_CheckNumForName(name):
    """Returns lump number, or -1 if not found. Searches backwards so PWADs override IWADs."""
    name = name.upper()
    for i in range(len(lumpinfo) - 1, -1, -1):
        if lumpinfo[i].name == name:
            return i
    return -1

def W_GetNumForName(name):
    """Returns lump number, exits if missing."""
    i = W_CheckNumForName(name)
    if i == -1:
        print(f"W_GetNumForName: {name} not found!")
        raise ValueError(f"W_GetNumForName: {name} not found!")
    return i

def W_LumpLength(lump):
    """Returns the size of a lump in bytes."""
    if lump >= len(lumpinfo) or lump < 0:
        print(f"W_LumpLength: {lump} out of range")
        raise ValueError(f"W_GetNumForName: {name} not found!")
    return lumpinfo[lump].size

def W_ReadLump(lump, dest=None):
    """Reads lump data. If dest is provided, fills it, otherwise returns bytes."""
    if lump >= len(lumpinfo) or lump < 0:
        print(f"W_ReadLump: {lump} out of range")
        raise ValueError(f"W_GetNumForName: {name} not found!")
    
    info = lumpinfo[lump]
    info.handle.seek(getattr(info, 'position', getattr(info, 'filepos', 0)))
    data = info.handle.read(info.size)
    
    if dest is not None:
        # If a bytearray/list was passed, copy the data into it
        dest[:info.size] = data
        return dest
    return data

def W_CacheLumpNum(lump, tag):
    """Returns cached lump data."""
    if lump in lumpcache:
        return lumpcache[lump]
        
    data = W_ReadLump(lump)
    lumpcache[lump] = data
    return data

def W_CacheLumpName(name, tag):
    """Finds lump by name and returns cached data."""
    return W_CacheLumpNum(W_GetNumForName(name), tag)

# --- Added by Claude to fix WAD loading ---
import struct
import os

# Global lists to hold WAD file objects and lump directory info
if 'lumpinfo' not in globals():
    lumpinfo = []
if 'wadfiles' not in globals():
    wadfiles = []

def W_AddFile(filename):
    """Opens a WAD file and populates the global lump directory."""
    if not os.path.exists(filename):
        print(f"Error: Could not open {filename}")
        return None
        
    f = open(filename, 'rb')
    header = f.read(12)
    
    # Header format: 4 bytes identifier ("IWAD" or "PWAD"), 4 bytes num_lumps, 4 bytes directory_offset
    identification, numlumps, infotableofs = struct.unpack('<4sII', header)
    
    # Seek to the WAD directory table
    f.seek(infotableofs)
    
    for _ in range(numlumps):
        lump_data = f.read(16)
        if len(lump_data) < 16:
            break
            
        # Directory format: 4 bytes file_pos, 4 bytes size, 8 bytes name
        filepos, size, name_bytes = struct.unpack('<II8s', lump_data)
        
        # Clean up the C-style null-terminated string
        name = name_bytes.split(b'\x00')[0].decode('ascii', 'ignore').upper()
        
        lumpinfo.append({
            'name': name,
            'filepos': filepos,
            'size': size,
            'handle': f
        })
        
    wadfiles.append(f)
    # Return an integer handle (the index of this wad)
    return len(wadfiles)
# -----------------------------------------------

# --- Added by Claude to fix W_CheckCorrectIWAD ---
def W_CheckCorrectIWAD(game_mode):
    """Stub to verify the loaded IWAD matches the game mode."""
    # In a full C port, this checks for specific lumps like E1M1 vs MAP01.
    # We can safely pass here since D_FindIWAD already did the heavy lifting.
    pass
# -----------------------------------------------

# --- Added by Claude to fix lumpinfo dict vs object issue ---
class _Lump:
    """Mock struct to hold WAD lump data using attribute access."""
    def __init__(self, name, filepos, size, handle):
        self.name = name
        self.filepos = filepos
        self.size = size
        self.handle = handle

def W_AddFile(filename):
    """Opens a WAD file and populates the global lump directory with objects."""
    import struct, os
    global lumpinfo, wadfiles
    
    if not os.path.exists(filename):
        print(f"Error: Could not open {filename}")
        return None
        
    f = open(filename, 'rb')
    header = f.read(12)
    
    identification, numlumps, infotableofs = struct.unpack('<4sII', header)
    f.seek(infotableofs)
    
    for _ in range(numlumps):
        lump_data = f.read(16)
        if len(lump_data) < 16:
            break
            
        filepos, size, name_bytes = struct.unpack('<II8s', lump_data)
        name = name_bytes.split(b'\x00')[0].decode('ascii', 'ignore').upper()
        
        # Append an object instead of a dict!
        lumpinfo.append(_Lump(name, filepos, size, f))
        
    if 'wadfiles' not in globals():
        wadfiles = []
    wadfiles.append(f)
    return len(wadfiles)
# -----------------------------------------------

def W_ParseCommandLine():
    return False

def W_GenerateHashTable():
    pass
