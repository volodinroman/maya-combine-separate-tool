"""
combineSeparate.py 2015
Vendor: Roman Volodin
website: http://romanvolodin.com
e-mail: contact@romanvolodin.com

"""

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.mel as mel
from combineSeparate.tools.duplicateSeparate_launch import *
from combineSeparate.tools.flattenCombineDontMerge_launch import *


"""
combine 
separate back to original parts
preserve skinning
"""

class fnSkinCluster():
    def __init__(self):
        print "skinProcessor initialized"

    @classmethod
    def getShape(cls, node, intermediate=False):
        """
            Gets the shape from the specified node.
            @param[in] node Name of a transform or shape node.
            @param[in] intermediate True to get the intermediate shape, False to get the visible shape.
            @return The name of the desired shape node
        """
        if cmds.nodeType(node) == 'transform':
            shapes = cmds.listRelatives(node, shapes=True, path=True)
            if not shapes:
                shapes = []
            for shape in shapes:
                isIntermediate = cmds.getAttr('%s.intermediateObject' % shape)
                if intermediate and isIntermediate and cmds.listConnections(shape, source=False):
                    return shape
                elif not intermediate and not isIntermediate:
                    return shape
            if shapes:
                return shapes[0]
        elif cmds.nodeType(node) in ['mesh', 'nurbsCurve', 'nurbsSurface']:
            return node
        return None 

    @classmethod
    def getSkinCluster(cls, shape):
        """
            Get the skinCluster node attached to the specified shape.
            @param[in] shape Shape node name
            @return The attached skinCluster name or None if no skinCluster is attached.
        """
        shape = cls.getShape(shape)
        history = cmds.listHistory(shape, pruneDagObjects=True, il=2)
        if not history:
            return None
        skins = [x for x in history if cmds.nodeType(x) == 'skinCluster']
        if skins:
            return skins[0]
        return None

    @classmethod
    def getSkinClusterSet(cls, skinCluster):
        """ get skinClusterSet for a passed in skinCluster
            @param[in] skinCLuster: name of skinCluster
            @type skinCluster: string
        """
        deformerSet = cmds.connectionInfo(skinCluster + ".message", dfs=1)[0]
        deformerSet = deformerSet.split(".")[0]
        return deformerSet

    @classmethod
    def getSkinClusterJoints(cls, skinCluster):
        """
            Get list of joints connected with the skinCluster
            @param[in] skinCluster: name of skinCluster
            @type skinCluster: string
            @returns: list of joints (fullname)
        """
        output = []
        matrixAttrLen =  cmds.getAttr(skinCluster + ".matrix", s=1) #get len of array attribute (matrix)

        for i in range(0, matrixAttrLen):
            jointAttr = cmds.ls(cmds.connectionInfo(skinCluster + ".matrix[" + str(i) + "]", sfd=1), l=1)[0]
            joint = jointAttr.split(".")[0]
            
            output.append(joint)

        return output

    @classmethod
    def getSkinClusterInfluences(cls, fnSC):
        """
            @param[in] fnSC: MFnSkinCluster pointer
            @return skin cluster influence objects := joints 
        """
        output = []
   
        influencePaths = OpenMaya.MDagPathArray()
        numInfluences = fnSC.influenceObjects(influencePaths)
        for i in range(influencePaths.length()):
            output.append(influencePaths[i].fullPathName())

        return output

    @classmethod
    def createMFnSkinCluster(cls, objectShape):
        """
            @param[in] objectShape: shape of a passed in object type string
            @return MFnSkinCluster  
        """
        selectionList = OpenMaya.MSelectionList()
        selectionList.add(objectShape)
        mobject = OpenMaya.MObject()
        selectionList.getDependNode(0, mobject)
        fnSC = OpenMayaAnim.MFnSkinCluster(mobject)

        return fnSC 

    @classmethod
    def getGeometryComponents(cls, fnSC):
        """
            @param[in] fnSC: MFnSkinCluster pointer
            @return components of an object which is connected with the fnSC skin cluster as MObject
        """
        # Get dagPath and member components of skinned shape
        fnSet = OpenMaya.MFnSet(fnSC.deformerSet())
        members = OpenMaya.MSelectionList()
        fnSet.getMembers(members, False)
        dagPath = OpenMaya.MDagPath()
        components = OpenMaya.MObject()
        members.getDagPath(0, dagPath, components)
        return dagPath, components

    @classmethod
    def getWeights(cls, fnSC, dagpath, components):
        """
            @param[in] fnSC: MFnSkinCluster pointer
            @param[in] dagpath: DagPath of an object for which skinWeights are gethering
            @param[in] components: MObject components pointer for the dagpath object
            @return list of weighs for each vertex per influence objec (joint)
        """
        weights = OpenMaya.MDoubleArray()
        util = OpenMaya.MScriptUtil()
        util.createFromInt(0)
        pUInt = util.asUintPtr()
        fnSC.getWeights(dagpath, components, weights, pUInt);
        return weights


