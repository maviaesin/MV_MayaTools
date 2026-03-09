import maya.cmds as cmds
from MV_UtilityScripts import maya_utilities as uti


class ObjectUtilities:
    """
    ObjectUtilities primarily consists of simple methods to query or modify object attributes.
    For convenience, method and variable names follow the format `o_name`, where `o_` stands for object.
    """

    def __init__(self, obj_to_operate):

        self.object = obj_to_operate
        print(self.object)


    def o_name_extractor(self):
        """
        Returns: Name of the object as o_name string
        """
        o_name = self.object.split("|")[-1]
        #print(f"o_name equals to: {o_name}") ###DEBUGLINE
        return o_name

    def o_type_identifier(self):
        """
        Returns: Type of the object as o_type string.
        """
        children = cmds.listRelatives(self.object, children=True) or []

        if uti.check_object_is_skeletal_mesh(self.object):
            o_type = "skeletal_mesh"

        elif uti.check_object_is_mesh(self.object):
            o_type = "mesh"

        elif children and len(children) == 1:
            child = children[0]
            o_type = cmds.objectType(child)
        else:
            o_type = cmds.objectType(self.object)

        #print(f"o_type equals to: {o_type}")  ###DEBUGLINE

        return o_type

    def detect_prefix(self, o_type, prefix_dict):

        o_prefix = prefix_dict.get(o_type, "")  ### Get the correct prefix for the object type

        return f"{o_prefix}"

    def o_check_prefix(self, o_name, o_type, prefix_dict):

        expected_prefix = self.detect_prefix(o_type, prefix_dict)

        ### Extract the current prefix from the object name (if any)
        current_prefix = ""
        if "_" in o_name:
            current_prefix = o_name.split("_")[0] + "_"

        # Check prefix conditions
        if not current_prefix:
            return "no_prefix"
        elif current_prefix == expected_prefix:
            return "correct_prefix"
        else:
            return "incorrect_prefix"














