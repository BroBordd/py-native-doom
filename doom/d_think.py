# d_think.py
# Thinker (actor) doubly-linked list infrastructure
# Ported from d_think.h

# In C, thinkers are a doubly-linked list threaded through all active
# map objects.  In Python we keep the same structure so the rest of the
# game logic translates 1:1, but use plain object references instead of
# raw pointers.

class Thinker:
    """
    Base class for every active object in the game world (mobjs, ceilings,
    doors, floors, …).  Mirrors thinker_t from d_think.h.

    'function' is a callable(thinker) or None.  Setting it to None is the
    Python equivalent of setting thinker.function.acv = (actionf_v)1 which
    signals "remove me from the thinker list next tic".
    """
    __slots__ = ('prev', 'next', 'function')

    def __init__(self):
        self.prev: 'Thinker | None' = None
        self.next: 'Thinker | None' = None
        self.function = None   # callable(thinker) | None

    def mark_removed(self):
        """Signal this thinker for removal (equiv. to setting acv = 1)."""
        self.function = _REMOVED_SENTINEL

# Sentinel callable used to flag removal (matches C's ((actionf_v)1) trick)
def _REMOVED_SENTINEL(_t):
    pass

_REMOVED_SENTINEL._is_removed = True

def thinker_is_removed(t: Thinker) -> bool:
    return getattr(t.function, '_is_removed', False)


class ThinkerList:
    """
    The global doubly-linked thinker list.
    Head/tail sentinel node; actual thinkers sit between them.
    Mirrors the 'thinkercap' pattern from p_tick.c.
    """
    def __init__(self):
        self._cap = Thinker()          # sentinel head/tail
        self._cap.prev = self._cap
        self._cap.next = self._cap

    def add(self, thinker: Thinker):
        """Add thinker at end of list (before cap)."""
        cap = self._cap
        thinker.next = cap
        thinker.prev = cap.prev
        cap.prev.next = thinker
        cap.prev = thinker

    def run(self):
        """
        Run all thinkers for one game tic.
        Thinkers that mark themselves removed are unlinked here.
        """
        cap = self._cap
        current = cap.next
        while current is not cap:
            nxt = current.next
            if thinker_is_removed(current):
                # unlink
                current.prev.next = current.next
                current.next.prev = current.prev
            elif current.function is not None:
                current.function(current)
            current = nxt

    def __iter__(self):
        cap = self._cap
        t = cap.next
        while t is not cap:
            yield t
            t = t.next


# Module-level singleton, matches C's global thinkercap
thinkercap = ThinkerList()
