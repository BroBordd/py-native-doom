import sys
import time

# --- 1. System/Hardware Stubs ---
# Doom relies on these standard C files being present.
# We inject them into sys.modules so d_main and others can import them normally.

# Mock m_argv (Command Line Arguments)
class MockArgv:
    @staticmethod
    def M_CheckParmWithArgs(parm, num_args):
        import sys
        if parm in sys.argv and sys.argv.index(parm) + num_args < len(sys.argv):
            return sys.argv.index(parm)
        return 0

    @staticmethod
    def M_CheckParm(parm):
        import sys
        return sys.argv.index(parm) if parm in sys.argv else 0

    myargv = sys.argv
    myargc = len(sys.argv)

    @staticmethod
    def M_CheckParm(check):
        for i in range(1, MockArgv.myargc):
            if MockArgv.myargv[i].casefold() == check.casefold():
                return i
        return 0
    
    @staticmethod
    def M_ParmExists(check):
        return MockArgv.M_CheckParm(check) > 0

# Mock i_system (System Timer & Init)
class MockSystem:
    @staticmethod
    def I_DisplayFPSDots(*args, **kwargs):
        pass

    @staticmethod
    def I_PrintBanner(msg, *args, **kwargs):
        print("====", msg, "====")

    @staticmethod
    def I_AtExit(*args, **kwargs):
        pass

    # Doom ticks 35 times a second
    start_time = time.time()

    @staticmethod
    def I_GetTime():
        # Return time elapsed in Doom tics (1 tic = 1/35th of a second)
        return int((time.time() - MockSystem.start_time) * 35.0)

    @staticmethod
    def I_Init():
        pass
        
    @staticmethod
    def I_Quit():
        print("Engine gracefully exited.")
        sys.exit(0)

    @staticmethod
    def I_Error(error_string):
        print(f"FATAL ERROR: {error_string}")
        sys.exit(1)

# Inject our mocks into the Python module system
sys.modules['m_argv'] = MockArgv
sys.modules['i_system'] = MockSystem


# --- 2. Start the Engine ---
if __name__ == "__main__":
    try:
        import d_main
        
        print("=== BOOTING PYTHON DOOM ===")
        # Call the legendary entry point
        d_main.D_DoomMain()
        
    except Exception as e:
        import traceback
        print("\n=== CRASH LOG ===")
        traceback.print_exc()
