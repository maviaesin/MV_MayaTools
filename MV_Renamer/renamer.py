import maya.cmds as cmds
from MV_UtilityScripts.constants_library import PREFIXES
from MV_UtilityScripts.object_utilities import ObjectUtilities
import MV_UtilityScripts.maya_utilities as uti


def configure_operable_object_dictionary():
    """
    Collects user-selected objects and stores relevant renaming data in `operable_objects`.
    Filters out shape nodes and processes only transform nodes.
    """
    ### INITIALIZE DICTIONARY TO STORE OPERABLE OBJECTS
    operable_objects = {
        "objects": []
    }

    prefix_dict = PREFIXES
    selected_objects = uti.get_user_object_selection()

    ### LOOP THROUGH SELECTED OBJECTS AND EXTRACT DATA
    for obj in selected_objects:
        opr = ObjectUtilities(obj)

        # Skip non-transform nodes (e.g., shape nodes)
        if cmds.nodeType(obj) != "transform":
            continue

        ### EXTRACT OBJECT PROPERTIES
        obj_path = cmds.ls(obj, long=True)[0]
        obj_name = opr.o_name_extractor()
        obj_type = opr.o_type_identifier()
        detected_prefix = opr.detect_prefix(obj_type, prefix_dict)
        prefix_check = opr.o_check_prefix(obj_name, obj_type, prefix_dict)

        ### STORE OBJECT DATA IN DICTIONARY
        operable_objects["objects"].append({
            "Object": obj,
            "Path": obj_path,
            "Name": obj_name,
            "DetectedType": obj_type,
            "DetectedPrefix": detected_prefix,
            "PrefixStatus": prefix_check
        })

    return operable_objects


### FILTER OBJECTS THAT NEED RENAMING (EXCLUDES CORRECTLY PREFIXED OBJECTS)
def exclude_objects_with_correct_prefixes():

    operable_objects = configure_operable_object_dictionary()

    obj_to_operate = [
        obj for obj in operable_objects["objects"]
        if obj["PrefixStatus"] in ["no_prefix", "incorrect_prefix"]
    ]

    return obj_to_operate


def rename_objects(obj_list):
    """
    Renames objects based on their detected prefix.
    Works for both 'rename all' and 'rename selected'.

    :param obj_list: List of objects to rename
    """
    for obj_data in obj_list:
        obj_path = obj_data["Path"]
        obj_name = obj_data["Name"]
        detected_prefix = obj_data["DetectedPrefix"]
        prefix_status = obj_data["PrefixStatus"]

        new_name = obj_name  # Initialize with the current name

        ### HANDLE PREFIX RENAMING LOGIC
        if prefix_status == "no_prefix":
            new_name = f"{detected_prefix}{obj_name}"

        elif prefix_status == "incorrect_prefix":
            if "_" in obj_name:
                stripped_name = "_".join(obj_name.split("_")[1:])
            else:
                stripped_name = obj_name

            new_name = f"{detected_prefix}{stripped_name}"

        ### RENAME OBJECT IN MAYA
        transform_node = obj_path.split('|')[-1]
        cmds.rename(transform_node, new_name, ignoreShape=True)
