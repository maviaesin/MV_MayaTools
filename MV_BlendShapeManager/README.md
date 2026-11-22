# MV_BlendShapeManager

A blendshape toolkit that docks next to Maya's Shape Editor. Made for avatars whose body and clothing share target names, so one slider in the engine drives them all.

- Every button that changes the scene is one undo step.
- Everything also works from the Script Editor, without the window.
- Open it from the **MV_Tools** shelf or the **MV_Tools** menu.

---

## Global Shape Controller

Imitates the engine's character customizer: one slider per target name moves it on every mesh of the avatar at once.

- **Select:** the avatar's group, or one or more of its meshes, then click **Load Selected**.
- **Needs:** at least one selected mesh with a blendshape node.
- **Result:**
  - One row per target name, with a visibility toggle, a weight field and a slider.
  - A row whose targets differ shows **mixed**. Keyed, connected or locked targets are skipped and counted, like **2 of 3**.
  - **Refresh** reads the scene again. The list also follows Undo and Redo.

---

## Better Methods

### Create Blendshape
- **Select:** one mesh.
- **Needs:** no deformers after the skinCluster.
- **Result:** an empty node, `MV_Blendshape1`, placed before the skinCluster, so the pose never ends up in a target.

### Create Blendshape from Template
A template is a saved list of target names, in order, plus a node name prefix. Make and edit templates with **Templates...**.

- **Select:** one or more meshes, or the avatar's group.
- **Needs:** a template picked in the Templates window.
- **Result:**
  - A popup to tick which meshes to use, and to set the asset name.
  - Each mesh gets a node named `<prefix>_<asset>_<mesh>`, with every template target, empty and ready to sculpt.
  - Every mesh is checked first; if one can't take a node, nothing changes.

---

## Weight Actions

Work on what's selected in the Shape Editor.

### Paint Weights
- Opens Maya's Paint Blend Shape Weights tool with its Tool Settings.

### Reset Weights
- **Select:** targets, or whole nodes, in the Shape Editor.
- **Result:** painted weights are flooded with 1. For a node, choose its targets' weights, its base weights, or both.

### Bake Weights
- **Select:** one target in the Shape Editor.
- **Needs:** the target has painted weights, and no live target mesh connected.
- **Result:** the painting becomes part of the target's shape and its weights are reset to 1, so FBX export keeps it.

### Copy Weights
- **Select:** a node in the Shape Editor, then pick one target to copy from and the targets to copy to.
- **Result:** the targets get the exact painted weights of the first one. Unlike Maya's own copy, it can be undone.

### Merge and Bake Weights
- **Select:** a target in the Shape Editor.
- **Result:** what the node shows right now, painted weights included, saved into that target or into a new one. No mesh is duplicated.

---

## Proxy Wrap

Makes clothing follow the body's customization targets, then saves the result as clothing targets.

### Create Wrapped Proxies
- **Select:** the clothing meshes, then the body.
- **Needs:** bind pose, with every body slider at 0 (**Set Sliders to 0** does that), and the body's transformations frozen.
- **Result:** clean, skinless copies in `<Body>_ProxyGroup`, each wrapped to the body with a Proximity Wrap. The real meshes don't change.

### Add Proxy as Target
- **Select:** one or more proxies made by Create Wrapped Proxies, with the body sliders set to the shape you want.
- **Result:**
  - The shape each proxy shows becomes a target on the mesh it was copied from.
  - The name starts as the body slider that is on the most. An existing target with that name is replaced in place.
  - Works on moved or unfrozen meshes. The proxy is hidden afterwards.

---

## Templates

Opened with **Templates...** at the bottom of the toolkit.

- **New**, **Delete** and **Save** manage templates: a name, a node name prefix and the target names in order.
- **Import...** and **Export...** read and write `.json` files, to share templates with others.
- Two example templates come with the tool: `SimpleAvatarCustomization` and `EmoteShapes`.

---

## Validate

- **Select:** a mesh, then **Load Selected Mesh**, and pick a template.
- **Result:**
  - Lists missing, extra, likely misspelled (`eyesclosed`, `Eyes_Closed`) and empty targets.
  - **Add Missing Targets** adds the missing ones, empty, after the last target.
