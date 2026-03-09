import maya.cmds as cmds
from MV_UtilityScripts.constants_library import PREFIXES
from MV_UtilityScripts.object_utilities import ObjectUtilities
import MV_UtilityScripts.maya_utilities as uti



### Configure a dictionary from user selected objects
operable_objects = {
        "objects": []
    }

def configure_operable_object_dictionary():
    prefix_dict = PREFIXES

    selected_objects = uti.get_user_object_selection()

    for obj in selected_objects:
        opr = ObjectUtilities(obj)

        print(f"iterating on:{obj}") ##DEBUGLINE

        obj_obj  = obj

        obj_path = cmds.ls(obj, long = True)[0]

        obj_name = opr.o_name_extractor()

        obj_type = opr.o_type_identifier()

        detected_prefix = opr.detect_prefix(obj_type, prefix_dict)

        prefix_check = opr.o_check_prefix(obj_name, obj_type, prefix_dict)

        ### OPERABLE OBJECT DICTIONARY CREATION

        # Add the object's information to the dictionary
        operable_objects["objects"].append({
            "Object": obj_obj,
            "Path": obj_path,
            "Name": obj_name,
            "DetectedType": obj_type,
            "DetectedPrefix": detected_prefix,
            "PrefixStatus": prefix_check
        })

configure_operable_object_dictionary()

### CONFIGURE THE OBJECTS TO OPERATE BY EXCLUDING OBJECT WITH CORRECT PREFIX

obj_to_operate = [
    obj for obj in operable_objects["objects"]
    if obj["PrefixStatus"] in ["no_prefix", "incorrect_prefix"]
]



### RENAMING SELECTED OBJECTS

def rename_all():

    for obj_data in obj_to_operate:
        obj_path = obj_data["Path"]
        obj_name = obj_data["Name"]
        detected_prefix = obj_data["DetectedPrefix"]
        prefix_status = obj_data["PrefixStatus"]

        new_name = obj_name  # Initialize with the current name

        if prefix_status == "no_prefix":
            # Add the correct prefix
            new_name = f"{detected_prefix}{obj_name}"

        elif prefix_status == "incorrect_prefix":
            # Remove the existing incorrect prefix (assuming it's up to the first '_')
            if "_" in obj_name:
                stripped_name = "_".join(obj_name.split("_")[1:])  # Remove incorrect prefix
            else:
                stripped_name = obj_name  # No underscore found, keep the name as-is

            # Add the correct prefix
            new_name = f"{detected_prefix}{stripped_name}"



        # Rename the object in Maya
        transform_node = obj_path.split('|')[-1]  # Extract the object name from the full path
        # new_full_path = cmds.rename(transform_node, new_name)
        cmds.rename(transform_node, new_name, ignoreShape=True)



def rename():
    pass