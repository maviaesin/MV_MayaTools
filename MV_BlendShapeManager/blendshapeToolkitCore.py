import os
from dataclasses import dataclass
from enum import Enum

from maya import cmds, mel

from MV_BlendShapeManager.blendshapeTemplatesCore import BlendShapeTemplate, check_template
from MV_UtilityScripts import maya_utilities


@dataclass(frozen=True)
class LikelyTypo:
    scene_name: str
    template_name: str


@dataclass(frozen=True)
class TemplateCheck:
    """What Validate found when it compared a blendshape node with a template."""

    node: str
    node_target_names: tuple[str, ...]
    missing_targets: tuple[str, ...]
    extra_targets: tuple[str, ...]
    likely_typos: tuple[LikelyTypo, ...]
    empty_targets: tuple[str, ...]


@dataclass(frozen=True)
class TemplateSelection:
    """What Create Blendshape from Template works on: the meshes, and the asset name if the selection gives it."""

    meshes: tuple[str, ...]
    # the selected group's name; None when meshes were selected, so the artist is asked for it
    asset_name: str | None


@dataclass(frozen=True)
class TemplateCreationCheck:
    """What Create Blendshape from Template found, before changing anything."""

    # problems that stop the whole create
    refusals: tuple[str, ...]
    # names other nodes already have; Create Anyway lets Maya add a number to them
    taken_node_names: tuple[str, ...]


@dataclass(frozen=True)
class TargetState:
    """One target's weight, and whether it can be set."""

    target_name: str
    weight: float
    # False when the slider is keyed, connected or locked, so setting it would fail
    can_set_weight: bool


@dataclass(frozen=True)
class SelectedTarget:
    """A target picked in Maya's Shape Editor."""

    node: str
    index: int
    target_name: str


@dataclass(frozen=True)
class ActiveTarget:
    """A target that is on, for the warning before Merge and Bake Weights."""

    node: str
    target_name: str
    weight: float


@dataclass(frozen=True)
class ActiveTargets:
    """The targets that are on, split by whether Merge and Bake Weights includes them."""

    # other targets on the node being rebuilt: their shape becomes part of the result
    on_this_node: tuple[ActiveTarget, ...]
    # targets on the mesh's other blendshape nodes: seen in the viewport, but not part of the result
    on_other_nodes: tuple[ActiveTarget, ...]


@dataclass(frozen=True)
class PointMove:
    """How far one vertex moves, in the space before the skinCluster."""

    vertex_index: int
    offset: tuple[float, float, float]


@dataclass(frozen=True)
class CopyWeightsCheck:
    """What Copy Weights found before copying. Problems stop the copy; warnings only tell the user."""

    problems: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class WrappedProxiesCheck:
    """What Create Wrapped Proxies found before creating. Problems stop it; warnings only tell the user."""

    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    # targets not at 0 on the meshes, so the window knows when Set Sliders to 0 has something to do
    targets_that_are_on: tuple[ActiveTarget, ...]


@dataclass(frozen=True)
class ProxyTargetCheck:
    """What Add Proxy as Target found before adding. Problems stop it; warnings only tell the user."""

    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    # the real meshes that already have a target with that name, so it gets replaced, and the ones that get it new
    meshes_with_target: tuple[str, ...]
    meshes_without_target: tuple[str, ...]


@dataclass(frozen=True)
class AvatarSelection:
    """What the Global Shape Controller loads: the avatar's meshes that have blendshapes, and its group's name."""

    meshes: tuple[str, ...]
    # None when meshes were selected instead of a group
    group_name: str | None


@dataclass(frozen=True)
class AvatarTarget:
    """One target on one of the avatar's blendshape nodes, as the Global Shape Controller reads it."""

    target_name: str
    mesh: str
    node: str
    index: int
    weight: float
    is_visible: bool
    # False when the plug is keyed, connected or locked, so setting it would fail
    can_set_weight: bool
    can_set_visibility: bool


@dataclass(frozen=True)
class GlobalTarget:
    """Every target with one name on the avatar: one row of the Global Shape Controller."""

    target_name: str
    targets: tuple[AvatarTarget, ...]


@dataclass(frozen=True)
class SharedValue:
    """What a Global Shape Controller row shows: the weight and visibility most of its targets share."""

    weight: float
    # True when the targets don't all have the same weight, so the row is marked "mixed"
    is_weight_mixed: bool
    is_visible: bool
    is_visibility_mixed: bool


class NodeWeights(Enum):
    """Which painted weights Reset Weights floods with 1 when a whole node is selected."""

    # every target's own painting
    TARGET_WEIGHTS = "target weights"
    # the painting on the node itself, which scales every target at once
    BASE_WEIGHTS = "base weights"
    BOTH = "both"


# reading targets through the shape editor's mel function was an ai suggestion, instead of the channel box:
# it only shows the selected mesh's targets, by short name, so the same name on two nodes gets mixed up.
# i don't use the channel box in this workflow anyway, kept it this way just in case.
# TODO: look further into maya's mel commands and what getShapeEditorTreeviewSelection actually reads
# scope 4 of Maya's getShapeEditorTreeviewSelection means "the selected targets"
SHAPE_EDITOR_SELECTED_TARGETS_SCOPE = 4
# scope 1 means "the selected blendshape nodes"
SHAPE_EDITOR_SELECTED_NODES_SCOPE = 1

# Maya stores a target's full shape at item 6000; 5000 to 5999 are in-betweens
FULL_TARGET_ITEM = 6000

# points that moved less than this still count as not sculpted
EMPTY_TARGET_TOLERANCE = 0.0001

# Create Blendshape names its nodes MV_Blendshape1, 2, ..., so they stand apart from Maya's own blendShape1
DEFAULT_NODE_NAME_START = "MV_Blendshape"
# a template's node keeps the template's name here, so Validate finds it even after a rename
TEMPLATE_NAME_ATTRIBUTE = "mvTemplate"

PROXY_NAME_ENDING = "_Proxy"
PROXY_GROUP_NAME_ENDING = "_ProxyGroup"
# the hidden attribute on a proxy that links it to the mesh it was copied from
PROXY_SOURCE_ATTRIBUTE = "proxySourceMesh"
# Body_ProxyGroup, then Body_ProxyGroup_02 and on; 99 groups for one mesh is surely a mistake
# bc never let an endless search go rogue
PROXY_GROUP_COUNT_MAX = 99
# a transform that isn't moved, rotated or scaled, as the 16 numbers cmds.xform(matrix=True) gives
IDENTITY_MATRIX = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
# smaller differences than this still count as not moved, so rounding noise isn't a problem
FROZEN_TRANSFORM_TOLERANCE = 0.0001
TRANSFORM_ATTRIBUTES = (
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
)

# weights are shown and compared with 3 decimals, like in the Shape Editor
WEIGHT_DECIMALS = 3


# its own error so the UI can catch just this one and offer "create anyway"
class NodeNameTakenError(RuntimeError):
    pass


# its own error so the UI can show it in the same popup as the "added" messages
class DeformersAfterSkinClusterError(RuntimeError):
    pass


def add_blend_shapes_from_template(meshes, template, asset_name, allow_renamed_nodes=False):
    """Gives each mesh a node named <prefix>_<asset>_<mesh>, with the template's targets empty, before the skinCluster.

    One undo step. If one mesh can't take its node, nothing changes.
    A taken name raises NodeNameTakenError, unless allow_renamed_nodes lets Maya add a number.
    """
    check = check_template_creation(meshes, template, asset_name)
    if check.refusals:
        raise RuntimeError("\n".join(check.refusals) + "\nNothing was changed.")
    if check.taken_node_names and not allow_renamed_nodes:
        taken_names_text = ", ".join(f"'{name}'" for name in check.taken_node_names)
        raise NodeNameTakenError(
            f"Already used in this scene: {taken_names_text}. Reference the other avatar so it gets its own "
            "namespace, or create anyway and Maya adds a number to the end."
        )

    nodes = []
    cmds.undoInfo(openChunk=True, chunkName="Create Blendshape from Template")
    try:
        for mesh in meshes:
            node_name = build_template_node_name(template.node_name, asset_name, mesh)
            node = _create_blend_shape_node(mesh, node_name)
            _add_empty_targets(node, mesh, template.target_names, 0)
            cmds.addAttr(node, longName=TEMPLATE_NAME_ATTRIBUTE, dataType="string")
            cmds.setAttr(f"{node}.{TEMPLATE_NAME_ATTRIBUTE}", template.template_name, type="string")
            nodes.append(node)
    finally:
        cmds.undoInfo(closeChunk=True)
    return nodes


