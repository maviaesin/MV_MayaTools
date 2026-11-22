import os
import sys
import maya.cmds as cmds

import MV_UtilityScripts

# Add Scripts folder to sys.path
# maya runs this file without __file__, so we find the Scripts folder through a package instead
scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(MV_UtilityScripts.__file__)))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)


def build_shelf():
    try:
        shelf_name = "MV_Tools"

        if not cmds.shelfLayout(shelf_name, exists=True):
            cmds.shelfLayout(shelf_name, parent="ShelfLayout")

        # maya refills the shelf from its saved prefs file, so clear it and add every button fresh
        old_buttons = cmds.shelfLayout(shelf_name, query=True, childArray=True) or []
        for button in old_buttons:
            cmds.deleteUI(button)

        icon_path = os.path.join(scripts_dir, "MV_Renamer", "MV_Renamer.png")
        if not os.path.exists(icon_path):
            icon_path = "commandButton.png"  # fallback to default Maya icon

        cmds.shelfButton(
            parent=shelf_name,
            label="MV_Renamer",
            annotation="MV Renamer - Asset Prefix Tool",
            sourceType="python",
            image=icon_path,
            command=(
                "import importlib\n"
                "import MV_Renamer.renamerUI as renamerUI\n"
                "importlib.reload(renamerUI)\n"
                "renamerUI.showUI()"
            )
        )

        icon_path = os.path.join(scripts_dir, "MV_BlendShapeManager", "MV_BlendShapeManager.png")
        if not os.path.exists(icon_path):
            icon_path = "commandButton.png"  # fallback to default Maya icon

        cmds.shelfButton(
            parent=shelf_name,
            label="MV_BlendShapeManager",
            annotation="MV Blendshape Toolkit",
            sourceType="python",
            image=icon_path,
            command=(
                "import importlib\n"
                "import MV_BlendShapeManager.blendshapeToolkitUI as blendshapeToolkitUI\n"
                "importlib.reload(blendshapeToolkitUI)\n"
                "blendshapeToolkitUI.showUI()"
            )
        )
        print("[MV_Tools] Shelf built successfully.")

    except Exception as e:
        import traceback
        print(f"[MV_Tools] Failed to build shelf: {e}")
        traceback.print_exc()


def build_menu():
    try:
        menu_name = "MV_Tools_Menu"

        # maya without its interface has no main window to add a menu to
        if not cmds.window("MayaWindow", exists=True):
            return
        if cmds.menu(menu_name, exists=True):
            cmds.deleteUI(menu_name)

        # a menu on the main window shows in every menu set (Modeling, Rigging, ...)
        cmds.menu(menu_name, label="MV_Tools", parent="MayaWindow", tearOff=True)

        # Ctrl+Shift+click on an item adds it to the current shelf
        cmds.menuItem(
            label="MV_Renamer",
            annotation="MV Renamer - Asset Prefix Tool",
            image=os.path.join(scripts_dir, "MV_Renamer", "MV_Renamer.png"),
            sourceType="python",
            command=(
                "import importlib\n"
                "import MV_Renamer.renamerUI as renamerUI\n"
                "importlib.reload(renamerUI)\n"
                "renamerUI.showUI()"
            )
        )
        cmds.menuItem(
            label="MV_BlendShape_Toolkit",
            annotation="MV Blendshape Toolkit",
            image=os.path.join(scripts_dir, "MV_BlendShapeManager", "MV_BlendShapeManager.png"),
            sourceType="python",
            command=(
                "import importlib\n"
                "import MV_BlendShapeManager.blendshapeToolkitUI as blendshapeToolkitUI\n"
                "importlib.reload(blendshapeToolkitUI)\n"
                "blendshapeToolkitUI.showUI()"
            )
        )
        cmds.menuItem(
            label="Global Shape Controller",
            annotation="One slider per target name, for every mesh of an avatar",
            image="polySphere.png",
            sourceType="python",
            command=(
                "import importlib\n"
                "import MV_BlendShapeManager.blendshapeGlobalControllerUI as blendshapeGlobalControllerUI\n"
                "importlib.reload(blendshapeGlobalControllerUI)\n"
                "blendshapeGlobalControllerUI.showUI()"
            )
        )
        print("[MV_Tools] Menu built successfully.")

    except Exception as e:
        import traceback
        print(f"[MV_Tools] Failed to build menu: {e}")
        traceback.print_exc()


# lowestPriority runs it after the rest of maya's startup work
cmds.evalDeferred(build_shelf, lowestPriority=True)
cmds.evalDeferred(build_menu, lowestPriority=True)
