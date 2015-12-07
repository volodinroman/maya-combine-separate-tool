#attach surveying device to a mesh
import maya.cmds as cmds
import maya.mel as mel
import os
dir = str(os.path.dirname(__file__))

def options():
	print 

def runFlattenCombine():
    cmds.undoInfo(ock=1)
    scriptFile = open(dir+"/flattenCombineDontMerge.mel", 'r')
    scriptIn =  scriptFile.read()
    out = mel.eval(scriptIn)
    cmds.undoInfo(cck=1)

    return out