def check_template_creation(meshes, template, asset_name):
    """Finds what would stop each mesh from getting its template node. Changes nothing."""
    check_template(template)
    refusals = []
    taken_node_names = []
    # node name -> the first mesh that gets it, to catch two meshes that would get the same name
    mesh_by_node_name = {}
    for mesh in meshes:
        node_name = build_template_node_name(template.node_name, asset_name, mesh)
        refusals.extend(_find_template_mesh_refusals(mesh, template, node_name))

        if node_name in mesh_by_node_name:
            refusals.append(
                f"{mesh_by_node_name[node_name]} and {mesh} would both get '{node_name}'. "
                "Untick one of them, or rename one."
            )
        else:
            mesh_by_node_name[node_name] = mesh

        if cmds.objExists(node_name) and node_name not in taken_node_names:
            taken_node_names.append(node_name)
    return TemplateCreationCheck(refusals=tuple(refusals), taken_node_names=tuple(taken_node_names))


def _find_template_mesh_refusals(mesh, template, node_name):
    mesh_name = get_short_name(mesh)
    refusals = []
    if not maya_utilities.check_is_valid_maya_name(node_name):
        refusals.append(
            f"'{node_name}' is not a valid Maya name. "
            "Use only letters, numbers and _ in the asset name, and do not start with a number."
        )
    existing_node = find_template_node(mesh, template)
    if existing_node is not None:
        refusals.append(
            f"{mesh_name} already has '{existing_node}' from template {template.template_name}. "
            "Use Validate to compare it with the template."
        )
    deformers_after_skin_cluster = find_deformers_after_skin_cluster(mesh)
    if deformers_after_skin_cluster:
        refusals.append(
            f"{mesh_name} has deformers after its skinCluster: {', '.join(deformers_after_skin_cluster)}. "
            "Bake or remove them first."
        )
    return refusals


def get_template_selection():
    """Returns the selected meshes, or every mesh in one selected group. Raises if neither is selected."""
    # only for its "nothing selected" message, which every tool shares
    maya_utilities.get_user_object_selection()
    selected_objects = cmds.ls(selection=True, long=True)
    selected_meshes = []
    for selected_object in selected_objects:
        if maya_utilities.check_object_is_mesh(selected_object):
            selected_meshes.append(selected_object)
    # only meshes selected, in the order they were picked
    if len(selected_meshes) == len(selected_objects):
        return TemplateSelection(meshes=tuple(selected_meshes), asset_name=None)
    if len(selected_objects) > 1:
        raise RuntimeError("Select one or more meshes, or the avatar's group.")

    selected_object = selected_objects[0]
    meshes = find_meshes_in_group(selected_object)
    group_name = get_short_name(selected_object)
    if not meshes:
        raise RuntimeError(f"{group_name} has no meshes in it.")
    return TemplateSelection(meshes=tuple(meshes), asset_name=group_name.split(":")[-1])


def find_meshes_in_group(group):
    """Returns every mesh under the group, at any depth, as full paths sorted by path.

    Orig shapes (the hidden rest shapes of deformed meshes) are left out, and an instanced mesh is listed once.
    """
    shapes = cmds.listRelatives(group, allDescendents=True, type="mesh", fullPath=True, noIntermediate=True) or []
    meshes = []
    seen_shape_ids = []
    for shape in sorted(shapes):
        # an instanced shape has one path under each of its parents, but only one id
        shape_id = cmds.ls(shape, uuid=True)[0]
        if shape_id in seen_shape_ids:
            continue
        seen_shape_ids.append(shape_id)
        meshes.append(cmds.listRelatives(shape, parent=True, fullPath=True)[0])
    return meshes


def find_asset_name(mesh):
    """Returns the name of the mesh's top group without its namespace, "FemaleA" for "|FemaleA|Geo|Body".

    Returns "" when the mesh isn't in a group.
    """
    full_path = cmds.ls(mesh, long=True)[0]
    path_parts = full_path.split("|")
    mesh_has_a_group = len(path_parts) > 2
    if not mesh_has_a_group:
        return ""
    return path_parts[1].split(":")[-1]


def build_template_node_name(node_name_prefix, asset_name, mesh):
    """Returns <prefix>_<asset name>_<mesh>, or <prefix>_<mesh> when asset_name is empty, without namespaces."""
    mesh_name = get_short_name(mesh).split(":")[-1]
    if asset_name:
        return f"{node_name_prefix}_{asset_name}_{mesh_name}"
    return f"{node_name_prefix}_{mesh_name}"


def find_template_node(mesh, template):
    """Returns the mesh's node made from the template, or None.

    Looks at mvTemplate first, so renamed nodes are found; older nodes by their name prefix.
    """
    nodes = maya_utilities.find_blend_shape_nodes(mesh)
    for node in nodes:
        if not cmds.attributeQuery(TEMPLATE_NAME_ATTRIBUTE, node=node, exists=True):
            continue
        if cmds.getAttr(f"{node}.{TEMPLATE_NAME_ATTRIBUTE}") == template.template_name:
            return node

    for node in nodes:
        if node.split(":")[-1].startswith(f"{template.node_name}_"):
            return node
    return None


def create_blend_shape_node(mesh):
    """Adds an empty node before the mesh's skinCluster, named MV_Blendshape1, 2, ... One undo step."""
    node_name = get_default_node_name()
    _check_node_can_be_added(mesh, node_name, allow_renamed_node=False)

    cmds.undoInfo(openChunk=True, chunkName="Create Blendshape")
    try:
        node = _create_blend_shape_node(mesh, node_name)
    finally:
        cmds.undoInfo(closeChunk=True)
    return node


def get_default_node_name():
    """Returns the first free name of MV_Blendshape1, MV_Blendshape2, ..."""
    # there can't be more taken names than nodes, so one of these numbers is always free
    for number in range(1, len(cmds.ls()) + 2):
        node_name = f"{DEFAULT_NODE_NAME_START}{number}"
        if not cmds.objExists(node_name):
            return node_name
    raise AssertionError("A free blendshape node name always exists.")


def _check_node_can_be_added(mesh, node_name, allow_renamed_node):
    """Raises if a blendshape node called node_name can't go on the mesh. Changes nothing."""
    mesh_name = mesh.split("|")[-1]

    if node_name in maya_utilities.find_blend_shape_nodes(mesh):
        raise RuntimeError(f"{mesh_name} already has '{node_name}'. Use Validate to compare it with a template.")

    deformers_after_skin_cluster = find_deformers_after_skin_cluster(mesh)
    if deformers_after_skin_cluster:
        raise DeformersAfterSkinClusterError(
            f"{mesh_name} has deformers after its skinCluster: {', '.join(deformers_after_skin_cluster)}. "
            "Bake or remove them first, then try again. Nothing was changed."
        )

    node_name_is_taken = cmds.objExists(node_name)
    if node_name_is_taken and not allow_renamed_node:
        raise NodeNameTakenError(
            f"'{node_name}' is already used in this scene. Reference the other avatar "
            f"so it gets its own namespace, or create it anyway as '{node_name}1'."
        )


def _find_next_target_index(node):
    """Returns the index after the last target. Indices can have gaps, so it's never just the count."""
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    if not indices:
        return 0
    return max(indices) + 1


def get_target_names(node):
    """Returns the node's target names in index order."""
    # indices can have gaps where targets were deleted, so never count from 0
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    target_names = []
    for index in indices:
        target_name = cmds.aliasAttr(f"{node}.weight[{index}]", query=True)
        # Maya gives "" or None for a target without a name; Validate then lists its plug as extra
        if not target_name:
            target_name = f"weight[{index}]"
        target_names.append(target_name)
    return target_names


def validate_against_template(node, template):
    """Compares a blendshape node's targets with the template and finds empty ones. Changes nothing in the scene.

    The node name is not compared: a body and its clothing in one scene can never share it.
    """
    check_template(template)
    if not cmds.objExists(node):
        raise RuntimeError(f"{node} is not in the scene anymore. Load the mesh again.")
    if not cmds.objectType(node, isType="blendShape"):
        raise RuntimeError(f"{node} is not a blendshape node.")
    node_target_names = get_target_names(node)

    # scene names the template doesn't have: each one is either a likely typo or extra
    unmatched_scene_names = []
    for scene_name in node_target_names:
        if scene_name not in template.target_names:
            unmatched_scene_names.append(scene_name)

    missing_targets = []
    likely_typos = []
    for template_name in template.target_names:
        if template_name in node_target_names:
            continue
        similar_name = _find_similar_name(template_name, unmatched_scene_names)
        if similar_name is None:
            missing_targets.append(template_name)
        else:
            likely_typos.append(LikelyTypo(scene_name=similar_name, template_name=template_name))
            # a scene name can only be the typo of one template name
            unmatched_scene_names.remove(similar_name)

    return TemplateCheck(
        node=node,
        node_target_names=tuple(node_target_names),
        missing_targets=tuple(missing_targets),
        extra_targets=tuple(unmatched_scene_names),
        likely_typos=tuple(likely_typos),
        empty_targets=tuple(find_empty_targets(node)),
    )


