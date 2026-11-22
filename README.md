# MV_MayaTools

A growing set of Maya tools for game asset production. Each one takes a slow, repetitive step of the pipeline, like naming conventions or blendshape setup for customizable characters, and makes it quick and hard to get wrong.

---

## MV_UtilityScripts

The shared foundation every tool in this repo builds on. Rather than duplicating Maya API calls or hardcoding values across tools, MV_UtilityScripts centralizes that layer so each tool stays focused on what it actually does.

| Module | What it does |
|---|---|
| `maya_utilities.py` | Wraps and extends Maya's built-in methods. Instead of calling raw `cmds` functions everywhere, tools go through this module. Designed to be extended as new tools require new Maya operations. |
| `object_utilities.py` | Works on anything produced in Maya, whether that is a mesh, a material, or any other node type. Handles the things Maya does not make obvious, like identifying what kind of node something is or whether it follows a naming convention. |
| `constants_library.py` | A single place for all constants used across the toolkit. Prefixes, suffixes, naming rules, anything that would otherwise be hardcoded in multiple places lives here. |
| `Qt.py` | Needed for Maya compatibility. Supported Maya versions are 2024-2026: Maya 2024 ships with PySide2, Maya 2025-2026 ship with PySide6. This shim lets all UI code run across those versions without branching. Third-party, included as is. |

---

## Tools

### MV_Renamer

Makes batch renaming easier for naming conventions, baking pipelines, or anything else that requires consistent object names across a scene.

- **Prefix tab** - scans selected objects, detects their type (static mesh, skeletal mesh), and flags anything with a missing or wrong prefix. Rename individually or all at once.
- **Suffix tab** - adds or removes `_low`, `_high`, or a custom suffix across the whole selection.
- **Materials tab** - finds all materials assigned to selected objects, shows prefix status, and lets you rename them from one screen. Material names can be edited inline before applying, without tracking down each one through Maya's attribute editors.

### MV_BlendShapeManager

A blendshape toolkit that docks next to Maya's Shape Editor, for avatars whose body and clothing share target names. Every action that changes the scene is one undo step. What each button needs and does: [MV_BlendShapeManager/README.md](MV_BlendShapeManager/README.md).

- **Global Shape Controller** - one slider per target name moves it on every mesh of the avatar at once, like the engine's customizer.
- **Create Blendshape** - places the node before the skinCluster, so the pose never ends up in a target.
- **Create Blendshape from Template** - adds a node with a saved list of target names to many meshes at once, named `<prefix>_<asset>_<mesh>`.
- **Validate** - finds missing, extra, misspelled and empty targets against a template.
- **Weight Actions** - bake, reset and copy painted weights, with undo. Merge and Bake turns what a node shows into a target without duplicating the mesh.
- **Proxy Wrap** - wraps clothing copies to the body so they follow its sliders, then saves what they show as clothing targets.

---

## Setup

Copy these into `Documents/maya/scripts/`:

```
MV_BlendShapeManager/
MV_Renamer/
MV_UtilityScripts/
userSetup.py
```

If you already have a `userSetup.py`, do not replace it. Open both files and copy the contents of this one into yours. It adds the scripts folder to Maya's Python path and builds the **MV_Tools** shelf and menu.

Open Maya: the **MV_Tools** shelf and the **MV_Tools** menu in the top bar will appear.

MV_BlendShapeManager is tested in Maya 2026; 2024 and 2025 aren't tested yet.

---

## Known Bugs

### MV_Tools

- The MV_Tools shelf sometimes doesn't appear on its own when Maya starts. The MV_Tools menu in Maya's top bar still opens every tool.

### MV_BlendShapeManager

- **Global Shape Controller:** scrolling the list with the mouse wheel over a slider moves that slider and sets every target with its name.
- **Global Shape Controller:** renaming a loaded avatar's group or meshes drops them at the next Refresh. Load the avatar again.
- **Templates:** renaming a template saves a new copy and leaves the old one. Delete the old one by hand.

### MV_Renamer

- A rename isn't one undo step: Ctrl+Z undoes one object at a time.

---

## Roadmap

### MV_Tools

- **Self-installing module** - MV_Tools installs itself as a Maya module, so nobody has to copy folders into `Documents/maya/scripts` or edit `userSetup.py`. This also fixes the shelf that sometimes doesn't appear.

### MV_BlendShapeManager

- **Fix the known bugs** - sliders that ignore the scroll wheel, and loaded avatars that survive a rename.
- **Flood with 0 or 1** - Reset Weights becomes Flood: black (0) or white (1), like Maya's paint tool.
- **Heatmap** - a column in the Global Shape Controller that colors each mesh by how far its vertices move in a target, in greyscale or heatmap colors.
- **More from the Global Shape Controller** - rows in a template's order with missing names shown, and one slider and visibility toggle for the whole avatar.
- **Copy Weights from another mesh** - copy a target's painted weights from the body to a jacket or shirt, matched by closest point, so clothing starts from an estimate instead of being painted from scratch.
- **Every body target in one click** - Add Proxy as Target runs through each body slider in turn, instead of one at a time.
- **Template categories and project folders** - group templates (Head: expressions, Body: customization) and read them from a shared project folder.
- **Better UI/UX** - Create Blendshape from Template in its own window, a clearer Templates window, Copy Weights that starts from the Shape Editor's selection, and layouts closer to Maya's own editors.

### MV_Renamer

- **Fix the known bug** - every rename as one undo step.
- Ability to add custom prefixes and suffixes to objects.
