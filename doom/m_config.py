# m_config.py
#
# DESCRIPTION:
#       Configuration file loading and saving.
#       Replaces the C-style struct mapping with Python dynamic attributes.

import os
import m_controls
import hu_stuff

# -----------------------------------------------------------------------------
# ENGINE CONFIGURATION VARIABLES (GLOBALS)
# -----------------------------------------------------------------------------

mouseSensitivity = 5
showMessages = 1
detailLevel = 0
screenblocks = 10

snd_Channels = 3
snd_MusicVolume = 8
snd_SfxVolume = 8

use_mouse = 1
use_joystick = 0

# Default chat macros
chat_macros = [
    "No way!",
    "I'm out of here.",
    "Help!",
    "Gotcha!",
    "I'll be back.",
    "That sucks!",
    "Take that!",
    "Behind you!",
    "Oof.",
    "Yes."
]

config_file = "default.cfg"

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

def M_LoadDefaults():
    """
    Reads default.cfg and applies settings to globals and m_controls.
    """
    global mouseSensitivity, showMessages, detailLevel, screenblocks
    global snd_Channels, snd_MusicVolume, snd_SfxVolume
    global use_mouse, use_joystick

    # Populate hu_stuff chat macros with defaults
    for i in range(10):
        hu_stuff.chat_macros[i] = chat_macros[i]

    # In Python doom, hu_stuff might try to access showMessages directly
    hu_stuff.showMessages = showMessages

    if not os.path.exists(config_file):
        return # Use default hardcoded values if no config exists

    with open(config_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                key, val = parts[0], parts[1]
                
                try:
                    # Convert to int if it's a number
                    if val.lstrip('-').isdigit(): 
                        val = int(val)
                    
                    # Apply general settings
                    if key == "mouse_sensitivity": mouseSensitivity = val
                    elif key == "show_messages": showMessages = val
                    elif key == "detaillevel": detailLevel = val
                    elif key == "screenblocks": screenblocks = val
                    elif key == "snd_channels": snd_Channels = val
                    elif key == "snd_musicvolume": snd_MusicVolume = val
                    elif key == "snd_sfxvolume": snd_SfxVolume = val
                    elif key == "use_mouse": use_mouse = val
                    elif key == "use_joystick": use_joystick = val
                    
                    # Apply controls directly to m_controls module
                    elif hasattr(m_controls, key):
                        setattr(m_controls, key, val)
                        
                    # Apply chat macros
                    elif key.startswith("chatmacro"):
                        idx = int(key.replace("chatmacro", ""))
                        if 0 <= idx <= 9:
                            hu_stuff.chat_macros[idx] = str(val).strip('"')
                            
                except ValueError:
                    pass

    # Ensure hu_stuff has the updated value
    hu_stuff.showMessages = showMessages


def M_SaveDefaults():
    """
    Writes current settings back to default.cfg.
    """
    with open(config_file, "w") as f:
        f.write("# DOOM Python Port Configuration\n\n")
        
        f.write(f"mouse_sensitivity {mouseSensitivity}\n")
        f.write(f"show_messages {int(showMessages)}\n")
        f.write(f"detaillevel {detailLevel}\n")
        f.write(f"screenblocks {screenblocks}\n")
        f.write(f"snd_channels {snd_Channels}\n")
        f.write(f"snd_musicvolume {snd_MusicVolume}\n")
        f.write(f"snd_sfxvolume {snd_SfxVolume}\n")
        f.write(f"use_mouse {use_mouse}\n")
        f.write(f"use_joystick {use_joystick}\n\n")
        
        # Save standard bindings
        keys_to_save = [
            "key_right", "key_left", "key_up", "key_down",
            "key_fire", "key_use", "key_strafe", "key_speed",
            "key_map_toggle", "key_message_refresh"
        ]
        
        for k in keys_to_save:
            if hasattr(m_controls, k):
                f.write(f"{k} {getattr(m_controls, k)}\n")

        f.write("\n")
        
        # Save macros
        for i in range(10):
            f.write(f"chatmacro{i} \"{hu_stuff.chat_macros[i]}\"\n")

def M_SetConfigDir(path):
    pass

def M_SetConfigFilenames(main_config, extra_config):
    pass

def M_ApplyPlatformDefaults():
    pass

# --- Added by Claude to fix variable binding ---
if 'parsed_config' not in globals():
    parsed_config = {}
if 'bound_variables' not in globals():
    bound_variables = []

def M_BindIntVariable(config_key, module, var_name):
    bound_variables.append({'key': config_key, 'module': module, 'var_name': var_name, 'type': 'int'})
    if config_key in parsed_config:
        try:
            setattr(module, var_name, int(parsed_config[config_key]))
        except ValueError:
            pass

def M_BindFloatVariable(config_key, module, var_name):
    bound_variables.append({'key': config_key, 'module': module, 'var_name': var_name, 'type': 'float'})
    if config_key in parsed_config:
        try:
            setattr(module, var_name, float(parsed_config[config_key]))
        except ValueError:
            pass

def M_BindStringVariable(config_key, module, var_name):
    bound_variables.append({'key': config_key, 'module': module, 'var_name': var_name, 'type': 'str'})
    if config_key in parsed_config:
        setattr(module, var_name, str(parsed_config[config_key]))
# -----------------------------------------------

def M_GetAutoloadDir(name):
    return ""

def M_GetSaveGameDir(name):
    return "."
