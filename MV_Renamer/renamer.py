import re
import maya.cmds as cmds
from MV_UtilityScripts.constants_library import PREFIXES, SUFFIXES
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
        cmds.rename(obj_path, new_name, ignoreShape=True)


### SUFFIX OPERATIONS

def add_suffix(suffix):
    """
    Appends the given suffix to all selected transform nodes.
    Skips objects that already have the suffix.

    :param suffix: Suffix string to append (e.g. "_low", "_high")
    """
    selected = uti.get_user_object_selection()

    for obj in selected:
        if cmds.nodeType(obj) != "transform":
            continue

        name = obj.split("|")[-1]

        if not name.endswith(suffix):
            cmds.rename(obj, f"{name}{suffix}", ignoreShape=True)


def remove_suffix(known_suffixes):
    """
    Removes a known suffix from all selected transform nodes.
    Only strips the first matching suffix found.

    :param known_suffixes: List of suffix strings to check against (e.g. ["_low", "_high"])
    """
    selected = uti.get_user_object_selection()

    for obj in selected:
        if cmds.nodeType(obj) != "transform":
            continue

        name = obj.split("|")[-1]

        for suffix in known_suffixes:
            if name.endswith(suffix):
                cmds.rename(obj, name[:-len(suffix)], ignoreShape=True)
                break


### MATERIAL OPERATIONS

MATERIAL_PREFIXES = ["M_", "MAT_"]


def get_material_data():
    """
    Builds up the data needed for the Materials tab.
    Goes through each material found on the selection and figures out
    what type it is, whether it already has a prefix, and if the name looks auto-generated.

    :return: rows, also_affected, lambert1_objects
    """
    mat_rows, also_affected, lambert1_objects = uti.get_materials_from_selection()
    rows = []

    for mat, assigned_to in mat_rows:
        opr = ObjectUtilities(mat)
        obj_type = opr.o_type_identifier()

        ### skip anything that isnt a standard material type
        if obj_type not in ["lambert", "blinn", "phong"]:
            continue

        name = opr.o_name_extractor()

        ### check if the name already starts with a known prefix
        current_prefix = ""
        for p in MATERIAL_PREFIXES:
            if name.startswith(p):
                current_prefix = p
                break

        if current_prefix:
            prefix_status = "has_prefix"
        else:
            prefix_status = "no_prefix"

        ### strip the prefix to get the base name, then check if it looks auto-generated
        if current_prefix:
            base = name[len(current_prefix):]
        else:
            base = name

        is_auto_named = bool(re.match(r'^[a-zA-Z]+\d+$', base))

        rows.append({
            "Material": mat,
            "AssignedTo": assigned_to,
            "Type": obj_type,
            "Name": name,
            "IsAutoNamed": is_auto_named,
            "PrefixStatus": prefix_status,
        })

    return rows, also_affected, lambert1_objects


def rename_materials(mat_list, prefix):
    """
    Applies the given prefix to each material in the list.
    Strips M_ or MAT_ first if one is already there, so it doesnt stack up.
    The name used is whatever is in the dict (could be edited by the user in the UI).

    :param mat_list: list of material dicts
    :param prefix: the prefix to apply, e.g. "M_" or "MAT_"
    """
    for mat_data in mat_list:
        name = mat_data["Name"]

        ### strip any existing prefix before applying the new one
        base = name
        for p in MATERIAL_PREFIXES:
            if name.startswith(p):
                base = name[len(p):]
                break

        new_name = f"{prefix}{base}"

        if new_name != name:
            cmds.rename(mat_data["Material"], new_name)
