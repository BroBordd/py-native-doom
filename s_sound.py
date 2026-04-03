#
# Copyright(C) 1993-1996 Id Software, Inc.
# Copyright(C) 2005-2014 Simon Howard
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# DESCRIPTION:
#	The not so system specific sound interface.
#

import doomstat
import r_main
import tables
import w_wad
import z_zone
import i_sound
import i_system
import m_random
import deh_str
from doomdef import FRACUNIT, FRACBITS
from sounds import *


# when to clip out sounds
# Does not fit the large outdoor areas.
S_CLIPPING_DIST = 1200 * FRACUNIT

# Distance tp origin when sounds should be maxed out.
# This should relate to movement clipping resolution
# (see BLOCKMAP handling).
# In the source code release: (160*FRACUNIT).  Changed back to the
# Vanilla value of 200 (why was this changed?)
S_CLOSE_DIST = 200 * FRACUNIT

# The range over which sound attenuates
S_ATTENUATOR = (S_CLIPPING_DIST - S_CLOSE_DIST) >> FRACBITS

# Stereo separation
S_STEREO_SWING = 96 * FRACUNIT

NORM_PRIORITY = 64
NORM_SEP = 128
NORM_PITCH = 128

class channel_t:
    def __init__(self):
        self.sfxinfo = None  # sound information (if null, channel avail.)
        self.origin = None   # origin of sound
        self.handle = 0      # handle of the sound being played
        self.pitch = 0


# The set of channels available
channels = []

# Maximum volume of a sound effect.
# Internal default is max out of 0-15.
sfxVolume = 8

# Maximum volume of music.
musicVolume = 8

# Internal volume level, ranging from 0-127
snd_SfxVolume = 0

# Whether songs are mus_paused
mus_paused = False

# Music currently being played
mus_playing = None

# Number of channels to use
snd_channels = 8


def S_Init(sfx_volume, music_volume):
    global channels, mus_paused
    
    if doomstat.gameversion == doomstat.exe_doom_1_666:
        if doomstat.logical_gamemission == doomstat.doom:
            i_sound.I_SetOPLDriverVer(i_sound.opl_doom1_1_666)
        else:
            i_sound.I_SetOPLDriverVer(i_sound.opl_doom2_1_666)
    else:
        i_sound.I_SetOPLDriverVer(i_sound.opl_doom_1_9)

    i_sound.I_PrecacheSounds(S_sfx, NUMSFX)

    S_SetSfxVolume(sfx_volume)
    S_SetMusicVolume(music_volume)

    # Allocating the internal channels for mixing
    # (the maximum numer of sounds rendered
    # simultaneously) within zone memory.
    channels = [channel_t() for _ in range(snd_channels)]

    # no sounds are playing, and they are not mus_paused
    mus_paused = False

    # Note that sounds have not been cached (yet).
    for i in range(1, NUMSFX):
        S_sfx[i].lumpnum = -1
        S_sfx[i].usefulness = -1

    # Doom defaults to pitch-shifting off.
    if i_sound.snd_pitchshift == -1:
        i_sound.snd_pitchshift = 0

    i_system.I_AtExit(S_Shutdown, True)


def S_Shutdown():
    i_sound.I_ShutdownSound()
    i_sound.I_ShutdownMusic()


def S_StopChannel(cnum):
    c = channels[cnum]

    if c.sfxinfo:
        # stop the sound playing
        if i_sound.I_SoundIsPlaying(c.handle):
            i_sound.I_StopSound(c.handle)

        # check to see if other channels are playing the sound
        # (This loop matches Vanilla Doom's logic, which iterates
        # without conditionally executing the usefulness degrade)
        for i in range(snd_channels):
            if cnum != i and c.sfxinfo == channels[i].sfxinfo:
                break

        # degrade usefulness of sound data
        c.sfxinfo.usefulness -= 1
        c.sfxinfo = None
        c.origin = None


