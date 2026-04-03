# doomkeys.py
#
# DESCRIPTION:
#	Key codes for Doom key events.

#
# DOOM keyboard definition.
# This is the stuff configured by Setup.Exe.
# Most key data are simple ascii (uppercased).
#

KEY_RIGHTARROW	= 0xae
KEY_LEFTARROW	= 0xac
KEY_UPARROW		= 0xad
KEY_DOWNARROW	= 0xaf
KEY_ESCAPE		= 27
KEY_ENTER		= 13
KEY_TAB			= 9

KEY_CAPSLOCK = 0x3A
KEY_SCRLCK   = 0x46
KEY_NUMLOCK  = 0x45

KE_ENTER     = 13   # m_menu.py specifically looks for KE_ENTER
KE_ESCAPE    = 27   # m_menu.py specifically looks for KE_ESCAPE

# Missing from your current file but used in hu_stuff.py
KEY_LALT     = 0x38

KEY_F1			= (0x80+0x3b)
KEY_F2			= (0x80+0x3c)
KEY_F3			= (0x80+0x3d)
KEY_F4			= (0x80+0x3e)
KEY_F5			= (0x80+0x3f)
KEY_F6			= (0x80+0x40)
KEY_F7			= (0x80+0x41)
KEY_F8			= (0x80+0x42)
KEY_F9			= (0x80+0x43)
KEY_F10			= (0x80+0x44)
KEY_F11			= (0x80+0x57)
KEY_F12			= (0x80+0x58)

KEY_BACKSPACE	= 127
KEY_PAUSE		= 0xff

KEY_EQUALS		= 0x3d
KEY_MINUS		= 0x2d

KEY_RSHIFT		= (0x80+0x36)
KEY_RCTRL		= (0x80+0x1d)
KEY_RALT		= (0x80+0x38)

KEY_LALT		= KEY_RALT

# Menu Navigation & Interaction
key_menu_activate  = 0x0D  # Enter
key_menu_back      = 0x1B  # Escape (standard)
key_menu_confirm   = ord('y')
key_menu_abort     = ord('n')
key_menu_up        = 0x48  # Arrow Up
key_menu_down      = 0x50  # Arrow Down
key_menu_left      = 0x4B  # Arrow Left
key_menu_right     = 0x4D  # Arrow Right
key_menu_forward   = 0x0D  # Often same as activate
KEY_ESCAPE         = 0x1B

# Function Keys (F1 - F12)
key_menu_help      = 0x3B  # F1
key_menu_save      = 0x3C  # F2
key_menu_load      = 0x3D  # F3
key_menu_volume    = 0x3E  # F4
key_menu_detail    = 0x3F  # F5
key_menu_qsave     = 0x40  # F6 (QuickSave)
key_menu_endgame   = 0x41  # F7
key_menu_messages  = 0x42  # F8
key_menu_qload     = 0x43  # F9 (QuickLoad)
key_menu_quit      = 0x44  # F10
key_menu_gamma     = 0x57  # F11
key_menu_screenshot = 0x61 # F12 (as per your previous fix)

# Screen Size
key_menu_decscreen = 0x2D  # '-'
key_menu_incscreen = 0x3D  # '='

# Automap (AM_) Keys
key_map_toggle     = ord('f') # Tab is standard, but 'f' often used in ports
key_map_north      = 0x48
key_map_south      = 0x50
key_map_east       = 0x4D
key_map_west       = 0x4B
key_map_zoomin     = ord('=')
key_map_zoomout    = ord('-')
key_map_maxzoom    = ord('0')
key_map_follow     = ord('f')
key_map_grid       = ord('g')
key_map_mark       = ord('m')
key_map_clearmark  = ord('c')

# Gameplay (referenced in m_config)
key_right          = 0x4D
key_left           = 0x4B
key_up             = 0x48
key_down           = 0x50
key_fire           = 0x1D  # Ctrl
key_use            = 0x20  # Space
key_strafe         = 0x38  # Alt
key_speed          = 0x2A  # Shift
key_message_refresh = ord('r')
key_multi_msg      = ord('t')
