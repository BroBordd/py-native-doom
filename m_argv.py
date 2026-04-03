import sys

myargv = sys.argv[:]

def M_CheckParm(parm):
    try:
        return myargv.index(parm)
    except ValueError:
        return 0

def M_CheckParmWithArgs(parm, num_args):
    try:
        i = myargv.index(parm)
        if i + num_args < len(myargv):
            return i
    except ValueError:
        pass
    return 0

def M_ParmExists(parm):
    return parm in myargv
