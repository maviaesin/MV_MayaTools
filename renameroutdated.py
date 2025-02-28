from maya import cmds

# Lets retrieve selected objects from the scene. If an object is selected, selection keeps its name. pCube1.
# If nothing is selected, using dag to retrieve all items in object hierarchy, use long to retrieve path names.
# selection sort sorts all items from the selection list by string length.

SUFFIXES = {
    "mesh" : "geo",
    "joint" : "jnt",
    "camera" : None,
    "ambientLight" : "aLgt"
}

DEFAULT_SUFFIX = 'grp'

def rename(selection = False):
    """
    This function will rename any objects to have the correct suffix.
    Args:
        selection: Whether or not we use the current selection

    Returns:
        A list of all objects we operated on.
    """
    objects = cmds.ls(selection=True)

    if selection and not objects:
        raise RuntimeError ("You don't have anything selected.")


    if len(objects) == 0:

        objects = cmds.ls(dag=True, type='transform')

    # objects.sort(key = len, reverse= True)
    # print(objects)


    for obj in objects:
        # Extracts the short name of each selected object.
        shortName = (obj.split("|")[-1])

        # see that if the object has a child. return full path of children or if no children return empty list.

        children = cmds.listRelatives(obj, children=True) or []

        # If the object has exactly one child, get that child's type.
        if children and len(children) == 1:
            child = children[0]
            objType = cmds.objectType(child)

        # Otherwise, get the parent object's type:
        else:
            objType = cmds.objectType(obj)

        # #adding suffixes
        # if objType == "mesh":
        #     suffix = "geo"
        # elif objType == "joint":
        #     suffix = "jnt"
        # elif objType == "camera":
        #     print("Skipping camera")
        #     continue
        # else:
        #     suffix = "grp"

        suffix = SUFFIXES.get(objType, DEFAULT_SUFFIX)

        if not suffix:
            continue

        if obj.endswith('_' + suffix):
            continue


        #newName = shortName + "_" + suffix

        newName = "%s_%s" % (shortName, suffix)

        index = objects.index(obj)

        objects[index] = obj.replace(shortName, newName)
        cmds.rename(obj, newName)
        print(newName)
        print(objects)