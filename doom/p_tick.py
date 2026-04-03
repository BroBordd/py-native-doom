import p_ceilng
import p_floor
# p_tick.py
# Thinker list management + P_Ticker (main game tic)
# Ported from p_tick.c / p_tick.h

# In our Python port the thinker list lives in d_think.thinkercap.
# We expose the same API names the C code used so every other module
# can call p_tick.P_AddThinker, p_tick.P_RemoveThinker, P_InitThinkers without
# caring that the implementation is different.

from d_think import thinkercap, thinker_is_removed, Thinker

# ------------------------------------------------------------------
# P_InitThinkers  — reset the list (called at level start)
# ------------------------------------------------------------------
def P_InitThinkers():
    thinkercap.__init__()


# ------------------------------------------------------------------
# p_tick.P_AddThinker
# ------------------------------------------------------------------
def P_AddThinker(thinker: Thinker):
    thinkercap.add(thinker)


# ------------------------------------------------------------------
# p_tick.P_RemoveThinker  — lazy removal (mark, unlink on next run)
# ------------------------------------------------------------------
def P_RemoveThinker(thinker: Thinker):
    thinker.mark_removed()


# ------------------------------------------------------------------
# P_RunThinkers
# ------------------------------------------------------------------
def P_RunThinkers():
    thinkercap.run()


# ------------------------------------------------------------------
# P_Ticker  — called once per game tic
# ------------------------------------------------------------------
def P_Ticker():
    import doomstat

    if doomstat.paused:
        return

    # Menu pause (single-player only, once at least one tic has run)
    if (not doomstat.netgame and
            doomstat.menuactive and
            not doomstat.demoplayback):
        p = doomstat.players[doomstat.consoleplayer]
        if p and p.viewz != 1:
            return

    # Run player thinking
    from p_user import P_PlayerThink
    for i in range(doomstat.MAXPLAYERS if hasattr(doomstat, 'MAXPLAYERS') else 4):
        if doomstat.playeringame[i]:
            p = doomstat.players[i]
            if p:
                P_PlayerThink(p)

    P_RunThinkers()

    # Sector specials / texture anims / button timers
    try:
        import p_spec
        p_spec.P_UpdateSpecials()
    except (ImportError, AttributeError):
        pass

    # Item respawn queue (deathmatch alt-death)
    try:
        from p_mobj import P_RespawnSpecials
        P_RespawnSpecials()
    except (ImportError, AttributeError):
        pass

    doomstat.leveltime += 1
