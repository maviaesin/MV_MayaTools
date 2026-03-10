# MV_MayaTools

A growing toolkit built to address the painpoints of 3D asset production for games. The goal is to cover the parts of the pipeline that are slow, repetitive, or just painful enough that artists avoid doing them properly.

---

## MV_UtilityScripts

The shared foundation every tool in this repo builds on. Rather than duplicating Maya API calls or hardcoding values across tools, MV_UtilityScripts centralizes that layer so each tool stays focused on what it actually does.

| Module | What it does |
|---|---|
| `maya_utilities.py` | Wraps and extends Maya's built-in methods. Instead of calling raw `cmds` functions everywhere, tools go through this module. Designed to be extended as new tools require new Maya operations. |
| `object_utilities.py` | Works on anything produced in Maya, whether that is a mesh, a material, or any other node type. Handles the things Maya does not make obvious, like identifying what kind of node something is or whether it follows a naming convention. |
| `constants_library.py` | A single place for all constants used across the toolkit. Prefixes, suffixes, naming rules, anything that would otherwise be hardcoded in multiple places lives here. |
| `Qt.py` | Needed for Maya compatibility. Maya 2022-2024 ships with PySide2, Maya 2025-2026 ships with PySide6. This shim lets all UI code run across those versions without branching. Keep it in the repo. |

---

## Tools

### MV_Renamer

Makes batch renaming easier for naming conventions, baking pipelines, or anything else that requires consistent object names across a scene.

- **Prefix tab** - scans selected objects, detects their type (static mesh, skeletal mesh), and flags anything with a missing or wrong prefix. Rename individually or all at once.
- **Suffix tab** - adds or removes `_low`, `_high`, or a custom suffix across the whole selection.
- **Materials tab** - finds all materials assigned to selected objects, shows prefix status, and lets you rename them from one screen. Material names can be edited inline before applying, without tracking down each one through Maya's attribute editors.

---

## Setup

Copy three things into `Documents/maya/scripts/`:

```
MV_Renamer/
MV_UtilityScripts/
userSetup.py
```

If you already have a `userSetup.py`, do not replace it. Open both files and copy the contents of this one into yours. It adds the scripts folder to Maya's Python path and builds the shelf.

Open Maya and an **MV_Tools** shelf will appear automatically.

---

## Roadmap

### MV_Renamer

- Ability to add custom prefixes and suffixes to objects.

### MV_SnapshotsPDF

Captures consistent model snapshots (wireframe, default texture, and assigned texture from multiple angles) and exports them to a PDF.
