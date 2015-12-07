"""
combineSeparate.py 2015
Vendor: Roman Volodin
website: http://romanvolodin.com
e-mail: contact@romanvolodin.com

"""

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.mel as mel
from combineSeparate.tools.duplicateSeparate_launch import *
from combineSeparate.tools.flattenCombineDontMerge_launch import *


"""
combine 
separate back to original parts
"""

class objectCombine():
    def __init__(self):

        self.origObjectList = cmds.ls(sl=1, l=1)  #orig objects list

        #ORIGINAL MESHES DATA

        #struct = [ [ object                        ] , [ object                         ] ]
        #         [ [ shell,    shell,     shell]   ] , [ shell,     shell,      shell   ] ]
        #               |         |           |             |          |           |
        #Shells = [ [(f,f,f,f), (f,f,f,f), (f,f,f,f)] , [(f,f,f,f), (f,f,f,f), (f,f,f,f) ] ]   := faces per shell - aux list for getting bboxes
        #Bboxes = [ [ bbox,     bbox,      bbox     ] , [ bbox,      bbox,      bbox     ] ]   := MBoundingBox

        self.orig_shells = [] #original shells
        self.orig_bboxes = [] #original bounding boxes
        self.orig_names = [] #original names

        #initialization
        self.getOrigShellsData() #get shells data from original objects


        #COMBINED MESH DATA

        #Shells = [ (f,f,f,f), (f,f,f,f), (f,f,f,f), (f,f,f,f), (f,f,f,f), (f,f,f,f) ]   := faces per shell
        #Bboxes = [ bbox,      bbox,      bbox,      bbox,      bbox,      bbox      ]   := MBoundingBox

        self.tmp_combinedObject = None
        self.tmp_shells = [] #shells of combined object
        self.tmp_bboxes = [] #bounding boxes of these shells
        self.tmp_visited = [] #data for a graph computation
        self.tmp_sorted = [] #list of shell ids for restoring the original meshes


    def comprehensionList(self, A,B):

        return list(set(A) - set(B))

    #get a MBoundingBox of passed in components
    def getComponentBBox(self, components):
        cmds.select(components)

        objectList = OpenMaya.MSelectionList()
        objectList.clear()

        OpenMaya.MGlobal.getActiveSelectionList(objectList) #get active selection list 

        dagPath = OpenMaya.MDagPath()
        component = OpenMaya.MObject()

        objectList.getDagPath(0, dagPath, component)

        iter = OpenMaya.MItMeshPolygon(dagPath, component)

        bbox = OpenMaya.MBoundingBox()
        while not iter.isDone():
            pointArray = OpenMaya.MPointArray()
            iter.getPoints(pointArray, OpenMaya.MSpace.kWorld)

            for i in range(0, pointArray.length()):
                bbox.expand(OpenMaya.MPoint(pointArray[i].x, pointArray[i].y, pointArray[i].z))

            iter.next()


        return bbox

    # return a list of shells of a passed in object
    def getShells(self, obj):
        output = []

        #total data
        numOfShells = cmds.polyEvaluate(obj, s=1) 

        faceList = cmds.ls(cmds.polyListComponentConversion( obj, tf=True), l=1, fl=1)

        for i in range(numOfShells):
            # cmds.select(obj)
            idx = int(faceList[0].split(".f[")[-1].split("]")[0])
            shellFaces = cmds.polySelect(obj, q=1, ets=idx)
            
            shellFacesFormat = [] #obj.f[0], obj.f[1] ...
            if shellFaces:
                for j in shellFaces:
                    __faceData = obj + ".f[" + str(j) + "]"
                    shellFacesFormat.append(__faceData)

            faceList = self.comprehensionList(faceList, shellFacesFormat)

            output.append(shellFacesFormat)

        return output 

    def getOrigShellsData(self):
        #get orig shells and bboxes
        if self.origObjectList:
            for obj in self.origObjectList:
                shellsBBoxList = []
                self.orig_names.append(obj) #save name
                objectShells = self.getShells(obj)
                self.orig_shells.append(objectShells) #save shells

                shellBBox = []
                for shell in objectShells: # for i in current object shells
                    shellBBox.append(self.getComponentBBox(shell)) # append MBoundingBox
                self.orig_bboxes.append(shellBBox)

    def doCombine(self):
        cmds.select(self.origObjectList)
        self.tmp_combinedObject = runFlattenCombine()

    def mel_separate(self, flist):
        cmds.select(d=1)
        cmds.select(flist)
        result = runDuplicateSeparate()
        return result

    def setVisited(self, __list, i):

        __list[i] = 1

    def checkVisited(self, __list, i):
        if __list[i] == 1:
            return True
        else:
            return False

    def doSeparate(self):

        # get shells of the combined mesh
        self.tmp_shells = self.getShells(self.tmp_combinedObject)

        #Get bounding boxes for these shells
        for shell in self.tmp_shells: # for i in current object shells
            self.tmp_bboxes.append(self.getComponentBBox(shell)) # append MBoundingBox

        #initialize visited units
        self.tmp_visited = [0] * len(self.tmp_bboxes)

        #initialize ids list
        self.tmp_sorted = [0] * len(self.tmp_bboxes) #indices of shells and bboxes according their objects L

        #Get combined object data
        for idx_i, i in enumerate(self.orig_bboxes): #for each orig object (bbox)
            for idx_j, j in enumerate(i): #for each bbox of orig object
                
                for idx_k, k in enumerate(self.tmp_bboxes): #combined bboxes
                    if not self.checkVisited(self.tmp_visited, idx_k): #if not visited
                        bbox = self.orig_bboxes[idx_i][idx_j] #orig bbox
                        #compare bboxes
                        if round(bbox.min().z, 5) == round(k.min().z, 5) and round(bbox.max().z, 5) == round(k.max().z, 5) and round(bbox.min().x, 5) == round(k.min().x, 5):
                            self.setVisited(self.tmp_visited, idx_k) # visited is 1  -do no check it in the future iterations
                            self.tmp_sorted[idx_k] = idx_i #combined bbox at idx_k set id index as idx_i (original list object index)
                            continue #stop iteration

   
        #separate                    
        for i in range(len(self.orig_shells)): # for i in 0...num objects L
            id = i  #id = current i
            faceList_toSeparate = []
            for idx_j, j in enumerate(self.tmp_sorted): #for each sorted_id for combined object
                if j == id: #0 1 2 3 4 5 6 7 8 9
                    faceList_toSeparate.extend(self.tmp_shells[idx_j])

            if faceList_toSeparate:
                object = self.mel_separate(faceList_toSeparate) #do separate
                name = self.orig_names[i].split("|")[-1]
                cmds.rename(object, name)

        cmds.delete(self.tmp_combinedObject)



def runTest():

    instance = objectCombine() #create an instance of the class

    instance.doCombine()

    instance.doSeparate()


