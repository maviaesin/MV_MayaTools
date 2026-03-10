import maya.cmds as cmds
from MV_UtilityScripts import maya_utilities as uti


class ObjectUtilities:
    """
    A utility class for querying and modifying object attributes in Maya.

    - Methods follow the format `o_<method_name>`, where `o_` stands for 'object'.
    """

    def __init__(self, obj_to_operate):
        """
        Initializes the ObjectUtilities class with the given object.

        Args:
            obj_to_operate (str): The name of the object to operate on.
        """
        self.o_obj = obj_to_operate

    def o_name_extractor(self):
        """
        Extracts the base name of the object from its full DAG path.

        Returns:
            str: The object's name (without hierarchy).
        """
        return self.o_obj.split("|")[-1]

    def o_type_identifier(self):
        """
        Identifies the type of the object based on its properties.

        Returns:
            str: The determined type of the object.
        """
        children = cmds.listRelatives(self.o_obj, children=True) or []

        ### CHECK IF OBJECT IS A SKELETAL MESH ###
        if uti.check_object_is_skeletal_mesh(self.o_obj):
            return "skeletal_mesh"

        ### CHECK IF OBJECT IS A STATIC MESH ###
        elif uti.check_object_is_mesh(self.o_obj):
            return "mesh"

        ### CHECK IF OBJECT HAS A SINGLE CHILD (USUALLY SHAPE NODE) ###
        elif children and len(children) == 1:
            return cmds.objectType(children[0])

        ### DEFAULT: RETURN OBJECT TYPE ###
        return cmds.objectType(self.o_obj)

    def detect_prefix(self, o_type, prefix_dict):
        """
        Retrieves the correct prefix for a given object type.

        Args:
            o_type (str): The type of the object.
            prefix_dict (dict): Dictionary mapping object types to prefixes.

        Returns:
            str: The prefix corresponding to the object's type.
        """
        return prefix_dict.get(o_type, "")

    def o_check_prefix(self, o_name, o_type, prefix_dict):
        """
        Checks if the object's current prefix matches the expected prefix.

        Args:
            o_name (str): The object's name.
            o_type (str): The object's type.
            prefix_dict (dict): Dictionary mapping object types to prefixes.

        Returns:
            str: One of ["no_prefix", "correct_prefix", "incorrect_prefix"].
        """
        expected_prefix = self.detect_prefix(o_type, prefix_dict)

        ### CHECK IF NAME STARTS WITH ANY KNOWN PREFIX ###
        current_prefix = ""
        for prefix in set(prefix_dict.values()):
            if prefix and o_name.startswith(prefix):
                current_prefix = prefix
                break

        ### CHECK PREFIX CONDITIONS ###
        if not current_prefix:
            return "no_prefix"
        elif current_prefix == expected_prefix:
            return "correct_prefix"
        else:
            return "incorrect_prefix"
