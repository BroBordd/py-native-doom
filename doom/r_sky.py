# r_sky.py
#
# DESCRIPTION:
#  Sky rendering. The DOOM sky is a texture map like any
#  wall, wrapping around. A 1024 columns equal 360 degrees.
#  The default sky map is 256 columns and repeats 4 times
#  on a 320 screen?

# --- Constants from r_sky.h ---

# SKY, store the number for name.
SKYFLATNAME = "F_SKY1"

# The sky map is 256*128*4 maps.
ANGLETOSKYSHIFT = 22


# --- Global Variables from r_sky.c / r_sky.h ---

skyflatnum = 0
skytexture = 0
skytexturemid = 0


# --- Functions ---

def R_InitSkyMap():
    """
    Called whenever the view size changes.
    """
    global skytexturemid
    
    # Import locally to avoid circular dependencies during engine boot
    from doomdef import SCREENHEIGHT, FRACUNIT
    
    # In the provided C source, this line was commented out:
    # skyflatnum = R_FlatNumForName ( SKYFLATNAME )
    
    # Python uses integer division // to match C's integer math behavior
    skytexturemid = (SCREENHEIGHT // 2) * FRACUNIT