def S_Start():
    global mus_paused

    # kill all playing sounds at start of level
    #  (trust me - a good idea)
    for cnum in range(snd_channels):
        if channels[cnum].sfxinfo:
            S_StopChannel(cnum)

    # start new music for the level
    mus_paused = False

    if doomstat.gamemode == doomstat.commercial:
        mnum = mus_runnin + doomstat.gamemap - 1
    else:
        spmus = [
            # Song - Who? - Where?
            mus_e3m4,        # American     e4m1
            mus_e3m2,        # Romero       e4m2
            mus_e3m3,        # Shawn        e4m3
            mus_e1m5,        # American     e4m4
            mus_e2m7,        # Tim          e4m5
            mus_e2m4,        # Romero       e4m6
            mus_e2m6,        # J.Anderson   e4m7 CHIRON.WAD
            mus_e2m5,        # Shawn        e4m8
            mus_e1m9,        # Tim          e4m9
        ]

        if doomstat.gameepisode < 4:
            mnum = mus_e1m1 + (doomstat.gameepisode - 1) * 9 + doomstat.gamemap - 1
        else:
            mnum = spmus[doomstat.gamemap - 1]

    S_ChangeMusic(mnum, True)


def S_StopSound(origin):
    for cnum in range(snd_channels):
        if channels[cnum].sfxinfo and channels[cnum].origin == origin:
            S_StopChannel(cnum)
            break


def S_GetChannel(origin, sfxinfo):
    # Find an open channel
    for cnum in range(snd_channels):
        if not channels[cnum].sfxinfo:
            break
        elif origin and channels[cnum].origin == origin:
            S_StopChannel(cnum)
            break
    else:
        # Executes if loop didn't break
        cnum = snd_channels

    # None available
    if cnum == snd_channels:
        # Look for lower priority
        for cnum in range(snd_channels):
            if channels[cnum].sfxinfo.priority >= sfxinfo.priority:
                break
        else:
            cnum = snd_channels

        if cnum == snd_channels:
            # FUCK!  No lower priority.  Sorry, Charlie.
            return -1
        else:
            # Otherwise, kick out lower priority.
            S_StopChannel(cnum)

    c = channels[cnum]

    # channel is decided to be cnum.
    c.sfxinfo = sfxinfo
    c.origin = origin

    return cnum


def S_AdjustSoundParams(listener, source):
    # calculate the distance to sound origin
    #  and clip it if necessary
    adx = abs(listener.x - source.x)
    ady = abs(listener.y - source.y)

    # From _GG1_ p.428. Appox. eucledian distance fast.
    approx_dist = adx + ady - (min(adx, ady) >> 1)

    if doomstat.gamemap != 8 and approx_dist > S_CLIPPING_DIST:
        return False, 0, 0

    # angle of source to listener
    angle = r_main.R_PointToAngle2(listener.x, listener.y, source.x, source.y)

    if angle > listener.angle:
        angle = (angle - listener.angle) & 0xffffffff
    else:
        angle = (angle + (0xffffffff - listener.angle)) & 0xffffffff

    angle >>= tables.ANGLETOFINESHIFT

    # stereo separation
    sep = 128 - ((S_STEREO_SWING * tables.finesine[angle]) >> FRACBITS)

    # volume calculation
    if approx_dist < S_CLOSE_DIST:
        vol = snd_SfxVolume
    elif doomstat.gamemap == 8:
        if approx_dist > S_CLIPPING_DIST:
            approx_dist = S_CLIPPING_DIST

        vol = 15 + ((snd_SfxVolume - 15) * ((S_CLIPPING_DIST - approx_dist) >> FRACBITS)) // S_ATTENUATOR
    else:
        # distance effect
        vol = (snd_SfxVolume * ((S_CLIPPING_DIST - approx_dist) >> FRACBITS)) // S_ATTENUATOR

    return (vol > 0), vol, sep


def Clamp(x):
    if x < 0:
        return 0
    elif x > 255:
        return 255
    return x


def S_StartSound(origin_p, sfx_id):
    origin = origin_p
    volume = snd_SfxVolume

    # check for bogus sound #
    if sfx_id < 1 or sfx_id > NUMSFX:
        i_system.I_Error("Bad sfx #: %d" % sfx_id)

    sfx = S_sfx[sfx_id]

    # Initialize sound parameters
    pitch = NORM_PITCH
    if sfx.link:
        volume += sfx.volume
        pitch = sfx.pitch

        if volume < 1:
            return

        if volume > snd_SfxVolume:
            volume = snd_SfxVolume

    # Check to see if it is audible,
    #  and if not, modify the params
    if origin and origin != doomstat.players[doomstat.consoleplayer].mo:
        rc, volume, sep = S_AdjustSoundParams(doomstat.players[doomstat.consoleplayer].mo, origin)

        if origin.x == doomstat.players[doomstat.consoleplayer].mo.x and \
           origin.y == doomstat.players[doomstat.consoleplayer].mo.y:
            sep = NORM_SEP

        if not rc:
            return
    else:
        sep = NORM_SEP

    # hacks to vary the sfx pitches
    if sfx_sawup <= sfx_id <= sfx_sawhit:
        pitch += 8 - (m_random.M_Random() & 15)
    elif sfx_id != sfx_itemup and sfx_id != sfx_tink:
        pitch += 16 - (m_random.M_Random() & 31)
        
    pitch = Clamp(pitch)

    # kill old sound
    S_StopSound(origin)

    # try to find a channel
    cnum = S_GetChannel(origin, sfx)

    if cnum < 0:
        return

    # increase the usefulness
    old_usefulness = sfx.usefulness
    sfx.usefulness += 1
    if old_usefulness < 0:
        sfx.usefulness = 1

    if sfx.lumpnum < 0:
        sfx.lumpnum = i_sound.I_GetSfxLumpNum(sfx)

    channels[cnum].pitch = pitch
    channels[cnum].handle = i_sound.I_StartSound(sfx, cnum, volume, sep, channels[cnum].pitch)


