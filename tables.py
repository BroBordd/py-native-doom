# tables.py
# Precomputed trigonometry tables used throughout the renderer.
# In the original source these came from tables.c (a generated file).
# We regenerate them at import time using Python's math module.
# All values are fixed-point (16.16) matching the C originals exactly.

import math

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
FINEANGLES      = 8192          # fine angle resolution
FINEMASK        = FINEANGLES - 1
ANGLETOFINESHIFT = 19           # BAM >> 19 → fine index
FRACBITS        = 16
FRACUNIT        = 1 << FRACBITS

SLOPERANGE      = 2048
SLOPEBITS       = 11
DBITS           = FRACBITS - SLOPEBITS   # = 5

# Binary-angle constants (re-exported for callers)
ANG45  = 0x20000000
ANG90  = 0x40000000
ANG180 = 0x80000000
ANG270 = 0xC0000000

# ------------------------------------------------------------------
# finesine[0 .. 5*FINEANGLES/4-1]
# finesine[i] = sin(i * 2π / FINEANGLES) in fixed-point
# The table is extended to 5/4 of a full circle so that
# finecosine can simply point 1/4 circle ahead.
# ------------------------------------------------------------------
_FINE_N = FINEANGLES * 5 // 4   # 10240 entries

finesine: list = [0] * _FINE_N

for _i in range(_FINE_N):
    _a = (_i + 0.5) * 2.0 * math.pi / FINEANGLES
    finesine[_i] = int(math.sin(_a) * FRACUNIT)

# finecosine is a view into finesine offset by FINEANGLES/4
# (cos θ = sin(θ + 90°))
# We materialise it as a separate list for speed (avoids modular index)
finecosine: list = finesine[FINEANGLES // 4: FINEANGLES // 4 + FINEANGLES]
# Pad to FINEANGLES length (it already is, just make sure)
assert len(finecosine) == FINEANGLES

# ------------------------------------------------------------------
# finetangent[0 .. FINEANGLES/2-1]
# finetangent[i] = tan((i - FINEANGLES/4 + 0.5) * 2π / FINEANGLES)
# Values beyond ±2*FRACUNIT are clamped by the renderer anyway.
# ------------------------------------------------------------------
finetangent: list = [0] * (FINEANGLES // 2)

for _i in range(FINEANGLES // 2):
    _a = (_i - FINEANGLES // 4 + 0.5) * 2.0 * math.pi / FINEANGLES
    _t = math.tan(_a) * FRACUNIT
    # clamp to int32 range
    if _t > 0x7FFFFFFF:  _t = 0x7FFFFFFF
    elif _t < -0x80000000: _t = -0x80000000
    finetangent[_i] = int(_t)

# ------------------------------------------------------------------
# tantoangle[0 .. SLOPERANGE]
# Inverse-tangent lookup: slope (y/x in fixed, scaled to SLOPERANGE)
# → BAM angle in [0, ANG90).
# Used by R_PointToAngle octant folding.
# ------------------------------------------------------------------
tantoangle: list = [0] * (SLOPERANGE + 1)

for _i in range(SLOPERANGE + 1):
    _f = math.atan(_i / SLOPERANGE) / (2.0 * math.pi)
    # 32-bit unsigned wrap
    tantoangle[_i] = int(0xFFFFFFFF * _f) & 0xFFFFFFFF

# ------------------------------------------------------------------
# SlopeDiv — fast unsigned slope for R_PointToAngle
# Returns index into tantoangle (0..SLOPERANGE).
# ------------------------------------------------------------------
def SlopeDiv(num: int, den: int) -> int:
    """
    Compute min(num * SLOPERANGE / den, SLOPERANGE).
    Both num and den are unsigned (non-negative).
    """
    if den < 512:
        return SLOPERANGE
    ans = (num << SLOPEBITS) // den
    return min(ans, SLOPERANGE)

# ------------------------------------------------------------------
# Cleanup temp loop vars
# ------------------------------------------------------------------
del _i, _a, _t, _f
