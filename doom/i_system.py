import sys

screensaver_mode = False
_exit_funcs = []

def I_Error(msg, *args):
    print(f"I_Error: {msg % args if args else msg}", file=sys.stderr)
    sys.exit(1)

def I_Quit():
    for fn, run_on_error in reversed(_exit_funcs):
        try:
            fn()
        except Exception:
            pass
    sys.exit(0)

def I_AtExit(func, run_on_error=False):
    _exit_funcs.append((func, run_on_error))

def I_PrintBanner(msg):
    print(msg)

def I_DisplayFPSDots(enable):
    pass

def I_Endoom(endoom):
    pass

def I_GetTime():
    import i_timer
    return i_timer.I_GetTime()

def I_PrintStartupBanner(msg):
    print(msg)

def I_CheckIsScreensaver():
    return False
