# i_joystick.py
# Translated DOOM joystick and gamepad input subsystem

# Joystick direction constants
JOY_DIR_NONE  = 0
JOY_DIR_UP    = 1
JOY_DIR_DOWN  = 2
JOY_DIR_LEFT  = 4
JOY_DIR_RIGHT = 8

# Global configurations (typically set by config file / m_misc)
usejoystick = 0
joystick_port = 0

def I_InitJoystick():
    """
    Initialize the joystick subsystem.
    For a framebuffer/headless Python port, if you eventually use Pygame 
    or evdev for input, you would initialize those devices here.
    """
    global usejoystick
    if not usejoystick:
        return
    # Hardware initialization would go here.

def I_UpdateJoystick():
    """
    Poll the hardware for joystick changes and inject them into 
    the DOOM event queue (D_PostEvent).
    """
    if not usejoystick:
        return
    # Hardware polling would go here.

def I_QuitJoystick():
    """
    Clean up the joystick subsystem on exit.
    """
    pass

# ==============================================================================
# Event Data Extraction Utilities
# ==============================================================================
# In the DOOM event system (ev_joystick):
# ev.data1 = Button bitmask (bit 0 = button 0, bit 1 = button 1, etc.)
# ev.data6 = Packed directional data
#   Bits 0-3:   D-Pad
#   Bits 4-7:   Left Analog Stick
#   Bits 8-11:  Right Analog Stick
# ==============================================================================

def JOY_GET_DPAD(data6):
    """Extract D-Pad direction from data6."""
    return data6 & 0x0F

def JOY_GET_LSTICK(data6):
    """Extract Left Stick direction from data6."""
    return (data6 >> 4) & 0x0F

def JOY_GET_RSTICK(data6):
    """Extract Right Stick direction from data6."""
    return (data6 >> 8) & 0x0F

def JOY_BUTTON_MAPPED(button):
    """Check if a button index is valid (mapped)."""
    return button >= 0

def JOY_BUTTON_PRESSED(ev, button):
    """
    Check if a specific button is pressed in the given joystick event.
    """
    if not JOY_BUTTON_MAPPED(button):
        return False
    # ev.data1 contains the bitmask of currently pressed buttons
    return (ev.data1 & (1 << button)) != 0

def I_BindJoystickVariables():
    pass
