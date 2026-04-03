# z_zone.py

# Memory tags used by Doom
PU_STATIC      = 1    # Static entire execution time
PU_SOUND       = 2    # Static while playing
PU_MUSIC       = 3    # Static while playing
PU_DAVE        = 4    # Anything else Dave wants static
PU_LEVEL       = 50   # Static until level exited
PU_LEVSPEC     = 51   # A special thinker in a level
PU_PURGELEVEL  = 100
PU_CACHE       = 101

def Z_Init():
    """Initialize the zone memory allocator."""
    pass

def Z_Malloc(size, tag, user):
    """
    Allocate memory. 
    In C, this returns a void pointer. In Python, we return a zeroed bytearray 
    that acts like a raw buffer the rest of the engine can read/write to.
    """
    return bytearray(size)

def Z_Free(ptr):
    """
    Free memory. 
    In Python, the Garbage Collector handles this, so we can just pass.
    """
    pass

def Z_ChangeTag(ptr, tag):
    """Change the purge tag on a block of memory."""
    pass

def Z_CheckHeap():
    """Debugging function to check memory corruption."""
    pass

def Z_FreeTags(lowtag, hightag):
    """Frees all blocks with tags in the specified range."""
    pass