def find_empty_targets(node):
    """Returns the names of the node's targets that have no sculpted data yet."""
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    target_names = get_target_names(node)
    empty_targets = []
    for position, index in enumerate(indices):
        if not _check_target_has_sculpted_data(node, index):
            empty_targets.append(target_names[position])
    return empty_targets


def _check_target_has_sculpted_data(node, index):
    target_group = f"{node}.inputTarget[0].inputTargetGroup[{index}]"
    # 6000 is the full target, 5000 to 5999 are in-betweens; any of them can hold a sculpt
    item_indices = cmds.getAttr(f"{target_group}.inputTargetItem", multiIndices=True) or []
    for item_index in item_indices:
        # Maya stores only the moved points, and nothing at all for an empty target
        moved_points = cmds.getAttr(f"{target_group}.inputTargetItem[{item_index}].inputPointsTarget") or []
        for point in moved_points:
            if _check_point_has_moved(point):
                return True
    return False


def _check_point_has_moved(point):
    """Takes x, y, z, or Maya's x, y, z, 1.0, and says whether the point moved at all."""
    # a 4th value from Maya is always 1.0, only x, y and z say how far the point moved
    for value in point[:3]:
        if abs(value) > EMPTY_TARGET_TOLERANCE:
            return True
    return False


def add_missing_targets(mesh, node, template):
    """Adds the template's missing targets to the mesh's node, empty, after the last target.

    Returns the added names.
    """
    # check again here, so a list from an older Validate can never be used
    check = validate_against_template(node, template)
    if not check.missing_targets:
        return []

    cmds.undoInfo(openChunk=True, chunkName="Add Missing Targets")
    try:
        _add_empty_targets(node, mesh, check.missing_targets, _find_next_target_index(node))
    finally:
        cmds.undoInfo(closeChunk=True)

    return list(check.missing_targets)


def _simplify_name(name):
    # EyesClosed, eyesclosed and Eyes_Closed all become eyesclosed
    return name.lower().replace("_", "")


def _find_similar_name(template_name, scene_names):
    """Returns the scene name that differs from template_name only in letter case or _, if there is one."""
    for scene_name in scene_names:
        if _simplify_name(scene_name) == _simplify_name(template_name):
            return scene_name
    return None


def find_deformers_after_skin_cluster(mesh):
    """Returns the deformers that run after the mesh's skinCluster. Empty if there is no skinCluster."""
    # history starts at the mesh and goes backwards, so everything before the skinCluster runs after it
    history = cmds.listHistory(mesh) or []
    deformers_after = []
    for deformer in cmds.ls(history, type="geometryFilter"):
        deformer_type = cmds.nodeType(deformer)
        if deformer_type == "skinCluster":
            return deformers_after
        # tweak nodes are maya's own bookkeeping, not real deformers
        if deformer_type != "tweak":
            deformers_after.append(deformer)

    # no skinCluster means nothing runs "after" it
    return []


def _create_blend_shape_node(mesh, node_name):
    """Puts the node directly before the skinCluster, so sculpting only has to undo the skin."""
    skin_clusters = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
    if not skin_clusters:
        # no skin, so the end of the chain is safe
        return cmds.blendShape(mesh, name=node_name)[0]

    # start at the front, then step past one deformer at a time until the skinCluster is next.
    # reorderDeformers only behaves when the two deformers sit next to each other.
    node = cmds.blendShape(mesh, name=node_name, frontOfChain=True)[0]
    deformer_count = len(cmds.ls(cmds.listHistory(mesh) or [], type="geometryFilter"))
    for _ in range(deformer_count):
        # history goes from the mesh backwards, so the item before ours runs right after it
        deformers = cmds.ls(cmds.listHistory(mesh) or [], type="geometryFilter")
        deformer_after_node = deformers[deformers.index(node) - 1]
        if deformer_after_node == skin_clusters[0]:
            return node
        cmds.reorderDeformers(node, deformer_after_node, mesh)

    raise RuntimeError(f"Could not move {node} in front of the skinCluster on {mesh}.")


def _add_empty_targets(node, mesh, target_names, first_index):
    """Adds every target, from first_index on, as a copy of what comes into the node, so they start out empty."""
    # copying the node's input (not the Orig shape) keeps other blendshapes out of our targets
    input_plug = cmds.listConnections(
        f"{node}.input[0].inputGeometry", source=True, destination=False, plugs=True
    )[0]

    temporary_shape = cmds.createNode("mesh")
    temporary_mesh = cmds.listRelatives(temporary_shape, parent=True, fullPath=True)[0]
    cmds.connectAttr(input_plug, f"{temporary_shape}.inMesh")

    for offset, target_name in enumerate(target_names):
        index = first_index + offset
        cmds.blendShape(node, edit=True, target=(mesh, index, temporary_mesh, 1.0))
        cmds.aliasAttr(target_name, f"{node}.weight[{index}]")

    # Each target keeps its own copy of the points, so the temporary mesh is not needed anymore.
    cmds.delete(temporary_mesh)


def list_blend_shape_nodes():
    """Returns every blendshape node in the scene, sorted by name."""
    return sorted(cmds.ls(type="blendShape"))


def get_target_states(node):
    """Returns every target's weight, in index order."""
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    target_names = get_target_names(node)
    target_states = []
    for position, index in enumerate(indices):
        weight_plug = f"{node}.weight[{index}]"
        target_states.append(
            TargetState(
                target_name=target_names[position],
                weight=cmds.getAttr(weight_plug),
                can_set_weight=cmds.getAttr(weight_plug, settable=True),
            )
        )
    return target_states


def set_target_weight(node, target_name, weight):
    """Sets the target's weight. Raises RuntimeError if the slider is keyed, connected or locked."""
    # target names are aliases, so node.EyesClosed is the same plug as node.weight[0]
    weight_plug = f"{node}.{target_name}"
    if not cmds.getAttr(weight_plug, settable=True):
        raise RuntimeError(f"{target_name} on {node} is keyed, connected or locked, so its weight can't be set.")
    cmds.setAttr(weight_plug, weight)




def get_readme_path():
    """Returns the full path of the toolkit's README.md, which Help opens."""
    tool_folder = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(tool_folder, "README.md")
    if not os.path.isfile(readme_path):
        raise RuntimeError(f"The README is missing. It should be at {readme_path}.")
    return readme_path


def get_shape_editor_selected_targets():
    """Returns the targets selected in the Shape Editor. Raises if none are, or one is gone."""
    # Maya's own Shape Editor function; it gives "node.index" strings like "blendShape1.0"
    selected_items = mel.eval(f"getShapeEditorTreeviewSelection({SHAPE_EDITOR_SELECTED_TARGETS_SCOPE})") or []
    if not selected_items:
        raise RuntimeError("Select one or more targets in the Shape Editor first.")

    selected_targets = []
    for selected_item in selected_items:
        # Maya names can't contain a dot, so the only dot is the one between node and index
        node, index_text = selected_item.split(".")
        index = int(index_text)
        selected_targets.append(
            SelectedTarget(node=node, index=index, target_name=_find_target_name(node, index))
        )
    return selected_targets


def _find_target_name(node, index):
    """Returns the name of the node's target at index. Raises if it's gone, for example after a delete."""
    if not cmds.objExists(node):
        raise RuntimeError(f"{node} is not in the scene anymore. Select the targets in the Shape Editor again.")
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    if index not in indices:
        raise RuntimeError(f"{node} has no target at index {index}. Select the targets in the Shape Editor again.")
    return get_target_names(node)[indices.index(index)]


def check_targets_share_one_node(selected_targets):
    """Returns the one node all the selected targets are on. Raises if they're on different nodes."""
    node = selected_targets[0].node
    for selected_target in selected_targets:
        if selected_target.node != node:
            raise RuntimeError("Select targets from one blendshape node only.")
    return node


def find_deformed_mesh(node):
    """Returns the mesh the blendshape node deforms, or None if it doesn't deform one anymore."""
    shapes = cmds.blendShape(node, query=True, geometry=True) or []
    if not shapes:
        return None
    # a blendshape node can deform several meshes, but BSM always makes one per mesh
    return cmds.listRelatives(shapes[0], parent=True)[0]


