# hu_lib.py
#
# DESCRIPTION: heads-up text and input code
# Ported from Doom C source to Python

import doomstat
from doomdef import SCREENWIDTH
from doomkeys import KEY_BACKSPACE, KEY_ENTER

# Standard C Doom renderer imports (assuming standard port structure)
try:
    import v_video
except ImportError:
    v_video = None

try:
    import r_draw
except ImportError:
    r_draw = None

try:
    import r_main
except ImportError:
    r_main = None

# -----------------------------------------------------------------------------
# hu_lib.h CONSTANTS
# -----------------------------------------------------------------------------

HU_CHARERASE     = KEY_BACKSPACE
HU_MAXLINES      = 4
HU_MAXLINELENGTH = 80

# Helper macro for endian-swapping in WADs. Assuming structs are already parsed 
# natively in Python, we can just return the int.
def SHORT(x):
    return x

# -----------------------------------------------------------------------------
# CLASSES (equivalent to structs)
# -----------------------------------------------------------------------------

class hu_textline_t:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.f = None           # font (list of patches)
        self.sc = 0             # start character (ord)
        self.l = []             # line of text (list of chars)
        self.len = 0            # current line length
        self.needsupdate = 0    # whether this line needs to be updated


class hu_stext_t:
    def __init__(self):
        self.l = [hu_textline_t() for _ in range(HU_MAXLINES)]
        self.h = 0              # height in lines
        self.cl = 0             # current line number
        self.on = None          # reference to boolean (list with 1 element)
        self.laston = False


class hu_itext_t:
    def __init__(self):
        self.l = hu_textline_t()
        self.lm = 0             # left margin past which I am not to delete characters
        self.on = None          # reference to boolean (list with 1 element)
        self.laston = False


# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

def HUlib_init():
    pass


def HUlib_clearTextLine(t: hu_textline_t):
    t.l.clear()
    t.len = 0
    t.needsupdate = 1 # true in C boolean


def HUlib_initTextLine(t: hu_textline_t, x, y, f, sc):
    t.x = x
    t.y = y
    t.f = f
    t.sc = sc
    HUlib_clearTextLine(t)


def HUlib_addCharToTextLine(t: hu_textline_t, ch):
    if t.len == HU_MAXLINELENGTH:
        return False
    else:
        # ensuring we store strings or ints properly; let's store 1-length string or raw char
        t.l.append(ch)
        t.len += 1
        t.needsupdate = 4
        return True


def HUlib_delCharFromTextLine(t: hu_textline_t):
    if not t.len:
        return False
    else:
        t.l.pop()
        t.len -= 1
        t.needsupdate = 4
        return True


def HUlib_drawTextLine(l: hu_textline_t, drawcursor: bool):
    x = l.x
    for i in range(l.len):
        ch = l.l[i]
        
        # Determine the ascii value
        if isinstance(ch, int):
            c_val = ch
        else:
            c_val = ord(ch)
            
        c_upper = ord(chr(c_val).upper()) if c_val < 128 else c_val

        if c_upper != ord(' ') and c_upper >= l.sc and c_upper <= ord('_'):
            w = SHORT(l.f[c_upper - l.sc].width)
            if x + w > SCREENWIDTH:
                break
            if v_video is not None:
                v_video.V_DrawPatchDirect(x, l.y, l.f[c_upper - l.sc])
            x += w
        else:
            x += 4
            if x >= SCREENWIDTH:
                break

    # draw the cursor if requested
    if drawcursor and x + SHORT(l.f[ord('_') - l.sc].width) <= SCREENWIDTH:
        if v_video is not None:
            v_video.V_DrawPatchDirect(x, l.y, l.f[ord('_') - l.sc])


