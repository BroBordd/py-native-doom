# i_sound.py

import w_wad

def I_InitSound():
    """Initializes the sound system."""
    print("I_InitSound: Sound system initialized (Dummy)")

def I_UpdateSound():
    """Called every tick to update sound background tasks."""
    pass

def I_SubmitSound():
    """Submits sound to the audio buffer."""
    pass

def I_ShutdownSound():
    """Shuts down the sound system."""
    pass

def I_GetSfxLumpNum(sfxinfo):
    """
    Returns the WAD lump number for a specific sound effect.
    Doom sound lumps are prefixed with 'DS' (e.g., 'DSPISTOL').
    """
    # Assuming sfxinfo has a 'name' attribute like in C
    # We prefix 'DS' to the name as per Doom's engine design
    name = f"DS{sfxinfo.name}".upper()
    return w_wad.W_CheckNumForName(name)

def I_StartSound(id, vol, sep, pitch, priority):
    """
    Starts playing a sound.
    Returns a dummy channel handle (e.g., 0).
    """
    return 0

def I_StopSound(handle):
    """Stops playing a sound on the given channel handle."""
    pass

def I_SoundIsPlaying(handle):
    """Checks if a sound is still playing."""
    return False

def I_UpdateSoundParams(handle, vol, sep, pitch):
    """Updates panning and volume of a currently playing sound."""
    pass

def I_BindSoundVariables():
    pass

# --- Auto-generated Hardware Sound Stubs ---
def I_SetOPLDriverVer(ver):
    pass
opl_doom_1_9 = 1
opl_doom_1_666 = 0
def I_SetChannels(*args):
    pass
def I_SetSfxVolume(*args):
    pass
def I_SetMusicVolume(*args):
    pass

def I_PrecacheSounds(sounds, num_sounds):
    # Stubbed out for now. Later you can add sound precaching logic here.
    pass

snd_pitchshift = False

# Sound device constants
SNDDEVICE_NONE     = 0
SNDDEVICE_PCSPEAKER = 1
SNDDEVICE_ADLIB    = 2
SNDDEVICE_SB       = 3
SNDDEVICE_PAS      = 4
SNDDEVICE_GUS      = 5
SNDDEVICE_WAVEBLASTER = 6
SNDDEVICE_SOUNDCANVAS = 7
SNDDEVICE_GENMIDI  = 8
SNDDEVICE_AWE32    = 9
SNDDEVICE_DIGITAL  = 10

snd_sfxdevice   = SNDDEVICE_SB
snd_musicdevice = SNDDEVICE_GENMIDI

def I_RegisterSong(data, length):
    return 0

def I_PlaySong(handle, looping):
    pass

def I_PauseSong(handle):
    pass

def I_ResumeSong(handle):
    pass

def I_StopSong(handle):
    pass

def I_UnRegisterSong(handle):
    pass

def I_QrySongPlaying(handle):
    return False

def I_InitMusic():
    pass

def I_ShutdownMusic():
    pass
