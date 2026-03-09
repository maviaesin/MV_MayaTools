import maya.cmds as cmds
from MV_Renamer.renamerUI import showUI
from MV_UtilityScripts.maya_utilities import get_user_object_selection


def launch_renamer():
    """
    Launches the Renamer UI from the Maya shelf button.
    Ensures that objects are selected before opening the UI.
    """
    try:
        get_user_object_selection()  # Check if the user has selected objects
        showUI()                     # Launch the UI
    except RuntimeError as e:
        cmds.warning(str(e))         # Show a warning if no objects are selected
