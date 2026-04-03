# hu_stuff.py
#
# DESCRIPTION: Heads-up displays
# Ported from Doom C source to Python

from doomdef import *
from doomstat import *
from dstrings import *
from doomkeys import *
from sounds import *
import m_controls
import hu_lib
from w_wad import W_CacheLumpName
from z_zone import PU_STATIC
from deh_main import DEH_String
from s_sound import S_StartSound

try:
    import i_input
except ImportError:
    i_input = None

# -----------------------------------------------------------------------------
# hu_stuff.h CONSTANTS
# -----------------------------------------------------------------------------

HU_FONTSTART = ord('!')   # the first font characters
HU_FONTEND   = ord('_')   # the last font characters
HU_FONTSIZE  = HU_FONTEND - HU_FONTSTART + 1

HU_BROADCAST = 5

HU_MSGX      = 0
HU_MSGY      = 0
HU_MSGWIDTH  = 64         # in characters
HU_MSGHEIGHT = 1          # in lines

HU_MSGTIMEOUT = 4 * TICRATE

# -----------------------------------------------------------------------------
# LOCALS / GLOBALS
# -----------------------------------------------------------------------------

# Player chat colors/names
player_names = [
    HUSTR_PLRGREEN,
    HUSTR_PLRINDIGO,
    HUSTR_PLRBROWN,
    HUSTR_PLRRED
]

chat_macros = [""] * 10

hu_font = [None] * HU_FONTSIZE
w_title = hu_lib.hu_textline_t()
w_chat = hu_lib.hu_itext_t()
w_message = hu_lib.hu_stext_t()
w_inputbuffer = [hu_lib.hu_itext_t() for _ in range(MAXPLAYERS)]

# Passed by reference (equivalent to pointers in C) to HU_lib
chat_on    = [False]
message_on = [False]
always_off = [False]

message_dontfuckwithme = False
message_nottobefuckedwith = False
headsupactive = False
message_counter = 0

chat_dest = [0] * MAXPLAYERS

QUEUESIZE = 128
chatchars = [0] * QUEUESIZE
head = 0
tail = 0

# Responder static variables
lastmessage = ""
altdown = False
num_nobrainers = 0


# -----------------------------------------------------------------------------
# MAP NAMES
# -----------------------------------------------------------------------------

mapnames = [
    HUSTR_E1M1, HUSTR_E1M2, HUSTR_E1M3, HUSTR_E1M4, HUSTR_E1M5,
    HUSTR_E1M6, HUSTR_E1M7, HUSTR_E1M8, HUSTR_E1M9,

    HUSTR_E2M1, HUSTR_E2M2, HUSTR_E2M3, HUSTR_E2M4, HUSTR_E2M5,
    HUSTR_E2M6, HUSTR_E2M7, HUSTR_E2M8, HUSTR_E2M9,

    HUSTR_E3M1, HUSTR_E3M2, HUSTR_E3M3, HUSTR_E3M4, HUSTR_E3M5,
    HUSTR_E3M6, HUSTR_E3M7, HUSTR_E3M8, HUSTR_E3M9,

    HUSTR_E4M1, HUSTR_E4M2, HUSTR_E4M3, HUSTR_E4M4, HUSTR_E4M5,
    HUSTR_E4M6, HUSTR_E4M7, HUSTR_E4M8, HUSTR_E4M9,

    "NEWLEVEL", "NEWLEVEL", "NEWLEVEL", "NEWLEVEL", "NEWLEVEL",
    "NEWLEVEL", "NEWLEVEL", "NEWLEVEL", "NEWLEVEL"
]

mapnames_chex = [
    HUSTR_E1M1, HUSTR_E1M2, HUSTR_E1M3, HUSTR_E1M4, HUSTR_E1M5,
    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,

    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,
    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,

    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,
    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,

    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,
    HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5, HUSTR_E1M5,

    "NEWLEVEL", "NEWLEVEL", "NEWLEVEL", "NEWLEVEL", "NEWLEVEL",
    "NEWLEVEL", "NEWLEVEL", "NEWLEVEL", "NEWLEVEL"
]

