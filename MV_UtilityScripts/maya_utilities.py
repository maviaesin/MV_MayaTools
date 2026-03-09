import maya.cmds as cmds


def get_user_object_selection(selection=False):
    """
    Retrieves the DAG objects selected by the user.

    Returns:
        selected_object_list (list): List of selected DAG objects.

    Raises:
        RuntimeError: If no object is selected.
    """
    # TODO: 1- Add an argument `include_materials=True`, so it includes materials in selection if set to True.
    # TODO: 2- Add a flag `include_references=False`. If True, excludes referenced objects from `selected_object_list` (for other scripts).

    selected_object_list = cmds.ls(selection=True, dag=True)

    # If no object is selected, raise an error
    if not selected_object_list:
        raise RuntimeError("You don't have anything selected.")

    return selected_object_list


def check_object_is_mesh(obj) -> bool:
    """
    Checks if the given object is a mesh.

    Args:
        obj (str): The name of the object.

    Returns:
        bool: True if the object is a mesh, otherwise False.
    """
    has_shape = False
    relatives = cmds.listRelatives(obj, shapes=True, fullPath=True) or []

    for shape in relatives:
        if cmds.objectType(shape) == "mesh":
            has_shape = True

    return has_shape


def check_object_is_skeletal_mesh(obj) -> bool:
    """
    Determines if the given object is a skeletal mesh by checking for a skinCluster.

    Args:
        obj (str): The name of the object.

    Returns:
        bool: True if the object is a skeletal mesh, otherwise False.
    """
    has_skin_cluster = False
    relatives = cmds.listRelatives(obj, shapes=True, fullPath=True) or []

    ### CHECK IF OBJECT IS A MESH ###
    if check_object_is_mesh(obj):
        ### CHECK IF A SKINCLUSTER EXISTS IN THE HISTORY ###
        for shape in relatives:
            history = cmds.listHistory(shape, pruneDagObjects=True) or []
            skin_clusters = cmds.ls(history, type="skinCluster")
            if skin_clusters:
                has_skin_cluster = True

    return has_skin_cluster