def find_active_targets(node, except_target_name):
    """Returns the targets that are on, except the one being rebuilt, for the warning before Merge and Bake Weights."""
    on_this_node = _find_targets_that_are_on(node, except_target_name=except_target_name)

    other_nodes = []
    mesh = find_deformed_mesh(node)
    if mesh is not None:
        other_nodes = maya_utilities.find_blend_shape_nodes(mesh)

    on_other_nodes = []
    for other_node in other_nodes:
        if other_node != node:
            # other nodes have no target being rebuilt, so every target that's on is listed
            on_other_nodes.extend(_find_targets_that_are_on(other_node, except_target_name=None))

    return ActiveTargets(on_this_node=tuple(on_this_node), on_other_nodes=tuple(on_other_nodes))


def _find_targets_that_are_on(node, except_target_name):
    targets_that_are_on = []
    for target in get_target_states(node):
        is_the_excepted_target = target.target_name == except_target_name
        if target.weight != 0 and not is_the_excepted_target:
            targets_that_are_on.append(ActiveTarget(node=node, target_name=target.target_name, weight=target.weight))
    return targets_that_are_on


def rebuild_with_weights_into_target(node, target_name):
    """Writes what the node shows right now, painted weights included, into an existing target.

    FBX drops painted weights, so this bakes them into the shape.
    """
    index = _find_target_index(node, target_name)
    _check_target_has_no_live_mesh(node, index, target_name)
    point_moves = _measure_node_point_moves(node)

    cmds.undoInfo(openChunk=True, chunkName="Merge and Bake Weights")
    try:
        _write_point_moves(node, index, FULL_TARGET_ITEM, point_moves)
    finally:
        cmds.undoInfo(closeChunk=True)


def rebuild_with_weights_into_new_target(node, new_target_name):
    """Adds a new target, after the last one, with what the node adds to the mesh right now."""
    if not maya_utilities.check_is_valid_maya_name(new_target_name):
        raise RuntimeError(
            f"'{new_target_name}' is not a valid Maya name. "
            "Use only letters, numbers and _, and do not start with a number."
        )
    if new_target_name in get_target_names(node):
        raise RuntimeError(f"{node} already has a target called '{new_target_name}'. Pick another name.")
    mesh = find_deformed_mesh(node)
    if mesh is None:
        raise RuntimeError(f"{node} doesn't deform a mesh, so there is nothing to merge and bake.")
    point_moves = _measure_node_point_moves(node)

    index = _find_next_target_index(node)
    cmds.undoInfo(openChunk=True, chunkName="Merge and Bake Weights")
    try:
        _add_empty_targets(node, mesh, (new_target_name,), index)
        _write_point_moves(node, index, FULL_TARGET_ITEM, point_moves)
    finally:
        cmds.undoInfo(closeChunk=True)


def _find_target_index(node, target_name):
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    target_names = get_target_names(node)
    if target_name not in target_names:
        raise RuntimeError(f"{node} has no target called '{target_name}'.")
    return indices[target_names.index(target_name)]


def _measure_node_point_moves(node):
    """Returns how far the node moves each point: what comes out minus what goes in.

    Read before the skinCluster, so the rig pose never ends up in it.
    """
    input_plug = cmds.listConnections(
        f"{node}.input[0].inputGeometry", source=True, destination=False, plugs=True
    )[0]
    points_in = _read_points_of_plug(input_plug)
    points_out = _read_points_of_plug(f"{node}.outputGeometry[0]")

    point_moves = []
    for vertex_index, point_in in enumerate(points_in):
        point_out = points_out[vertex_index]
        offset = (point_out[0] - point_in[0], point_out[1] - point_in[1], point_out[2] - point_in[2])
        if _check_point_has_moved(offset):
            point_moves.append(PointMove(vertex_index=vertex_index, offset=offset))

    if not point_moves:
        raise RuntimeError(f"Nothing on {node} moves the mesh right now, so there is nothing to merge and bake.")
    return point_moves


def _read_points_of_plug(geometry_plug):
    """Returns the vertex positions a geometry plug carries, by showing it on a temporary mesh."""
    # i couldn't figure out how to read point data straight from a plug, so ai suggested plugging it into a temporary mesh and reading that mesh's vertices with xform.
    # TODO: deep dive into what flows through a geometry plug, and if there's a way without the temp mesh
    temporary_shape = cmds.createNode("mesh")
    temporary_mesh = cmds.listRelatives(temporary_shape, parent=True, fullPath=True)[0]
    cmds.connectAttr(geometry_plug, f"{temporary_shape}.inMesh")
    flat_positions = cmds.xform(f"{temporary_mesh}.vtx[*]", query=True, translation=True, objectSpace=True)
    cmds.delete(temporary_mesh)

    # xform gives one long list, x y z x y z ..., so every 3 numbers are one point
    points = []
    for start in range(0, len(flat_positions), 3):
        points.append(flat_positions[start:start + 3])
    return points


def _write_point_moves(node, index, item_index, point_moves):
    """Stores the moves as one shape of the target (its full shape, or an in-between), the way Maya stores a sculpt."""
    item = f"{node}.inputTarget[0].inputTargetGroup[{index}].inputTargetItem[{item_index}]"
    points = []
    components = []
    for point_move in point_moves:
        points.append((point_move.offset[0], point_move.offset[1], point_move.offset[2], 1.0))
        components.append(f"vtx[{point_move.vertex_index}]")
    # setAttr wants each point as its own argument
    cmds.setAttr(f"{item}.inputPointsTarget", len(points), *points, type="pointArray")
    cmds.setAttr(f"{item}.inputComponentsTarget", len(components), *components, type="componentList")


def reset_painted_weights(selected_targets):
    """Sets the painted weights of every given target back to 1, in one undo step.

    After Merge and Bake Weights, this shows the target the way it will export.
    """
    cmds.undoInfo(openChunk=True, chunkName="Reset Weights")
    try:
        for selected_target in selected_targets:
            _reset_target_weights(selected_target.node, selected_target.index)
    finally:
        cmds.undoInfo(closeChunk=True)


def _reset_target_weights(node, index):
    _flood_weights_with_one(f"{node}.inputTarget[0].inputTargetGroup[{index}].targetWeights")


def _flood_weights_with_one(weights_plug):
    # only painted vertices have an entry; weights that were never painted are already 1 everywhere
    painted_vertices = cmds.getAttr(weights_plug, multiIndices=True) or []
    if not painted_vertices:
        return
    last_vertex = max(painted_vertices)
    # one setAttr for the whole range [0:last] is much faster than one per vertex on a big mesh
    cmds.setAttr(f"{weights_plug}[0:{last_vertex}]", *([1.0] * (last_vertex + 1)))


def get_shape_editor_selected_nodes():
    """Returns the blendshape nodes selected in Maya's Shape Editor (not their targets), or [] if none are."""
    selected_nodes = mel.eval(f"getShapeEditorTreeviewSelection({SHAPE_EDITOR_SELECTED_NODES_SCOPE})") or []
    for node in selected_nodes:
        if not cmds.objExists(node):
            raise RuntimeError(f"{node} is not in the scene anymore. Select it in the Shape Editor again.")
    return selected_nodes


def reset_node_weights(nodes, weights_to_reset):
    """Floods the painted weights of whole nodes with 1, in one undo step.

    Every target's own weights, the node's base weights (which scale every target at once), or both.
    """
    cmds.undoInfo(openChunk=True, chunkName="Reset Weights")
    try:
        for node in nodes:
            _reset_one_node_weights(node, weights_to_reset)
    finally:
        cmds.undoInfo(closeChunk=True)


def _reset_one_node_weights(node, weights_to_reset):
    reset_target_weights = weights_to_reset in (NodeWeights.TARGET_WEIGHTS, NodeWeights.BOTH)
    reset_base_weights = weights_to_reset in (NodeWeights.BASE_WEIGHTS, NodeWeights.BOTH)
    if reset_target_weights:
        for index in cmds.getAttr(f"{node}.weight", multiIndices=True) or []:
            _reset_target_weights(node, index)
    if reset_base_weights:
        # Maya's paint tool paints the node itself here; inputTarget[0].baseWeights does nothing in Maya 2026
        _flood_weights_with_one(f"{node}.weightList[0].weights")


def start_paint_blendshape_weights_tool():
    """Starts Maya's Paint Blend Shape Weights tool with its Tool Settings, the same as the Shape Editor does."""
    # Maya's own runtime command; the Options version also opens Tool Settings, where the target is picked
    mel.eval("ArtPaintBlendShapeWeightsToolOptions")


