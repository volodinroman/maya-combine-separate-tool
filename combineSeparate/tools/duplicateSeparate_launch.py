#attach surveying device to a mesh
import maya.cmds as cmds
import maya.mel as mel
import os
dir = str(os.path.dirname(__file__))

def options():
	print 

def runDuplicateSeparate():
    cmds.undoInfo(ock=1)
    scriptFile = open(dir+"/duplicateSeparate.mel", 'r')
    scriptIn =  scriptFile.read()
    result = mel.eval(scriptIn)
    cmds.undoInfo(cck=1)

    return result