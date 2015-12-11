# maya_combineSeparate

A python module for Autodesk Maya that shows a way to separate a combined object back to original ones (contained 2 or more shells) preserving skinning that was applied to the combined object.

It uses standart python libraries, maya.cmds, maya.mel, maya.OpenMaya and maya.OpenMayaAnim

####How it works:

- First step is to select objects that need to be combined and create an instance of objectCombine class that gathers all data from the original objects.

- Next step is combining method that runs a mel script with a custom combine function.
 
- After combining a user need to create a joint system and assign a skin deformer to the combined object using these joints. 

- Last step is to run methods that collect data from skinCluster assigned to the combined object, separate this object back to original meshes and recreates all the skinning weights in a newly created skinClusters for each separated mesh.
 
 
####Using:

Unzip the project to your Maya Python path folder

Import the script
```
import combineSeparate.main as combSep
```
Select objects You want to combine. They will be combined to the first selected object

Create an instance of objectCombine class and run combine
```
instance = combSep.objectCombine()  *#collects all data needed for combining and separating*
instance.doCombine() *#run combine*
```

Create joint system and assign skin deformer to the combined mesh where these joints are influence objects

Back to original meshes
```
instance.doCollectSkinData_deleteSkin() *#gather all data needed for restoring skinning from the combined object*
instance.doSeparate() *#separate object into parts*
instance.doRecreateSkinning() *#recreate skinning for separated objects*
```