def bake_painted_weights(node, target_name):
    """Multiplies a target's sculpt by its painted weights, then floods the weights with 1. One undo step.

    The target looks the same, and FBX keeps it.
    """
    index = _find_target_index(node, target_name)
    _check_target_has_no_live_mesh(node, index, target_name)
    target_group = f"{node}.inputTarget[0].inputTargetGroup[{index}]"
    painted_weights = _read_painted_weights(f"{target_group}.targetWeights")
    if not painted_weights:
        raise RuntimeError(f"{target_name} has no painted weights, so there is nothing to bake.")

    # 6000 is the full shape, 5000 to 5999 are in-betweens; the painting scales all of them
    item_indices = cmds.getAttr(f"{target_group}.inputTargetItem", multiIndices=True) or []
    cmds.undoInfo(openChunk=True, chunkName="Bake Weights")
    try:
        for item_index in item_indices:
            _bake_weights_into_item(node, index, item_index, painted_weights)
        _reset_target_weights(node, index)
    finally:
        cmds.undoInfo(closeChunk=True)


def _check_target_has_no_live_mesh(node, index, target_name):
    """Raises if a mesh from Maya's Rebuild Target is still connected: it would overwrite any change."""
    target_item = f"{node}.inputTarget[0].inputTargetGroup[{index}].inputTargetItem[{FULL_TARGET_ITEM}]"
    live_meshes = cmds.listConnections(f"{target_item}.inputGeomTarget") or []
    if live_meshes:
        raise RuntimeError(
            f"{target_name} is still connected to the mesh {live_meshes[0]}. Delete that mesh first, then try again."
        )


def _read_painted_weights(weights_plug):
    """Returns {vertex: weight} for the painted vertices only; every other vertex is at 1."""
    painted_weights = {}
    for vertex_index in cmds.getAttr(weights_plug, multiIndices=True) or []:
        painted_weights[vertex_index] = cmds.getAttr(f"{weights_plug}[{vertex_index}]")
    return painted_weights


def _bake_weights_into_item(node, index, item_index, painted_weights):
    item = f"{node}.inputTarget[0].inputTargetGroup[{index}].inputTargetItem[{item_index}]"
    points = cmds.getAttr(f"{item}.inputPointsTarget") or []
    if not points:
        return
    vertex_indices = _expand_vertex_components(cmds.getAttr(f"{item}.inputComponentsTarget"))

    point_moves = []
    for position, vertex_index in enumerate(vertex_indices):
        point = points[position]
        # .get with 1.0: a vertex that was never painted keeps its full move
        weight = painted_weights.get(vertex_index, 1.0)
        point_moves.append(
            PointMove(vertex_index=vertex_index, offset=(point[0] * weight, point[1] * weight, point[2] * weight))
        )
    _write_point_moves(node, index, item_index, point_moves)


def _expand_vertex_components(components):
    """Turns Maya's short vertex lists into one index per vertex: ["vtx[2]", "vtx[4:6]"] becomes [2, 4, 5, 6]."""
    vertex_indices = []
    for component in components:
        # the part between the brackets: "2" for one vertex, "4:6" for vertices 4 to 6
        inside_brackets = component[component.index("[") + 1:-1]
        if ":" in inside_brackets:
            first_text, last_text = inside_brackets.split(":")
            vertex_indices.extend(range(int(first_text), int(last_text) + 1))
        else:
            vertex_indices.append(int(inside_brackets))
    return vertex_indices


def find_shape_editor_nodes():
    """Returns the nodes picked in the Shape Editor: the selected nodes, then the nodes of the selected targets.

    Returns [] if nothing is selected there.
    """
    nodes = get_shape_editor_selected_nodes()
    # "node.index" strings like "blendShape1.0", the same as get_shape_editor_selected_targets reads
    selected_items = mel.eval(f"getShapeEditorTreeviewSelection({SHAPE_EDITOR_SELECTED_TARGETS_SCOPE})") or []
    for selected_item in selected_items:
        node = selected_item.split(".")[0]
        if not cmds.objExists(node):
            raise RuntimeError(f"{node} is not in the scene anymore. Select it in the Shape Editor again.")
        if node not in nodes:
            nodes.append(node)
    return nodes


def find_painted_targets(node):
    """Returns the names of the node's targets that have painting: at least one weight that isn't 1."""
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    target_names = get_target_names(node)
    painted_targets = []
    for position, index in enumerate(indices):
        if _check_target_has_painting(node, index):
            painted_targets.append(target_names[position])
    return painted_targets


def _check_target_has_painting(node, index):
    # after Reset Weights every vertex has an entry again, but they're all 1, so that's no painting
    painted_weights = _read_painted_weights(f"{node}.inputTarget[0].inputTargetGroup[{index}].targetWeights")
    for weight in painted_weights.values():
        if weight != 1.0:
            return True
    return False


def check_copy_weights(node, source_target_name, destination_target_names):
    """Finds what would stop Copy Weights, and what the user should know first. Changes nothing.

    source_target_name is None when no source is picked yet.
    """
    if not cmds.objExists(node):
        return CopyWeightsCheck(problems=(f"{node} is not in the scene anymore.",), warnings=())

    problems = []
    target_names = get_target_names(node)
    if source_target_name is None:
        problems.append("Pick the target to copy from.")
    if not destination_target_names:
        problems.append("Pick one or more targets to copy to.")
    picked_target_names = list(destination_target_names)
    if source_target_name is not None:
        picked_target_names.append(source_target_name)
    for target_name in picked_target_names:
        if target_name not in target_names:
            problems.append(f"{node} has no target called '{target_name}'. It may have been renamed or deleted.")
    if problems:
        return CopyWeightsCheck(problems=tuple(problems), warnings=())

    painted_targets = find_painted_targets(node)
    if source_target_name in destination_target_names:
        problems.append(f"{source_target_name} is both the source and a destination. Pick it on one side only.")
    if source_target_name not in painted_targets:
        problems.append(
            f"{source_target_name} has no painted weights, so there is nothing to copy. "
            "To flood weights with 1, use Reset Weights."
        )

    warnings = []
    painted_destinations = []
    for target_name in destination_target_names:
        if target_name in painted_targets and target_name != source_target_name:
            painted_destinations.append(target_name)
    if painted_destinations:
        warnings.append(f"The painting on {', '.join(painted_destinations)} will be replaced.")
    return CopyWeightsCheck(problems=tuple(problems), warnings=tuple(warnings))


def copy_painted_weights(node, source_target_name, destination_target_names):
    """Gives every destination target exactly the source target's painted weights, in one undo step.

    Maya's own blendShape(copyWeights=...) does the same, but Undo doesn't bring the old weights back.
    """
    # check again here, so a check from before an Undo or a delete can never be used
    check = check_copy_weights(node, source_target_name, destination_target_names)
    if check.problems:
        raise RuntimeError(check.problems[0])

    source_index = _find_target_index(node, source_target_name)
    painted_weights = _read_painted_weights(f"{node}.inputTarget[0].inputTargetGroup[{source_index}].targetWeights")

    cmds.undoInfo(openChunk=True, chunkName="Copy Weights")
    try:
        for target_name in destination_target_names:
            index = _find_target_index(node, target_name)
            _write_painted_weights(f"{node}.inputTarget[0].inputTargetGroup[{index}].targetWeights", painted_weights)
    finally:
        cmds.undoInfo(closeChunk=True)


def _write_painted_weights(weights_plug, painted_weights):
    """Replaces all the painting on weights_plug: painted vertices get their weight, every other vertex 1."""
    # the destination's own old painting may reach further than the source's, so cover both
    old_painted_vertices = cmds.getAttr(weights_plug, multiIndices=True) or []
    last_vertex = max(list(painted_weights) + old_painted_vertices)

    weights = []
    for vertex_index in range(last_vertex + 1):
        weights.append(painted_weights.get(vertex_index, 1.0))
    # one setAttr for the whole range, like _flood_weights_with_one
    cmds.setAttr(f"{weights_plug}[0:{last_vertex}]", *weights)


def get_short_name(path):
    """Returns the name without its parents, "Tshirt" for "|Character|Tshirt", for messages and new node names."""
    return path.split("|")[-1]


def get_selected_meshes_for_wrap():
    """Returns the selected meshes in pick order. A selected blendshape node counts as its mesh."""
    selected_meshes = []
    for selected_item in cmds.ls(selection=True, long=True):
        if cmds.objectType(selected_item) == "blendShape":
            mesh = find_deformed_mesh(selected_item)
        elif maya_utilities.check_object_is_mesh(selected_item):
            mesh = selected_item
        else:
            mesh = None

        if mesh is not None:
            mesh_path = cmds.ls(mesh, long=True)[0]
            if mesh_path not in selected_meshes:
                selected_meshes.append(mesh_path)

    if not selected_meshes:
        raise RuntimeError("Select one or more meshes, or a blendshape node.")
    return selected_meshes


