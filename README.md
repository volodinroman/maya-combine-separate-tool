# maya_combineSeparate

A Python module for Autodesk Maya that provides a method to separate a combined object back into its original components (containing two or more shells) while preserving skinning applied to the combined object.

It utilizes standard Python libraries along with `maya.cmds`, `maya.mel`, `maya.OpenMaya`, and `maya.OpenMayaAnim`.

## How It Works

1. **Select Objects** – Choose the objects that need to be combined and create an instance of the `objectCombine` class, which gathers all necessary data from the original objects.

2. **Combine Objects** – The module runs a MEL script with a custom combine function to merge the selected objects.

3. **Apply Skinning** – After combining, create a joint system and assign a skin deformer to the combined object using these joints.

4. **Separate & Restore Skinning** – Execute methods to collect skinCluster data from the combined object, separate it back into the original meshes, and restore skinning weights by creating new skinClusters for each separated mesh.

## Usage

1. Unzip the project into your Maya Python path folder.

2. Import the script:
   ```python
   import combineSeparate.main as combSep
   ```

3. Select the objects you want to combine. The first selected object will act as the base.

4. Create an instance of the `objectCombine` class and run the combine operation:
   ```python
   instance = combSep.objectCombine()  # Collects necessary data for combining and separating
   instance.doCombine()  # Executes the combine function
   ```

5. Create a joint system and assign a skin deformer to the combined mesh, ensuring the joints are set as influence objects.

6. Restore original meshes and skinning:
   ```python
   instance.doCollectSkinData_deleteSkin()  # Collects skinning data from the combined object
   instance.doSeparate()  # Separates the object into its original parts
   instance.doRecreateSkinning()  # Recreates skinning for the separated objects
   ```

