# f_wipe.py
#
# DESCRIPTION:
#   Mission start screen wipe/melt, special effects.

import v_video
import i_video
from m_random import M_Random
from doomdef import SCREENWIDTH, SCREENHEIGHT

# --- Constants ---

wipe_ColorXForm = 0
wipe_Melt = 1
wipe_NUMWIPES = 2

# --- Global State ---

go = False
wipe_scr_start_bytes = None
wipe_scr_end_bytes = None
y_array = []

# --- Helper Functions ---

def wipe_shittyColMajorXform(array_view, width, height):
    """
    Rearranges a 1D row-major array into a 1D column-major array.
    Operates on a 16-bit view (`dpixel_t`), so width is SCREENWIDTH / 2.
    """
    dest = [0] * (width * height)
    for y in range(height):
        for x in range(width):
            dest[x * height + y] = array_view[y * width + x]
    
    # Copy back
    array_view[:] = dest

# --- ColorXForm Wipe (Basic Fade) ---

def wipe_initColorXForm(width, height, ticks):
    global wipe_scr_start_bytes
    v_video.screens[0][:] = wipe_scr_start_bytes
    return 0

def wipe_doColorXForm(width, height, ticks):
    global wipe_scr_end_bytes
    changed = False
    
    scr = v_video.screens[0]
    end = wipe_scr_end_bytes
    
    for i in range(width * height):
        w = scr[i]
        e = end[i]
        if w != e:
            if w > e:
                newval = w - ticks
                scr[i] = e if newval < e else newval
                changed = True
            elif w < e:
                newval = w + ticks
                scr[i] = e if newval > e else newval
                changed = True
                
    return 0 if changed else 1

def wipe_exitColorXForm(width, height, ticks):
    return 0

# --- Melt Wipe (The Iconic Doom Melt) ---

def wipe_initMelt(width, height, ticks):
    global y_array, wipe_scr_start_bytes, wipe_scr_end_bytes
    
    # copy start screen to main screen
    v_video.screens[0][:] = wipe_scr_start_bytes
    
    # Cast bytearrays to arrays of 16-bit unsigned shorts ('H')
    # This emulates the C code's (dpixel_t*) pointer casting.
    start_view = memoryview(wipe_scr_start_bytes).cast('H')
    end_view = memoryview(wipe_scr_end_bytes).cast('H')
    
    # makes this wipe faster to have stuff in column-major format
    wipe_shittyColMajorXform(start_view, width // 2, height)
    wipe_shittyColMajorXform(end_view, width // 2, height)
    
    # setup initial column positions (y < 0 => not ready to scroll yet)
    y_array = [0] * width
    y_array[0] = -(M_Random() % 16)
    for i in range(1, width):
        r = (M_Random() % 3) - 1
        y_array[i] = y_array[i - 1] + r
        if y_array[i] > 0:
            y_array[i] = 0
        elif y_array[i] == -16:
            y_array[i] = -15
            
    return 0

def wipe_doMelt(width, height, ticks):
    global y_array, wipe_scr_start_bytes, wipe_scr_end_bytes
    
    done = True
    width = width // 2
    
    start_view = memoryview(wipe_scr_start_bytes).cast('H')
    end_view = memoryview(wipe_scr_end_bytes).cast('H')
    scr_view = memoryview(v_video.screens[0]).cast('H')
    
    while ticks > 0:
        ticks -= 1
        for i in range(width):
            if y_array[i] < 0:
                y_array[i] += 1
                done = False
            elif y_array[i] < height:
                dy = (y_array[i] + 1) if (y_array[i] < 16) else 8
                if y_array[i] + dy >= height:
                    dy = height - y_array[i]
                
                # Copy from wipe_scr_end (column-major) to screen (row-major)
                s_idx = i * height + y_array[i]
                d_idx = y_array[i] * width + i
                for j in range(dy):
                    scr_view[d_idx] = end_view[s_idx]
                    s_idx += 1
                    d_idx += width
                    
                y_array[i] += dy
                
                # Copy from wipe_scr_start (column-major) to screen (row-major)
                s_idx = i * height
                d_idx = y_array[i] * width + i
                for j in range(height - y_array[i]):
                    scr_view[d_idx] = start_view[s_idx]
                    s_idx += 1
                    d_idx += width
                    
                done = False
                
    return 1 if done else 0

def wipe_exitMelt(width, height, ticks):
    global y_array, wipe_scr_start_bytes, wipe_scr_end_bytes
    
    y_array = []
    wipe_scr_start_bytes = None
    wipe_scr_end_bytes = None
    
    return 0

# Function map replacing the C function pointer array
wipes = [
    (wipe_initColorXForm, wipe_doColorXForm, wipe_exitColorXForm),
    (wipe_initMelt, wipe_doMelt, wipe_exitMelt)
]

# --- Main API ---

def wipe_StartScreen(x, y, width, height):
    global wipe_scr_start_bytes
    wipe_scr_start_bytes = bytearray(SCREENWIDTH * SCREENHEIGHT)
    i_video.I_ReadScreen(wipe_scr_start_bytes)
    return 0

def wipe_EndScreen(x, y, width, height):
    global wipe_scr_end_bytes, wipe_scr_start_bytes
    wipe_scr_end_bytes = bytearray(SCREENWIDTH * SCREENHEIGHT)
    i_video.I_ReadScreen(wipe_scr_end_bytes)
    
    # Restore start screen to the main buffer
    v_video.screens[0][:] = wipe_scr_start_bytes
    return 0

def wipe_ScreenWipe(wipeno, x, y, width, height, ticks):
    global go
    
    # Check for valid wipeno to prevent index errors
    if wipeno < 0 or wipeno >= wipe_NUMWIPES:
        return 0
        
    init_func, do_func, exit_func = wipes[wipeno]
    
    # initial stuff
    if not go:
        go = True
        init_func(width, height, ticks)
        
    # do a piece of wipe-in (Note: MarkRect ignored since handled by modern display hooks)
    rc = do_func(width, height, ticks)
    
    # final stuff
    if rc != 0:
        go = False
        exit_func(width, height, ticks)
        
    return int(not go)