def check_wrapped_proxies(wrap_to_mesh, meshes_to_wrap):
    """Finds what would stop Create Wrapped Proxies, and what the user should know first. Changes nothing.

    wrap_to_mesh is None when no mesh is picked yet.
    """
    problems = []
    if wrap_to_mesh is None:
        problems.append("Pick the mesh to wrap to.")
    else:
        wrap_to_problem = _check_mesh_can_be_used(wrap_to_mesh)
        if wrap_to_problem is not None:
            problems.append(wrap_to_problem)
        elif not _check_transform_is_frozen(wrap_to_mesh):
            problems.append(
                f"{get_short_name(wrap_to_mesh)} is moved, rotated or scaled, and Proximity Wrap would put "
                "the proxies off by that much. Freeze its transformations first."
            )
    if not meshes_to_wrap:
        problems.append("Pick one or more meshes to wrap.")
    for mesh in meshes_to_wrap:
        mesh_problem = _check_mesh_can_be_used(mesh)
        if mesh_problem is not None:
            problems.append(mesh_problem)
        if mesh == wrap_to_mesh:
            problems.append(
                f"{get_short_name(mesh)} is the mesh to wrap to, so it can't follow itself. "
                "Remove it from Meshes to Wrap."
            )
    if problems:
        return WrappedProxiesCheck(problems=tuple(problems), warnings=(), targets_that_are_on=())

    warnings = []
    target_warning = _check_wrap_to_mesh_has_targets(wrap_to_mesh)
    if target_warning is not None:
        warnings.append(target_warning)
    targets_that_are_on = find_targets_that_are_on([wrap_to_mesh] + meshes_to_wrap)
    if targets_that_are_on:
        target_texts = []
        for target in targets_that_are_on:
            target_texts.append(f"{target.node}.{target.target_name} {target.weight:.2f}")
        warnings.append(
            f"Not at 0, so the proxies start from this shape: {', '.join(target_texts)}. "
            "Set Sliders to 0 turns them off."
        )
    return WrappedProxiesCheck(
        problems=(), warnings=tuple(warnings), targets_that_are_on=tuple(targets_that_are_on)
    )


def _check_mesh_can_be_used(mesh):
    """Returns why the mesh can't be wrapped or wrapped to, or None if it can."""
    if not cmds.objExists(mesh):
        return f"{get_short_name(mesh)} is not in the scene anymore."
    if not maya_utilities.check_object_is_mesh(mesh):
        return f"{get_short_name(mesh)} is not a mesh."
    return None


def _check_transform_is_frozen(mesh):
    """Returns True if the mesh and its parents aren't moved, rotated or scaled."""
    # worldSpace includes the parents, so a body inside a moved group counts as moved
    matrix = cmds.xform(mesh, query=True, matrix=True, worldSpace=True)
    for position, value in enumerate(matrix):
        if abs(value - IDENTITY_MATRIX[position]) > FROZEN_TRANSFORM_TOLERANCE:
            return False
    return True


def _check_wrap_to_mesh_has_targets(wrap_to_mesh):
    """Returns a warning if the mesh has no sculpted targets to test the proxies with, or None if it has."""
    mesh_name = get_short_name(wrap_to_mesh)
    nodes = maya_utilities.find_blend_shape_nodes(wrap_to_mesh)
    if not nodes:
        return f"{mesh_name} has no blendshape node, so there are no sliders to test the proxies with."

    target_count = 0
    empty_target_count = 0
    for node in nodes:
        target_count += len(get_target_names(node))
        empty_target_count += len(find_empty_targets(node))
    if target_count == 0:
        return f"{mesh_name}'s blendshape node has no targets, so there are no sliders to test the proxies with."
    if empty_target_count == target_count:
        return f"Every target on {mesh_name} is empty, so moving its sliders won't move the proxies."
    return None


def find_targets_that_are_on(meshes):
    """Returns every target that isn't at 0 on the meshes' blendshape nodes."""
    nodes = []
    for mesh in meshes:
        for node in maya_utilities.find_blend_shape_nodes(mesh):
            # two meshes can share history, so each node is read once
            if node not in nodes:
                nodes.append(node)

    targets_that_are_on = []
    for node in nodes:
        targets_that_are_on.extend(_find_targets_that_are_on(node, except_target_name=None))
    return targets_that_are_on


def set_sliders_to_zero(meshes):
    """Sets every target on the meshes to 0, in one undo step. Raises if one is keyed, connected or locked."""
    for mesh in meshes:
        if not cmds.objExists(mesh):
            raise RuntimeError(f"{get_short_name(mesh)} is not in the scene anymore. Nothing was changed.")
    targets_that_are_on = find_targets_that_are_on(meshes)
    for target in targets_that_are_on:
        if not cmds.getAttr(f"{target.node}.{target.target_name}", settable=True):
            raise RuntimeError(
                f"{target.target_name} on {target.node} is keyed, connected or locked, so it can't be set to 0. "
                "Nothing was changed."
            )

    cmds.undoInfo(openChunk=True, chunkName="Set Sliders to 0")
    try:
        for target in targets_that_are_on:
            set_target_weight(target.node, target.target_name, 0.0)
    finally:
        cmds.undoInfo(closeChunk=True)


def create_wrapped_proxies(wrap_to_mesh, meshes_to_wrap):
    """Copies the meshes without skin or history and wraps each copy to wrap_to_mesh. One undo step.

    Returns the new group. The real meshes don't change.
    """
    # check again here, so a check from before an Undo or a delete can never be used
    check = check_wrapped_proxies(wrap_to_mesh, meshes_to_wrap)
    if check.problems:
        raise RuntimeError(check.problems[0])
    group_name = _find_free_proxy_group_name(get_short_name(wrap_to_mesh) + PROXY_GROUP_NAME_ENDING)
    # the shape the viewport shows, not the hidden Orig shape a skinned mesh also has
    driver_shape = cmds.listRelatives(wrap_to_mesh, shapes=True, noIntermediate=True, fullPath=True)[0]

    cmds.undoInfo(openChunk=True, chunkName="Create Wrapped Proxies")
    try:
        group = cmds.ls(cmds.group(empty=True, name=group_name), long=True)[0]
        for mesh in meshes_to_wrap:
            proxy = _create_proxy(mesh, group)
            wrap_node = cmds.deformer(proxy, type="proximityWrap", name=get_short_name(proxy) + "_ProximityWrap")[0]
            cmds.proximityWrap(wrap_node, edit=True, addDrivers=[driver_shape])
    finally:
        cmds.undoInfo(closeChunk=True)
    return group


def _find_free_proxy_group_name(base_name):
    """Returns base_name if it's free, otherwise base_name_02, _03 and on."""
    if not cmds.objExists(base_name):
        return base_name
    for number in range(2, PROXY_GROUP_COUNT_MAX + 1):
        group_name = f"{base_name}_{number:02d}"
        if not cmds.objExists(group_name):
            return group_name
    raise RuntimeError(
        f"{base_name} and {base_name}_02 to _{PROXY_GROUP_COUNT_MAX} all exist. Delete the proxy groups you don't need."
    )


def _create_proxy(mesh, group):
    """Returns a copy of the mesh as it looks right now, without skin or history, inside the group."""
    # duplicate copies the shape as it looks now; the skinCluster and the rest of the history stay behind
    proxy = cmds.duplicate(mesh)[0]
    for shape in cmds.listRelatives(proxy, shapes=True, fullPath=True) or []:
        # the hidden Orig shape a skinned mesh keeps comes along too; nothing uses it on the proxy
        if cmds.getAttr(f"{shape}.intermediateObject"):
            cmds.delete(shape)

    # the copy keeps the rig's locked transformations and when parenting into the proxy group or freezing
    # and maya can't change locked ones so unlock them first
    for attribute in TRANSFORM_ATTRIBUTES:
        cmds.setAttr(f"{proxy}.{attribute}", lock=False)

    proxy = cmds.parent(proxy, group)[0]
    # renamed after parenting, so a proxy with the same name in an older group doesn't push a number on the end
    proxy = cmds.rename(cmds.ls(proxy, long=True)[0], get_short_name(mesh) + PROXY_NAME_ENDING)
    proxy = cmds.ls(proxy, long=True)[0]

    # Proximity Wrap reads the proxy's rest shape without its move, rotate and scale, so a moved proxy
    # would jump. Freezing puts them into the points, where the wrap sees them.
    cmds.makeIdentity(proxy, apply=True, translate=True, rotate=True, scale=True)

    # a message connection points at the real mesh and follows it through renames and moves,
    # so Add Proxy as Target knows where the shape goes. A copy of a proxy already has the attribute.
    if not cmds.attributeQuery(PROXY_SOURCE_ATTRIBUTE, node=proxy, exists=True):
        cmds.addAttr(proxy, longName=PROXY_SOURCE_ATTRIBUTE, attributeType="message")
    cmds.connectAttr(f"{mesh}.message", f"{proxy}.{PROXY_SOURCE_ATTRIBUTE}", force=True)
    return proxy


