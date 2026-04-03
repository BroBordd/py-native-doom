#
# Copyright(C) 1993-1996 Id Software, Inc.
# Copyright(C) 2005-2014 Simon Howard
# Copyright(C) 2025 Python Port Contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# DESCRIPTION:
#	Cheat sequence checking.
#

# -----------------------------------------------------------------------------
# cheatseq_t
# -----------------------------------------------------------------------------

class cheatseq_t:
    """
    Cheat sequence structure.
    """
    __slots__ = ['sequence', 'p']

    def __init__(self, sequence, p=0):
        # We need a mutable bytearray to faithfully simulate DOOM's 
        # in-place sequence modification for parameterized cheats.
        if isinstance(sequence, str):
            self.sequence = bytearray(sequence.encode('ascii'))
        elif isinstance(sequence, bytes):
            self.sequence = bytearray(sequence)
        elif isinstance(sequence, list):
            self.sequence = bytearray(sequence)
        else:
            self.sequence = bytearray(sequence)
            
        # Ensure null-termination as expected by C strings
        if not self.sequence or self.sequence[-1] != 0:
            self.sequence.append(0)
            
        self.p = p

def CHEAT(seq, p=0):
    """
    Helper macro functionally identical to the C CHEAT() macro.
    """
    return cheatseq_t(seq, p)

# -----------------------------------------------------------------------------
# cht_CheckCheat
# -----------------------------------------------------------------------------

def cht_CheckCheat(cht, key):
    """
    Checks a key against a cheat sequence.
    Returns True if the cheat was successfully completed.
    """
    rc = False

    if isinstance(key, str) and len(key) > 0:
        key = ord(key[0])
    
    key &= 0xFF

    if cht.p >= len(cht.sequence):
        cht.p = 0
        
    p = cht.p
    seq = cht.sequence

    if seq[p] == 0:
        rc = True
    elif key == seq[p]:
        cht.p += 1
    # 1 and 255 are placeholder chars in DOOM that capture parameters
    elif seq[p] == 1 or seq[p] == 255:
        seq[p] = key
        cht.p += 1
    elif key == seq[0]:
        cht.p = 1
    else:
        cht.p = 0

    # If we reached the end (null terminator), the cheat was successfully entered.
    if cht.p < len(seq) and seq[cht.p] == 0:
        rc = True
        cht.p = 0

    return rc

# -----------------------------------------------------------------------------
# cht_GetParam
# -----------------------------------------------------------------------------

def cht_GetParam(cht, buffer=None):
    """
    Extracts the parameter of a cheat sequence.
    In C, this populates a passed buffer. In Python, it optionally populates 
    a list/bytearray buffer and returns the parameter as a string.
    """
    p = 0
    seq = cht.sequence

    # Find start marker: while (*(p++) != 1);
    while p < len(seq):
        val = seq[p]
        p += 1
        if val == 1:
            break

    res = bytearray()
    
    # Read parameters: do { c = *p; *(buffer++) = c; *(p++) = 0; } while (c && *p!=255)
    if p < len(seq):
        while True:
            c = seq[p]
            res.append(c)
            seq[p] = 0
            p += 1
            
            if not c or (p < len(seq) and seq[p] == 255):
                break

        if p < len(seq) and seq[p] == 255:
            res.append(0)

    if buffer is not None:
        buffer.extend(res)
        
    return res.decode('ascii', errors='ignore').rstrip('\x00')