mapnames_commercial = [
    # DOOM 2 map names.
    HUSTR_1, HUSTR_2, HUSTR_3, HUSTR_4, HUSTR_5, HUSTR_6, HUSTR_7,
    HUSTR_8, HUSTR_9, HUSTR_10, HUSTR_11, HUSTR_12, HUSTR_13, HUSTR_14,
    HUSTR_15, HUSTR_16, HUSTR_17, HUSTR_18, HUSTR_19, HUSTR_20, HUSTR_21,
    HUSTR_22, HUSTR_23, HUSTR_24, HUSTR_25, HUSTR_26, HUSTR_27, HUSTR_28,
    HUSTR_29, HUSTR_30, HUSTR_31, HUSTR_32,

    # Plutonia WAD map names.
    PHUSTR_1, PHUSTR_2, PHUSTR_3, PHUSTR_4, PHUSTR_5, PHUSTR_6, PHUSTR_7,
    PHUSTR_8, PHUSTR_9, PHUSTR_10, PHUSTR_11, PHUSTR_12, PHUSTR_13, PHUSTR_14,
    PHUSTR_15, PHUSTR_16, PHUSTR_17, PHUSTR_18, PHUSTR_19, PHUSTR_20, PHUSTR_21,
    PHUSTR_22, PHUSTR_23, PHUSTR_24, PHUSTR_25, PHUSTR_26, PHUSTR_27, PHUSTR_28,
    PHUSTR_29, PHUSTR_30, PHUSTR_31, PHUSTR_32,
    
    # TNT WAD map names.
    THUSTR_1, THUSTR_2, THUSTR_3, THUSTR_4, THUSTR_5, THUSTR_6, THUSTR_7,
    THUSTR_8, THUSTR_9, THUSTR_10, THUSTR_11, THUSTR_12, THUSTR_13, THUSTR_14,
    THUSTR_15, THUSTR_16, THUSTR_17, THUSTR_18, THUSTR_19, THUSTR_20, THUSTR_21,
    THUSTR_22, THUSTR_23, THUSTR_24, THUSTR_25, THUSTR_26, THUSTR_27, THUSTR_28,
    THUSTR_29, THUSTR_30, THUSTR_31, THUSTR_32,

    # Emulation: TNT maps 33-35
    "", "", ""
]

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

def HU_Init():
    global hu_font
    j = HU_FONTSTART
    for i in range(HU_FONTSIZE):
        lumpname = f"STCFN{j:03d}"
        hu_font[i] = W_CacheLumpName(lumpname, PU_STATIC)
        j += 1


def HU_Stop():
    global headsupactive
    headsupactive = False


def HU_Start():
    global headsupactive, message_on, message_dontfuckwithme
    global message_nottobefuckedwith, chat_on

    if headsupactive:
        HU_Stop()

    plr = players[consoleplayer]
    message_on[0] = False
    message_dontfuckwithme = False
    message_nottobefuckedwith = False
    chat_on[0] = False

    # create the message widget
    hu_lib.HUlib_initSText(w_message, HU_MSGX, HU_MSGY, HU_MSGHEIGHT, hu_font, HU_FONTSTART, message_on)

    HU_TITLEX = 0
    HU_TITLEY = 167 - hu_font[0].height

    # create the map title widget
    hu_lib.HUlib_initTextLine(w_title, HU_TITLEX, HU_TITLEY, hu_font, HU_FONTSTART)
    
    s = "Unknown level"
    if logical_gamemission == doom:
        s = mapnames[(gameepisode-1)*9 + gamemap - 1]
    elif logical_gamemission == doom2:
        s = mapnames_commercial[gamemap - 1]
        # Pre-Final Doom compatibility: map33-map35 names don't spill over
        if gameversion <= exe_doom_1_9 and gamemap >= 33:
            s = ""
    elif logical_gamemission == pack_plut:
        s = mapnames_commercial[gamemap - 1 + 32]
    elif logical_gamemission == pack_tnt:
        s = mapnames_commercial[gamemap - 1 + 64]

    if logical_gamemission == doom and gameversion == exe_chex:
        s = mapnames_chex[(gameepisode-1)*9 + gamemap - 1]

    # dehacked substitution to get modified level name
    s = DEH_String(s)
    
    for char in s:
        hu_lib.HUlib_addCharToTextLine(w_title, ord(char))

    HU_INPUTX = HU_MSGX
    HU_INPUTY = HU_MSGY + HU_MSGHEIGHT * (hu_font[0].height + 1)

    # create the chat widget
    hu_lib.HUlib_initIText(w_chat, HU_INPUTX, HU_INPUTY, hu_font, HU_FONTSTART, chat_on)

    # create the inputbuffer widgets
    for i in range(MAXPLAYERS):
        hu_lib.HUlib_initIText(w_inputbuffer[i], 0, 0, hu_font, HU_FONTSTART, always_off)

    headsupactive = True


def HU_Drawer():
    hu_lib.HUlib_drawSText(w_message)
    hu_lib.HUlib_drawIText(w_chat)
    if automapactive:
        hu_lib.HUlib_drawTextLine(w_title, False)


def HU_Erase():
    hu_lib.HUlib_eraseSText(w_message)
    hu_lib.HUlib_eraseIText(w_chat)
    hu_lib.HUlib_eraseTextLine(w_title)


