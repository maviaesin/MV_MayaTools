import os
import sys
import maya.cmds as cmds

# Add Scripts folder to sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)


def build_shelf():
    try:
        shelf_name = "MV_Tools"

        if not cmds.shelfLayout(shelf_name, exists=True):
            cmds.shelfLayout(shelf_name, parent="ShelfLayout")

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
        print("[MV_Tools] Shelf built successfully.")

    except Exception as e:
        import traceback
        print(f"[MV_Tools] Failed to build shelf: {e}")
        traceback.print_exc()


cmds.evalDeferred(build_shelf)