def get_selected_proxies():
    """Returns the selected proxies. Raises if none are selected, or a selected mesh isn't one."""
    proxies = []
    for selected_item in cmds.ls(selection=True, long=True):
        if maya_utilities.check_object_is_mesh(selected_item):
            if not cmds.attributeQuery(PROXY_SOURCE_ATTRIBUTE, node=selected_item, exists=True):
                raise RuntimeError(
                    f"{get_short_name(selected_item)} is not a proxy made by Create Wrapped Proxies, "
                    "or it was made before Add Proxy as Target existed. Make it again with Create Wrapped Proxies."
                )
            proxies.append(selected_item)

    if not proxies:
        raise RuntimeError("Select one or more proxies made by Create Wrapped Proxies.")
    return proxies


def find_proxy_source_mesh(proxy):
    """Returns the full path of the mesh the proxy was copied from, or None if that mesh is gone."""
    source_meshes = cmds.listConnections(
        f"{proxy}.{PROXY_SOURCE_ATTRIBUTE}", source=True, destination=False
    ) or []
    if not source_meshes:
        return None
    return cmds.ls(source_meshes[0], long=True)[0]


def find_proxy_wrap_to_meshes(proxies):
    """Returns the meshes the proxies follow through their Proximity Wraps, each once, as full paths."""
    wrap_to_meshes = []
    for proxy in proxies:
        for driver in _find_proximity_wrap_drivers(proxy):
            if driver not in wrap_to_meshes:
                wrap_to_meshes.append(driver)
    return wrap_to_meshes


# it takes a mesh and it returns a list of strings
def _find_proximity_wrap_drivers(mesh):
    # pruneDagObjects stops at the body, so a wrap further up the body's own history isn't counted
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    drivers = []
    for wrap_node in cmds.ls(history, type="proximityWrap"):
        # Create Wrapped Proxies gives each wrap one driver, at index 0
        driver_meshes = cmds.listConnections(
            f"{wrap_node}.drivers[0].driverGeometry", source=True, destination=False
        ) or []
        for driver_mesh in driver_meshes:
            drivers.append(cmds.ls(driver_mesh, long=True)[0])
    return drivers


def list_proxy_mesh_target_names(proxies):
    """Returns the target names already on the proxies' meshes, each once, so one can be picked to replace."""
    nodes = []
    for proxy in proxies:
        mesh = find_proxy_source_mesh(proxy)
        # a missing mesh has nothing to list; the check says it's missing
        if mesh is not None:
            nodes.extend(maya_utilities.find_blend_shape_nodes(mesh))

    target_names = []
    for node in nodes:
        for target_name in get_target_names(node):
            if target_name not in target_names:
                target_names.append(target_name)
    return target_names


def suggest_proxy_target_name(targets_that_are_on):
    """Returns the name of the slider that is on the most, or "" when none is on or two share the highest value.

    The proxies show the shape of the body's sliders, so the one that is on the most names the target.
    """
    highest_weight = 0.0
    highest_names = []
    for target in targets_that_are_on:
        if target.weight > highest_weight:
            highest_weight = target.weight
            highest_names = [target.target_name]
        elif target.weight == highest_weight:
            highest_names.append(target.target_name)

    if len(highest_names) != 1:
        return ""
    return highest_names[0]


def check_proxies_as_target(proxies, target_name):
    """Finds what would stop Add Proxy as Target, and what the user should know first. Changes nothing."""
    problems = []
    if not target_name:
        problems.append("Type a name for the target, or pick one to replace.")
    elif not maya_utilities.check_is_valid_maya_name(target_name):
        problems.append(
            f"'{target_name}' is not a valid Maya name. "
            "Use only letters, numbers and _, and do not start with a number."
        )

    source_meshes = []
    meshes_with_target = []
    meshes_without_target = []
    for proxy in proxies:
        proxy_problem = _check_proxy_can_be_added(proxy, target_name)
        if proxy_problem is not None:
            problems.append(proxy_problem)
        else:
            mesh = find_proxy_source_mesh(proxy)
            if mesh in source_meshes:
                problems.append(f"Two of the selected proxies belong to {get_short_name(mesh)}. Select only one.")
            source_meshes.append(mesh)
            node = maya_utilities.find_blend_shape_nodes(mesh)[0]
            if target_name in get_target_names(node):
                meshes_with_target.append(mesh)
            else:
                meshes_without_target.append(mesh)

    warnings = []
    if meshes_with_target and target_name:
        mesh_names = []
        for mesh in meshes_with_target:
            mesh_names.append(get_short_name(mesh))
        warnings.append(f"Replaces {target_name} on {', '.join(mesh_names)}.")
    existing_proxies = []
    for proxy in proxies:
        if cmds.objExists(proxy):
            existing_proxies.append(proxy)
    warnings.extend(_find_body_slider_warnings(existing_proxies, target_name))
    return ProxyTargetCheck(
        problems=tuple(problems),
        warnings=tuple(warnings),
        meshes_with_target=tuple(meshes_with_target),
        meshes_without_target=tuple(meshes_without_target),
    )


def _check_proxy_can_be_added(proxy, target_name):
    """Returns why this proxy's shape can't go onto its mesh, or None if it can."""
    proxy_name = get_short_name(proxy)
    if not cmds.objExists(proxy):
        return f"{proxy_name} is not in the scene anymore."
    mesh = find_proxy_source_mesh(proxy)
    if mesh is None:
        return f"The mesh {proxy_name} was copied from is not in the scene anymore."

    mesh_name = get_short_name(mesh)
    nodes = maya_utilities.find_blend_shape_nodes(mesh)
    if not nodes:
        return f"{mesh_name} has no blendshape node. Add one first, with Templates or the Shape Editor."
    if len(nodes) > 1:
        return f"{mesh_name} has more than one blendshape node ({', '.join(nodes)}), so BSM can't tell which one to use."
    if cmds.polyEvaluate(proxy, vertex=True) != cmds.polyEvaluate(mesh, vertex=True):
        return f"{proxy_name} and {mesh_name} don't have the same number of vertices anymore."

    if target_name in get_target_names(nodes[0]):
        index = _find_target_index(nodes[0], target_name)
        live_meshes = cmds.listConnections(
            f"{nodes[0]}.inputTarget[0].inputTargetGroup[{index}].inputTargetItem[{FULL_TARGET_ITEM}].inputGeomTarget"
        ) or []
        if live_meshes:
            return f"{target_name} on {mesh_name} is still connected to the mesh {live_meshes[0]}. Delete that mesh first."
    return None


def _find_body_slider_warnings(proxies, target_name):
    """Warns when the proxies show no body slider at all, or more than one mixed together."""
    wrap_to_meshes = find_proxy_wrap_to_meshes(proxies)
    if not wrap_to_meshes:
        # the wraps were deleted, so there is no body to read; the proxies keep the shape they have
        return []

    targets_that_are_on = find_targets_that_are_on(wrap_to_meshes)
    if not targets_that_are_on:
        wrap_to_names = []
        for mesh in wrap_to_meshes:
            wrap_to_names.append(get_short_name(mesh))
        return [
            f"No slider on {', '.join(wrap_to_names)} is on, so the proxies show the rest shape "
            "and the target won't move anything."
        ]
    if len(targets_that_are_on) == 1:
        return []

    other_texts = []
    for target in targets_that_are_on:
        if target.target_name != target_name:
            other_texts.append(f"{target.target_name} {target.weight:.2f}")
    if not target_name:
        return [f"More than one slider is on, so the target mixes their shapes: {', '.join(other_texts)}."]
    return [f"Other sliders are on too, so their shape becomes part of {target_name}: {', '.join(other_texts)}."]


def add_proxies_as_target(proxies, target_name):
    """Saves each proxy's shape as a target on its real mesh, then hides the proxy. One undo step.

    A target with the same name is replaced in place.
    """
    # check again here, so a check from before an Undo or a delete can never be used
    check = check_proxies_as_target(proxies, target_name)
    if check.problems:
        raise RuntimeError(check.problems[0])

    cmds.undoInfo(openChunk=True, chunkName="Add Proxy as Target")
    try:
        for proxy in proxies:
            mesh = find_proxy_source_mesh(proxy)
            node = maya_utilities.find_blend_shape_nodes(mesh)[0]
            point_moves = _measure_proxy_point_moves(proxy, mesh, node)
            if target_name in get_target_names(node):
                index = _find_target_index(node, target_name)
            else:
                index = _find_next_target_index(node)
                _add_empty_targets(node, mesh, (target_name,), index)
            _write_point_moves(node, index, FULL_TARGET_ITEM, point_moves)
            # the shape is on the real mesh now, so the proxy is hidden; it stays for the next slider
            cmds.setAttr(f"{proxy}.visibility", False)
    finally:
        cmds.undoInfo(closeChunk=True)


