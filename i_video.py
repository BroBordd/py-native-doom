# i_video.py
# DESCRIPTION:
#   System-specific video interface. 
#   Acts as the bridge between the Doom engine and your external graphics hook.

import v_video

# Expose this to your external program! 
# It holds 768 bytes (256 colors * 3 bytes for R, G, B).
current_palette = bytearray(768)

def I_InitGraphics():
    """Called by D_DoomMain at startup."""
    pass

def I_ShutdownGraphics():
    """Called when the engine quits."""
    pass

def I_SetPalette(palette_data):
    """
    Called by the engine whenever the palette changes (pain, pickup, radsuit).
    palette_data is a byte array of 768 bytes (256 * RGB).
    """
    global current_palette
    # Copy the new palette data into our exposed bytearray
    current_palette[:] = palette_data

def I_UpdateNoBlit():
    pass

def I_FinishUpdate():
    """
    Called by D_Display at the end of every frame.
    Since you are polling `v_video.screens[0]` from an external program, 
    we just pass.
    """
    import r_draw
    import v_video
    if any(r_draw.screen):
        v_video.screens[0][:] = r_draw.screen

def I_ReadScreen(dest_bytearray):
    """
    Utility for the engine to read the screen (used in savegames/wipes).
    """
    dest_bytearray[:] = v_video.screens[0]

def I_BindVideoVariables():
    pass

def I_SetWindowTitle(title):
    print(f"Window title set to: {title}")

def I_GraphicsCheckCommandLine():
    pass


def I_SetGrabMouseCallback(callback):
    pass


def I_StartFrame():
    pass