def S_PauseSound():
    global mus_paused
    if mus_playing and not mus_paused:
        i_sound.I_PauseSong()
        mus_paused = True


def S_ResumeSound():
    global mus_paused
    if mus_playing and mus_paused:
        i_sound.I_ResumeSong()
        mus_paused = False


def S_UpdateSounds(listener):
    i_sound.I_UpdateSound()

    for cnum in range(snd_channels):
        c = channels[cnum]
        sfx = c.sfxinfo

        if c.sfxinfo:
            if i_sound.I_SoundIsPlaying(c.handle):
                # initialize parameters
                volume = snd_SfxVolume
                sep = NORM_SEP

                if sfx.link:
                    volume += sfx.volume
                    if volume < 1:
                        S_StopChannel(cnum)
                        continue
                    elif volume > snd_SfxVolume:
                        volume = snd_SfxVolume

                # check non-local sounds for distance clipping
                #  or modify their params
                if c.origin and listener != c.origin:
                    audible, volume, sep = S_AdjustSoundParams(listener, c.origin)

                    if not audible:
                        S_StopChannel(cnum)
                    else:
                        i_sound.I_UpdateSoundParams(c.handle, volume, sep)
            else:
                # if channel is allocated but sound has stopped,
                #  free it
                S_StopChannel(cnum)


def S_SetMusicVolume(volume):
    if volume < 0 or volume > 127:
        i_system.I_Error("Attempt to set music volume at %d" % volume)

    i_sound.I_SetMusicVolume(volume)


def S_SetSfxVolume(volume):
    global snd_SfxVolume
    if volume < 0 or volume > 127:
        i_system.I_Error("Attempt to set sfx volume at %d" % volume)

    snd_SfxVolume = volume


def S_StartMusic(m_id):
    S_ChangeMusic(m_id, False)


def S_ChangeMusic(musicnum, looping):
    global mus_playing

    # The Doom IWAD file has two versions of the intro music: d_intro
    # and d_introa.  The latter is used for OPL playback.
    if musicnum == mus_intro and (i_sound.snd_musicdevice == i_sound.SNDDEVICE_ADLIB or \
                                  i_sound.snd_musicdevice == i_sound.SNDDEVICE_SB) and \
       w_wad.W_CheckNumForName("D_INTROA") >= 0:
        musicnum = mus_introa

    if musicnum <= mus_None or musicnum >= NUMMUSIC:
        i_system.I_Error("Bad music number %d" % musicnum)
    else:
        music = S_music[musicnum]

    if mus_playing == music:
        return

    # shutdown old music
    S_StopMusic()

    # get lumpnum if neccessary
    if not music.lumpnum:
        namebuf = "d_" + deh_str.DEH_String(music.name)
        music.lumpnum = w_wad.W_GetNumForName(namebuf)

    music.data = w_wad.W_CacheLumpNum(music.lumpnum, z_zone.PU_STATIC)

    handle = i_sound.I_RegisterSong(music.data, w_wad.W_LumpLength(music.lumpnum))
    music.handle = handle
    i_sound.I_PlaySong(handle, looping)

    mus_playing = music


def S_MusicPlaying():
    return i_sound.I_MusicIsPlaying()


def S_StopMusic():
    global mus_playing
    if mus_playing:
        if mus_paused:
            i_sound.I_ResumeSong()

        i_sound.I_StopSong()
        i_sound.I_UnRegisterSong(mus_playing.handle)
        w_wad.W_ReleaseLumpNum(mus_playing.lumpnum)
        mus_playing.data = None
        mus_playing = None
