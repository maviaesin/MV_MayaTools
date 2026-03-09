#from prefix_constants import PREFIXES
import maya.cmds as cmds


def get_user_object_selection(selection=False):
    """
    Creates a `selected_object_list`, which contains the dag objects selected by the user.
    Returns: selected_object_list
    """
    # TODO: 1- Create an argument.default is include_materials = True, and if its true it will include the to self.selection list
    # TODO: 2- Add a flag include_references. Default'u false. If its a referenced object, exlude it in selected_object_list. (for other scripts)

    selected_object_list = cmds.ls(selection=True, dag = True)


    # If no object is selected, throw error
    if len(selected_object_list) == 0:
        raise RuntimeError("You don't have anything selected.")

    return selected_object_list


def check_object_is_mesh(obj) -> bool:
    has_shape = False
    relatives = cmds.listRelatives(obj, shapes=True, fullPath= True) or []

    for shape in relatives:
        if cmds.objectType(shape) == "mesh":
            has_shape = True

    return has_shape

def check_object_is_skeletal_mesh(obj) -> bool:
    has_skin_cluster = False

    relatives = cmds.listRelatives(obj, shapes=True, fullPath= True)
    ##Check if object is a mesh.

    if check_object_is_mesh(obj):
        #Find history nodes affecting the shape
        for shape in relatives:
            history = cmds.listHistory(shape, pruneDagObjects=True) or []
            skin_clusters = cmds.ls(history, type="skinCluster")
            if skin_clusters:
                has_skin_cluster = True

    return has_skin_cluster


def clear_list(list_name):
    """
    Removes all items from a list.
    Args:
        list_name: The list to be cleared.
    Returns: None
    """
    list_name.clear()