def HU_Ticker():
    global message_counter, message_on, message_nottobefuckedwith
    global message_dontfuckwithme

    # tick down message counter if message is up
    if message_counter > 0:
        message_counter -= 1
        if message_counter == 0:
            message_on[0] = False
            message_nottobefuckedwith = False

    plr = players[consoleplayer]

    if showMessages or message_dontfuckwithme:
        # display message if necessary
        if (plr.message and not message_nottobefuckedwith) or (plr.message and message_dontfuckwithme):
            hu_lib.HUlib_addMessageToSText(w_message, 0, plr.message)
            plr.message = None
            message_on[0] = True
            message_counter = HU_MSGTIMEOUT
            message_nottobefuckedwith = message_dontfuckwithme
            message_dontfuckwithme = False

    # check for incoming chat characters
    if netgame:
        for i in range(MAXPLAYERS):
            if not playeringame[i]:
                continue
            
            c = players[i].cmd.chatchar
            if i != consoleplayer and c:
                if c <= HU_BROADCAST:
                    chat_dest[i] = c
                else:
                    rc = hu_lib.HUlib_keyInIText(w_inputbuffer[i], c)
                    if rc and c == KEY_ENTER:
                        if w_inputbuffer[i].l.len and (chat_dest[i] == consoleplayer + 1 or chat_dest[i] == HU_BROADCAST):
                            hu_lib.HUlib_addMessageToSText(w_message, DEH_String(player_names[i]), w_inputbuffer[i].l.l)
                            
                            message_nottobefuckedwith = True
                            message_on[0] = True
                            message_counter = HU_MSGTIMEOUT
                            
                            if gamemode == commercial:
                                S_StartSound(None, sfx_radio)
                            elif gameversion > exe_doom_1_2:
                                S_StartSound(None, sfx_tink)
                        hu_lib.HUlib_resetIText(w_inputbuffer[i])
                players[i].cmd.chatchar = 0


def HU_queueChatChar(c):
    global head
    plr = players[consoleplayer]
    if ((head + 1) & (QUEUESIZE - 1)) == tail:
        plr.message = DEH_String(HUSTR_MSGU)
    else:
        chatchars[head] = c
        head = (head + 1) & (QUEUESIZE - 1)


def HU_dequeueChatChar():
    global tail
    if head != tail:
        c = chatchars[tail]
        tail = (tail + 1) & (QUEUESIZE - 1)
    else:
        c = 0
    return c


def StartChatInput(dest):
    chat_on[0] = True
    hu_lib.HUlib_resetIText(w_chat)
    HU_queueChatChar(HU_BROADCAST)

    if i_input is not None:
        i_input.I_StartTextInput(0, 8, SCREENWIDTH, 16)


def StopChatInput():
    chat_on[0] = False
    if i_input is not None:
        i_input.I_StopTextInput()


def HU_Responder(ev):
    global lastmessage, altdown, num_nobrainers
    global message_on, message_counter

    numplayers = sum(1 for i in range(MAXPLAYERS) if playeringame[i])

    if ev.data1 == KEY_RSHIFT:
        return False
    elif ev.data1 in (KEY_RALT, KEY_LALT):
        altdown = (ev.type == ev_keydown)
        return False

    if ev.type != ev_keydown:
        return False

    eatkey = False
    plr = players[consoleplayer]

    if not chat_on[0]:
        if ev.data1 == m_controls.key_message_refresh:
            message_on[0] = True
            message_counter = HU_MSGTIMEOUT
            eatkey = True
        elif netgame and ev.data2 == m_controls.key_multi_msg:
            eatkey = True
            StartChatInput(HU_BROADCAST)
        elif netgame and numplayers > 2:
            for i in range(MAXPLAYERS):
                if ev.data2 == m_controls.key_multi_msgplayer[i]:
                    if playeringame[i] and i != consoleplayer:
                        eatkey = True
                        StartChatInput(i + 1)
                        break
                    elif i == consoleplayer:
                        num_nobrainers += 1
                        if num_nobrainers < 3:
                            plr.message = DEH_String(HUSTR_TALKTOSELF1)
                        elif num_nobrainers < 6:
                            plr.message = DEH_String(HUSTR_TALKTOSELF2)
                        elif num_nobrainers < 9:
                            plr.message = DEH_String(HUSTR_TALKTOSELF3)
                        elif num_nobrainers < 32:
                            plr.message = DEH_String(HUSTR_TALKTOSELF4)
                        else:
                            plr.message = DEH_String(HUSTR_TALKTOSELF5)
    else:
        # send a macro
        if altdown:
            c = ev.data1 - ord('0')
            if c > 9 or c < 0:
                return False

            macromessage = chat_macros[c]

            # kill last message with a '\n'
            HU_queueChatChar(KEY_ENTER)

            # send the macro message
            for char in macromessage:
                # Store char's byte representation
                char_val = ord(char) if isinstance(char, str) else char
                HU_queueChatChar(char_val)
                
            HU_queueChatChar(KEY_ENTER)

            # leave chat mode and notify that it was sent
            StopChatInput()
            lastmessage = str(chat_macros[c])
            plr.message = lastmessage
            eatkey = True
        else:
            c = ev.data3

            eatkey = hu_lib.HUlib_keyInIText(w_chat, c)
            if eatkey:
                HU_queueChatChar(c)

            if c == KEY_ENTER:
                StopChatInput()
                if w_chat.l.len:
                    # In Python, assuming l.l resolves to the string or list of characters
                    msg = "".join([chr(ch) if isinstance(ch, int) else ch for ch in w_chat.l.l]) if isinstance(w_chat.l.l, list) else w_chat.l.l
                    lastmessage = str(msg)
                    plr.message = lastmessage
            elif c == KEY_ESCAPE:
                StopChatInput()

    return eatkey