def HUlib_eraseTextLine(l: hu_textline_t):
    # Only erases when NOT in automap and the screen is reduced
    
    # We retrieve viewport vars safely. They usually live in r_main
    vw_x = getattr(r_main, 'viewwindowx', 0) if r_main else 0
    vw_y = getattr(r_main, 'viewwindowy', 0) if r_main else 0
    vw_w = getattr(r_main, 'viewwidth', 0) if r_main else 0
    vw_h = getattr(r_main, 'viewheight', 0) if r_main else 0

    automapactive = getattr(doomstat, 'automapactive', False)

    if not automapactive and vw_x and l.needsupdate:
        lh = SHORT(l.f[0].height) + 1
        yoffset = l.y * SCREENWIDTH
        
        for y in range(l.y, l.y + lh):
            if y < vw_y or y >= vw_y + vw_h:
                if r_draw is not None:
                    r_draw.R_VideoErase(yoffset, SCREENWIDTH)
            else:
                if r_draw is not None:
                    r_draw.R_VideoErase(yoffset, vw_x)
                    r_draw.R_VideoErase(yoffset + vw_x + vw_w, vw_x)
            yoffset += SCREENWIDTH

    if l.needsupdate > 0:
        l.needsupdate -= 1


def HUlib_initSText(s: hu_stext_t, x, y, h, font, startchar, on):
    s.h = h
    s.on = on
    s.laston = True
    s.cl = 0
    for i in range(h):
        HUlib_initTextLine(s.l[i], x, y - i * (SHORT(font[0].height) + 1), font, startchar)


def HUlib_addLineToSText(s: hu_stext_t):
    s.cl += 1
    if s.cl == s.h:
        s.cl = 0
    HUlib_clearTextLine(s.l[s.cl])

    for i in range(s.h):
        s.l[i].needsupdate = 4


def HUlib_addMessageToSText(s: hu_stext_t, prefix, msg):
    HUlib_addLineToSText(s)
    if prefix:
        for char in prefix:
            HUlib_addCharToTextLine(s.l[s.cl], char)

    if msg:
        for char in msg:
            HUlib_addCharToTextLine(s.l[s.cl], char)


def HUlib_drawSText(s: hu_stext_t):
    if not s.on[0]:
        return

    for i in range(s.h):
        idx = s.cl - i
        if idx < 0:
            idx += s.h
        
        l = s.l[idx]
        HUlib_drawTextLine(l, False)


def HUlib_eraseSText(s: hu_stext_t):
    for i in range(s.h):
        if s.laston and not s.on[0]:
            s.l[i].needsupdate = 4
        HUlib_eraseTextLine(s.l[i])
    s.laston = s.on[0]


def HUlib_initIText(it: hu_itext_t, x, y, font, startchar, on):
    it.lm = 0
    it.on = on
    it.laston = True
    HUlib_initTextLine(it.l, x, y, font, startchar)


def HUlib_delCharFromIText(it: hu_itext_t):
    if it.l.len != it.lm:
        HUlib_delCharFromTextLine(it.l)


def HUlib_eraseLineFromIText(it: hu_itext_t):
    while it.lm != it.l.len:
        HUlib_delCharFromTextLine(it.l)


def HUlib_resetIText(it: hu_itext_t):
    it.lm = 0
    HUlib_clearTextLine(it.l)


def HUlib_addPrefixToIText(it: hu_itext_t, str_prefix):
    for char in str_prefix:
        HUlib_addCharToTextLine(it.l, char)
    it.lm = it.l.len


def HUlib_keyInIText(it: hu_itext_t, ch) -> bool:
    if isinstance(ch, int):
        c_val = ch
    else:
        c_val = ord(ch)
        
    c_upper = ord(chr(c_val).upper()) if c_val < 128 else c_val

    if ord(' ') <= c_upper <= ord('_'):
        HUlib_addCharToTextLine(it.l, chr(c_upper))
    elif c_upper == KEY_BACKSPACE:
        HUlib_delCharFromIText(it)
    elif c_upper != KEY_ENTER:
        return False

    return True


def HUlib_drawIText(it: hu_itext_t):
    if not it.on[0]:
        return
    HUlib_drawTextLine(it.l, True)


def HUlib_eraseIText(it: hu_itext_t):
    if it.laston and not it.on[0]:
        it.l.needsupdate = 4
    HUlib_eraseTextLine(it.l)
    it.laston = it.on[0]