def _measure_proxy_point_moves(proxy, mesh, node):
    """Compares each proxy vertex with the same vertex going into the node: that difference is the target."""
    input_plug = cmds.listConnections(
        f"{node}.input[0].inputGeometry", source=True, destination=False, plugs=True
    )[0]
    points_in = _read_points_of_plug(input_plug)
    proxy_points = _read_proxy_points_in_mesh_space(proxy, mesh)

    point_moves = []
    for vertex_index, point_in in enumerate(points_in):
        proxy_point = proxy_points[vertex_index]
        offset = (proxy_point[0] - point_in[0], proxy_point[1] - point_in[1], proxy_point[2] - point_in[2])
        if _check_point_has_moved(offset):
            point_moves.append(PointMove(vertex_index=vertex_index, offset=offset))
    return point_moves


def _read_proxy_points_in_mesh_space(proxy, mesh):
    """Returns the proxy's points the way the mesh stores its own: without the mesh's move, rotate and scale.

    A blendshape works in that space, so a T-shirt that was moved and never frozen still gets the right shape.
    """
    temporary_mesh = cmds.duplicate(proxy)[0]
    # parent keeps the copy where it is in the world, so the copy now holds the mesh's move, undone;
    # freezing puts that into the points, which are then in the mesh's own space
    temporary_mesh = cmds.ls(cmds.parent(temporary_mesh, mesh)[0], long=True)[0]
    cmds.makeIdentity(temporary_mesh, apply=True, translate=True, rotate=True, scale=True)
    flat_positions = cmds.xform(f"{temporary_mesh}.vtx[*]", query=True, translation=True, objectSpace=True)
    cmds.delete(temporary_mesh)

    # xform gives one long list, x y z x y z ..., so every 3 numbers are one point
    points = []
    for start in range(0, len(flat_positions), 3):
        points.append(flat_positions[start:start + 3])
    return points


def get_avatar_selection():
    """Returns the selected group's or meshes' meshes that have their own blendshape node.

    Meshes without one, like eyes or teeth, are left out.
    """
    # only for its "nothing selected" message, which every tool shares
    maya_utilities.get_user_object_selection()
    selected_objects = cmds.ls(selection=True, long=True)
    selected_meshes = []
    selected_groups = []
    for selected_object in selected_objects:
        if maya_utilities.check_object_is_mesh(selected_object):
            selected_meshes.append(selected_object)
        else:
            selected_groups.append(selected_object)

    if not selected_groups:
        meshes = selected_meshes
        group_name = None
    elif len(selected_objects) > 1:
        raise RuntimeError("Select the avatar's group, or one or more of its meshes.")
    else:
        meshes = find_meshes_in_group(selected_groups[0])
        group_name = get_short_name(selected_groups[0])
        if not meshes:
            raise RuntimeError(f"{group_name} has no meshes in it.")

    meshes_with_blend_shapes = []
    for mesh in meshes:
        if _find_own_blend_shape_nodes(mesh):
            meshes_with_blend_shapes.append(mesh)
    if not meshes_with_blend_shapes:
        raise RuntimeError("None of the selected meshes has a blendshape node.")
    return AvatarSelection(meshes=tuple(meshes_with_blend_shapes), group_name=group_name)


def _find_own_blend_shape_nodes(mesh):
    """Returns the blendshape nodes that deform the mesh itself.

    A mesh wrapped to the body also has the body's node in its history, but that one belongs to the body.
    """
    mesh_shape = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True)[0]
    own_nodes = []
    for node in maya_utilities.find_blend_shape_nodes(mesh):
        deformed_shapes = cmds.ls(cmds.blendShape(node, query=True, geometry=True) or [], long=True)
        if mesh_shape in deformed_shapes:
            own_nodes.append(node)
    return own_nodes


def find_global_targets(meshes):
    """Returns one GlobalTarget per target name on the meshes' blendshape nodes, sorted by name.

    Meshes and nodes deleted since they were loaded are skipped, so Refresh never fails on them.
    """
    targets_by_name = {}
    for target in _read_avatar_targets(meshes):
        if target.target_name not in targets_by_name:
            targets_by_name[target.target_name] = []
        targets_by_name[target.target_name].append(target)

    global_targets = []
    for target_name in sorted(targets_by_name):
        global_targets.append(GlobalTarget(target_name=target_name, targets=tuple(targets_by_name[target_name])))
    return global_targets


def _read_avatar_targets(meshes):
    targets = []
    read_nodes = []
    for mesh in meshes:
        if not cmds.objExists(mesh):
            continue
        for node in _find_own_blend_shape_nodes(mesh):
            # two meshes can share one node; its targets are read once
            if node in read_nodes:
                continue
            read_nodes.append(node)
            targets.extend(_read_node_targets(mesh, node))
    return targets


def _read_node_targets(mesh, node):
    # indices can have gaps where targets were deleted, so never count from 0
    indices = cmds.getAttr(f"{node}.weight", multiIndices=True) or []
    targets = []
    for index in indices:
        target_name = cmds.aliasAttr(f"{node}.weight[{index}]", query=True)
        # Maya gives "" or None for a target without a name; weight[3] on two nodes isn't a shared target
        if not target_name:
            continue
        weight_plug = f"{node}.weight[{index}]"
        # the plug the Shape Editor's visibility toggle sets
        visibility_plug = f"{node}.targetVisibility[{index}]"
        targets.append(
            AvatarTarget(
                target_name=target_name,
                mesh=mesh,
                node=node,
                index=index,
                weight=cmds.getAttr(weight_plug),
                is_visible=cmds.getAttr(visibility_plug),
                can_set_weight=cmds.getAttr(weight_plug, settable=True),
                can_set_visibility=cmds.getAttr(visibility_plug, settable=True),
            )
        )
    return targets


def set_global_weight(global_target, weight):
    """Sets the weight on every target in the row, in one undo step. Keyed, connected or locked ones are skipped.

    Inside a slider drag, the window's own undo step holds every one of these, so the whole drag is one Ctrl+Z.
    """
    cmds.undoInfo(openChunk=True, chunkName=f"Set {global_target.target_name} Weight")
    try:
        for target in global_target.targets:
            if target.can_set_weight:
                cmds.setAttr(f"{target.node}.weight[{target.index}]", weight)
    finally:
        cmds.undoInfo(closeChunk=True)


def set_global_visibility(global_target, visible):
    """Shows or hides every target in the row, like the Shape Editor's toggle, in one undo step.

    The weights stay as they are. Keyed, connected or locked ones are skipped.
    """
    cmds.undoInfo(openChunk=True, chunkName=f"Set {global_target.target_name} Visibility")
    try:
        for target in global_target.targets:
            if target.can_set_visibility:
                cmds.setAttr(f"{target.node}.targetVisibility[{target.index}]", visible)
    finally:
        cmds.undoInfo(closeChunk=True)


def find_shared_value(global_target):
    """Returns the weight and visibility most of the row's targets have, and whether they differ.

    Weights are compared to 3 decimals, as the window shows them. On a tie, the first target wins.
    """
    weights = []
    visibilities = []
    for target in global_target.targets:
        weights.append(round(target.weight, WEIGHT_DECIMALS))
        visibilities.append(target.is_visible)

    weight, is_weight_mixed = _find_most_common(weights)
    is_visible, is_visibility_mixed = _find_most_common(visibilities)
    return SharedValue(
        weight=weight,
        is_weight_mixed=is_weight_mixed,
        is_visible=is_visible,
        is_visibility_mixed=is_visibility_mixed,
    )


def _find_most_common(values):
    """Returns the value that comes up most often (the first one on a tie), and whether the values differ at all."""
    counts = {}
    for value in values:
        if value not in counts:
            counts[value] = 0
        counts[value] += 1

    most_common = values[0]
    for value in values:
        # only a higher count replaces it, so on a tie the first value stays
        if counts[value] > counts[most_common]:
            most_common = value
    return most_common, len(counts) > 1


def find_targets_that_cannot_be_set(global_target):
    """Returns the row's targets whose weight or visibility is keyed, connected or locked, for the "2 of 3" mark."""
    skipped_targets = []
    for target in global_target.targets:
        if not target.can_set_weight:
            skipped_targets.append(target)
        elif not target.can_set_visibility:
            skipped_targets.append(target)
    return skipped_targets
