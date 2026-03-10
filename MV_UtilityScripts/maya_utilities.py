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


def get_materials_from_selection():
    """
    Grabs all materials assigned to the selected objects, skipping lambert1.
    Goes through each shape node and traces it back to its material through the shading engine.

    Returns three lists:
        mat_rows: one (material, object) pair per unique material found
        also_affected: other objects that share a material already in mat_rows
        lambert1_objects: objects where the only assigned material is lambert1
    """
    shapes = cmds.ls(selection=True, dag=True, shapes=True, noIntermediate=True) or []

    seen_mats = {}
    also_affected = []
    lambert1_objects = []

    for shape in shapes:
        transform = (cmds.listRelatives(shape, parent=True) or [shape])[0]
        obj_name = transform.split("|")[-1]

        shading_engines = cmds.listConnections(shape, type='shadingEngine') or []
        non_default_mats = []

        ### check each shading engine for a real material
        for se in shading_engines:
            mats = cmds.listConnections(se + '.surfaceShader') or []
            for mat in mats:
                if mat != 'lambert1':
                    non_default_mats.append(mat)

                    ### first time seeing this material, store it
                    if mat not in seen_mats:
                        seen_mats[mat] = obj_name

                    ### same material on a different object, track it separately
                    elif seen_mats[mat] != obj_name:
                        also_affected.append((obj_name, mat))

        ### if no real materials found, this object only has lambert1
        if not non_default_mats:
            lambert1_objects.append(obj_name)

    mat_rows = [(mat, obj) for mat, obj in seen_mats.items()]
    return mat_rows, also_affected, lambert1_objects


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
