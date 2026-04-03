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
#	Event handling definitions.
#

# -----------------------------------------------------------------------------
# evtype_t - Event types
# -----------------------------------------------------------------------------

ev_keydown  = 0
ev_keyup    = 1
ev_mouse    = 2
ev_joystick = 3
ev_quit = 4

# -----------------------------------------------------------------------------
# event_t
# -----------------------------------------------------------------------------
# Represents a single input event in the engine's event queue.
# -----------------------------------------------------------------------------

class event_t:
    """
    Event structure.
    
    Attributes:
        type (int): One of the ev_* constants (ev_keydown, ev_mouse, etc).
        data1 (int): Keys / mouse/joystick buttons.
        data2 (int): Mouse/joystick x move.
        data3 (int): Mouse/joystick y move.
    """
    __slots__ = ['type', 'data1', 'data2', 'data3']

    def __init__(self, type=0, data1=0, data2=0, data3=0):
        self.type = type
        self.data1 = data1
        self.data2 = data2
        self.data3 = data3
        
    def __repr__(self):
        return f"<event_t type={self.type} data1={self.data1} data2={self.data2} data3={self.data3}>"