class objectCombine():
    def __init__(self):

        self.origObjectList = cmds.ls(sl=1, l=1)  #orig objects list

        """
        @ORIGINAL MESHES DATA
            struct = [ [ object                        ] , [ object                         ] ]
                     [ [ shell,    shell,     shell]   ] , [ shell,     shell,      shell   ] ]
                           |         |           |             |          |           |
            Shells = [ [(f,f,f,f), (f,f,f,f), (f,f,f,f)] , [(f,f,f,f), (f,f,f,f), (f,f,f,f) ] ]   := faces per shell - aux list for getting bboxes
            Bboxes = [ [ bbox,     bbox,      bbox     ] , [ bbox,      bbox,      bbox     ] ]   := MBoundingBox
        """

        self.orig_shells = [] #original shells
        self.orig_bboxes = [] #original bounding boxes
        self.orig_names = [] #original names

        #initialization
        self.getOrigShellsData() #get shells data from original objects

        """
        @COMBINED MESH DATA
            Shells = [ (f,f,f,f), (f,f,f,f), (f,f,f,f), (f,f,f,f), (f,f,f,f), (f,f,f,f) ]   := faces per shell
            Bboxes = [ bbox,      bbox,      bbox,      bbox,      bbox,      bbox      ]   := MBoundingBox
        """

        self.tmp_combinedObject = None
        self.tmp_shells = [] #shells of combined object
        self.tmp_bboxes = [] #bounding boxes of these shells
        self.tmp_visited = [] #data for a graph computation
        self.tmp_sorted = [] #list of shell ids for restoring the original meshes

        """
        @SEPARATED MESHES DATA
        """
        self.separatedMeshes = []

        """
        @SKINNING DATA
        """
        self.jointList = [] #joint list got from cluster connections via MEL
        self.influenceList = [] #actual joint list got from combined object via OpenMaya

        self.separatedSkinClusters = [] #clusters name per each object

        self.combinedMPointList = [] #[ MPoint MPoint MPoint ...]
        self.separatedMPointList = [] #[ [MPoint MPoint MPoint ...] [MPoint MPoint MPoint ...] [...] ]
        
        self.combinedWeights = [] #[ w1, w2, w3, w4...] Float

    def comprehensionList(self, A,B):
        """
            @returns: comprehension of list A and list B
        """
        return list(set(A) - set(B))

    @classmethod
    def getComponentBBox(cls, components):
        """
            @param[in] components: faces that are used for computing their common bounding box
            @type components: list of faces
            @returns: MBoundingBox of the passed in components
        """
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

    def getShells(self, obj):
        """
            @param[in] obj: object full name 
            @type obj: string
            @returns: list of shells that is included in the passed in object in format [ [[obj.f[0], obj.f[1], obj.f[2]], [obj.f[3], obj.f[4], obj.f[5]], [another shell]], [another object]]
        """
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
        """
            @get original shells data
        """
        if self.origObjectList:
            for obj in self.origObjectList:
                shellsBBoxList = []
                self.orig_names.append(obj) #save name
                objectShells = self.getShells(obj)
                self.orig_shells.append(objectShells) #save shells

                shellBBox = []
                for shell in objectShells: # for i in current object shells
                    shellBBox.append(objectCombine.getComponentBBox(shell)) # append MBoundingBox
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


    def doCollectSkinData_deleteSkin(self):

        """first get the skin cluster from the combined object"""

        combinedObjectShape = fnSkinCluster.getShape(cmds.listRelatives(self.tmp_combinedObject, c=1, f=1)[0])
        combineSkinClusterName = fnSkinCluster.getSkinCluster(combinedObjectShape)
        combinedSkinClusterSet = fnSkinCluster.getSkinClusterSet(combineSkinClusterName)
        self.jointList = fnSkinCluster.getSkinClusterJoints(combineSkinClusterName) #returns list of joints  
        combinedIntermediateMesh = fnSkinCluster.getShape(self.tmp_combinedObject, True)

        """get MPoint data from the combined object to store vertex positions according ther indices"""

        selectionList = OpenMaya.MSelectionList()
        selectionList.clear()
        selectionList.add(self.tmp_combinedObject)
        dagPath = OpenMaya.MDagPath()
        selectionList.getDagPath(0, dagPath)
        iter = OpenMaya.MItMeshVertex(dagPath)
        while not iter.isDone():
            point = iter.position(OpenMaya.MSpace.kWorld)
            point.x = round(point.x, 6)
            point.y = round(point.y, 6)
            point.z = round(point.z, 6)
            self.combinedMPointList.append(point) 
            iter.next()


        """ #here we get data needed to restore skinning on separate objects """

        #skinCluster can deform only a single geometry, all gathering data through fnSkinCluster related to just one mesh
        combined_fnSkinCluster = fnSkinCluster.createMFnSkinCluster(combineSkinClusterName) # create MFnSkinCluster function set for the combied object
        combined_DagPath, combined_components = fnSkinCluster.getGeometryComponents(combined_fnSkinCluster) #get dagPath, components of the combined object for gathering skinClusterWeights
        combined_Weights_unsorted = fnSkinCluster.getWeights(combined_fnSkinCluster, combined_DagPath, combined_components) #get weights (see fnSkinCluster Doc)

        #get real list ofinfluences in the right order
        self.influenceList = fnSkinCluster.getSkinClusterInfluences(combined_fnSkinCluster)

        #sort jointWeights list as sublists of influences (self.influenceList) per vertex to get the same format as in ComponentEditor
        self.combinedWeights = [combined_Weights_unsorted[i:i+len(self.influenceList)] for i in range(0, len(combined_Weights_unsorted), len(self.influenceList))]

    
        """after collecting skinCluster data - delete skincluster and skinclusterSet"""
        cmds.delete(combineSkinClusterName)


        """delete intermediate shapeOrig nodes"""
        cmds.delete(self.tmp_combinedObject, ch=1)

        
        
    def doSeparate(self):

        """get shells of the combined mesh"""
        self.tmp_shells = self.getShells(self.tmp_combinedObject)

        """Get bounding boxes for these shells"""
        for shell in self.tmp_shells: # for i in current object shells
            self.tmp_bboxes.append(objectCombine.getComponentBBox(shell)) # append MBoundingBox

        """initialize visited units"""
        self.tmp_visited = [0] * len(self.tmp_bboxes)

        """initialize ids list"""
        self.tmp_sorted = [0] * len(self.tmp_bboxes) #indices of shells and bboxes according their objects L

        """Get combined object data"""
        for idx_i, i in enumerate(self.orig_bboxes): #for each orig object (bbox)
            for idx_j, j in enumerate(i): #for each bbox of orig object
                
                for idx_k, k in enumerate(self.tmp_bboxes): #combined bboxes
                    if not self.checkVisited(self.tmp_visited, idx_k): #if not visited
                        bbox = self.orig_bboxes[idx_i][idx_j] #orig bbox
                        #compare bboxes
                        if round(bbox.min().z, 5) == round(k.min().z, 5) and round(bbox.max().z, 5) == round(k.max().z, 5) and round(bbox.min().x, 5) == round(k.min().x, 5) and round(bbox.min().y, 5) == round(k.min().y, 5):
                            self.setVisited(self.tmp_visited, idx_k) # visited is 1  -do no check it in the future iterations
                            self.tmp_sorted[idx_k] = idx_i #combined bbox at idx_k set id index as idx_i (original list object index)
                            continue #stop iteration

   
        """separate   """                 
        for i in range(len(self.orig_shells)): # for i in 0...num objects L
            id = i  #id = current i
            faceList_toSeparate = []
            for idx_j, j in enumerate(self.tmp_sorted): #for each sorted_id for combined object
                if j == id: #0 1 2 3 4 5 6 7 8 9
                    faceList_toSeparate.extend(self.tmp_shells[idx_j])

            if faceList_toSeparate:
                object = self.mel_separate(faceList_toSeparate) #do separate
                name = self.orig_names[i].split("|")[-1]
                fullname = object[0][:-1 * len(object[0].split("|")[-1])] + name 
                fullname = cmds.rename(object[0], name)
                self.separatedMeshes.append(fullname) #save object's full name

        cmds.delete(self.tmp_combinedObject)

        """rename object that has the same as combineObject name but was renamed as name1         --------------TO DO"""

    def doRecreateSkinning(self):

        """
            @self.combinedMPointList - list of MPoints for vertices of the combined object
            @self.combinedWeights - list of sublists := weights for sublist[vertex] per each influence from self.influenceList

            @self.separatedMeshes - mesh list after separation
            @self.separatedSkinClusters - list of skinClusters names for self.separatedMeshes
            @self.separatedMPointList = List of sublists := MPoints for sublist[object] vertices

            @self.jointList - list of joints that took part in combined object skinning process 
            @self.influenceList - list of joints used as influence objects for combined skin cluster
        """

        """1 assign skin clusters to separated meshes"""
        for i in range(len(self.separatedMeshes)):
            separatedMesheShape = cmds.listRelatives(self.separatedMeshes[i], c=1, f=1, type="mesh")[0]
            sCluster = cmds.skinCluster(self.influenceList, separatedMesheShape, nw=2, prune = 1)[0] #tsb = to selected bones, nw = normalizeWeights interactive
            self.separatedSkinClusters.append(sCluster)


        """2 get separated objects vertices MPoint positions"""
        for i in self.separatedMeshes: #for each object in list
            objectVertPos = []

            selectionList = OpenMaya.MSelectionList()
            selectionList.clear()
            selectionList.add(i)

            dagPath = OpenMaya.MDagPath()
            selectionList.getDagPath(0, dagPath)
            iter = OpenMaya.MItMeshVertex(dagPath)
            while not iter.isDone():
                point = iter.position(OpenMaya.MSpace.kWorld)
                point.x = round(point.x, 6)
                point.y = round(point.y, 6)
                point.z = round(point.z, 6)
                objectVertPos.append(point) 
                iter.next()

            self.separatedMPointList.append(objectVertPos) #add object's mpoint list to global list [[...],[...],[...],[...],[...]]

        """ @recreating weights
            @we have: 
                Weight list for the combined object
                MPoint list for the combined object vertices
                influence list in the right order
        """

        combined_mpoint_visited = [0] * len(self.combinedMPointList)

        for idx, cluster in enumerate(self.separatedSkinClusters): #for each cluster
            
            #create MFnSkinCluster
            fnSC = fnSkinCluster.createMFnSkinCluster(cluster)
            
            #get object DagPath, all components 
            dagPath, components = fnSkinCluster.getGeometryComponents(fnSC)

            #influence indices
            influencePaths = OpenMaya.MDagPathArray()
            numInfluences = fnSC.influenceObjects(influencePaths)
            influenceIndices = OpenMaya.MIntArray(numInfluences)
            for i in range(numInfluences):
                influenceIndices.set(i, i)


            #list of weights for all vertices for the current object
            weights = fnSkinCluster.getWeights(fnSC, dagPath, components) #get unsorted but ordered list of weights
            idx_W = 0
            for idx_point, mpoint in enumerate(self.separatedMPointList[idx]): #for each mpoint in separated object

                for idx_cPoint, cpoint in enumerate(self.combinedMPointList): #for all mpoints in combined object

                    if combined_mpoint_visited[idx_cPoint] == 0: #check visited to prevent extra computations
                        if mpoint.x == cpoint.x and mpoint.y == cpoint.y and mpoint.z == cpoint.z:

                            #set visited
                            combined_mpoint_visited[idx_cPoint] = 1

                            #coordinates match
                            combined_vtx_weightList = self.combinedWeights[idx_cPoint] #for each self.influenceList

                            #update weight list
                            for i in combined_vtx_weightList:
                                weights.set(i, idx_W)
                                idx_W += 1

                            continue



            #set the weight for the current object
            fnSC.setWeights(dagPath, components, influenceIndices, weights, True) #normalize = True




def runTest():
    # 1) select objects You want to combine. They will be combined to the first selected object

    # 2) 
    instance = combSep.objectCombine()  #collects all data needed for combining and separating 
    instance.doCombine() #run combine

    # 3) Create joint system and assign skin deformer to the combined mesh where these joints are influence objects

    # 4) Back to subtools
    instance.doCollectSkinData_deleteSkin() #gather all data needed for restoring skinning from the combined object
    instance.doSeparate() #separate object into parts
    instance.doRecreateSkinning() #recreate skinning for separated objects


