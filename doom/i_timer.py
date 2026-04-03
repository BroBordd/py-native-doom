# i_timer.py
# Translated DOOM timer system logic

import time
import doomdef

# The standard DOOM tic rate is 35 Hz.
# (If your doomdef.py already defines this, we'll use it, otherwise fallback to 35)
TICRATE = getattr(doomdef, 'TICRATE', 35)

_basetime = 0.0

def I_InitTimer():
    """
    Initializes the timer subsystem. Sets the baseline time so I_GetTime
    returns counts starting from 0.
    """
    global _basetime
    _basetime = time.time()

def I_GetTime():
    """
    Returns the current time in DOOM tics.
    A tic is exactly 1/35th of a second.
    """
    global _basetime
    if _basetime == 0.0:
        I_InitTimer()
        
    elapsed = time.time() - _basetime
    return int(elapsed * TICRATE)

def I_GetTimeMS():
    """
    Returns the current time in milliseconds.
    Used by Chocolate DOOM for higher-resolution timing needs.
    """
    global _basetime
    if _basetime == 0.0:
        I_InitTimer()
        
    elapsed = time.time() - _basetime
    return int(elapsed * 1000.0)

def I_WaitVBL(count):
    """
    Wait for a specified number of vertical blanks (tics).
    This simulates Vanilla DOOM's function used to delay rendering
    or logic during specific scenarios like quitting or screen melts.
    """
    start_tic = I_GetTime()
    while (I_GetTime() - start_tic) < count:
        # Sleep for approx half a tic to yield the CPU, 
        # avoiding a 100% busy-wait loop while remaining accurate enough.
        time.sleep((1.0 / TICRATE) / 2.0)

def I_Sleep(ms):
    """
    Sleep for a specific number of milliseconds.
    """
    if ms > 0:
        time.sleep(ms / 1000.0)

def I_QuitTimer():
    """
    Cleanup function for the timer subsystem.
    In Python, there is no direct hardware timer hooking needed like in DOS,
    so this acts as a stub to maintain API parity.
    """
    pass
