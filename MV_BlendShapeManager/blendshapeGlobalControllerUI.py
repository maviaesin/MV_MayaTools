from importlib import reload

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from MV_BlendShapeManager import blendshapeToolkitCore
from MV_UtilityScripts.Qt import QtCore, QtGui, QtWidgets

reload(blendshapeToolkitCore)

WINDOW_OBJECT_NAME = "MV_GlobalShapeController"
# Maya docks the window inside a workspace control with this name
WORKSPACE_CONTROL_NAME = WINDOW_OBJECT_NAME + "WorkspaceControl"
VISIBILITY_COLUMN = 0
NAME_COLUMN = 1
WEIGHT_COLUMN = 2
ONLY_ON_ONE_MESH_TEXT = "Only on one mesh"
AVATAR_ICON = ":/out_transform.png"
# bigger icons make Maya draw the fold arrows bigger too
ROW_ICON_SIZE = 16
# set on the Weight column; set on Name, it squeezed the names away
ROW_HEIGHT = 28
# white: shown, empty: hidden, grey: some shown and some hidden
VISIBILITY_DOT_STYLE = (
    "QCheckBox::indicator { width: 10px; height: 10px; border-radius: 6px; border: 1px solid #c8c8c8; }"
    "QCheckBox::indicator:checked { background: #ffffff; }"
    "QCheckBox::indicator:indeterminate { background: #707070; }"
)
REFRESH_EVENTS = ("Undo", "Redo")
# a QSlider only has whole steps, so 1000 steps give 3 decimals
WEIGHT_SLIDER_STEPS = 1000
# Maya's own limits for a target weight
WEIGHT_TYPED_MIN = -10.0
WEIGHT_TYPED_MAX = 10.0
WEIGHT_FIELD_WIDTH = 55
WEIGHT_ROW_LEFT_GAP = 10
VISIBILITY_ICON = ":/visible.png"
# Qt draws a header icon at the left, so a narrow column is what centres the eye
VISIBILITY_COLUMN_WIDTH = 22
WEIGHT_SLIDER_WIDTH = 180
MARKER_COLOR = "grey"
WEIGHT_SLIDER_STYLE = (
    "QSlider::groove:horizontal { height: 4px; background: #1d1d1d; border-radius: 2px; }"
    "QSlider::sub-page:horizontal { background: #5285a6; border-radius: 2px; }"
    "QSlider::handle:horizontal { width: 6px; margin: -5px 0px; background: #c8c8c8; border-radius: 1px; }"
)


def build_mesh_count_text(mesh_count):
    if mesh_count == 1:
        return "1 mesh"
    return f"{mesh_count} meshes"


def build_avatar_label(group_name, mesh_count):
    """Returns "FemaleA · 3 meshes", or "3 meshes" when meshes were selected instead of a group."""
    mesh_count_text = build_mesh_count_text(mesh_count)
    if group_name is None:
        return mesh_count_text
    return f"{group_name} · {mesh_count_text}"


def find_target_meshes(global_target):
    """Returns the meshes a row reaches. A mesh with two nodes that have the name counts once."""
    meshes = []
    for target in global_target.targets:
        if target.mesh not in meshes:
            meshes.append(target.mesh)
    return meshes


def find_avatar_meshes(global_targets):
    meshes = []
    for global_target in global_targets:
        for mesh in find_target_meshes(global_target):
            if mesh not in meshes:
                meshes.append(mesh)
    return meshes


def build_target_tooltip(global_target):
    """One line per target, as "Mesh (node)"."""
    lines = []
    for target in global_target.targets:
        lines.append(f"{blendshapeToolkitCore.get_short_name(target.mesh)} ({target.node})")
    return "\n".join(lines)


def build_marker_label(text, tooltip):
    marker_label = QtWidgets.QLabel(text)
    marker_label.setStyleSheet(f"color: {MARKER_COLOR};")
    marker_label.setToolTip(tooltip)
    return marker_label


# the mixin comes first, so its show() can dock the window
class GlobalShapeControllerUI(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Global Shape Controller")
        self.setObjectName(WINDOW_OBJECT_NAME)
        # in the same order as the dropdown
        self.avatars = []
        self.script_job_ids = []

        self.buildUI()

    def start_refresh_after_undo(self):
        """Starts the scriptJobs that refresh the list after Undo and Redo.

        Call it after show(): the jobs belong to the workspace control, which only exists from then on.
        """
        for event_name in REFRESH_EVENTS:
            job_id = cmds.scriptJob(event=[event_name, self.refresh], parent=WORKSPACE_CONTROL_NAME)
            self.script_job_ids.append(job_id)

    def _stop_script_jobs(self):
        for job_id in self.script_job_ids:
            # Maya may have deleted it already, with the workspace control
            if cmds.scriptJob(exists=job_id):
                cmds.scriptJob(kill=job_id)
        self.script_job_ids = []

    def dockCloseEventTriggered(self):
        # called when the docked window closes
        self._stop_script_jobs()

    def closeEvent(self, event):
        # called when the floating window closes
        self._stop_script_jobs()
        super().closeEvent(event)

    def buildUI(self):
        layout = QtWidgets.QVBoxLayout(self)

        avatar_row = QtWidgets.QHBoxLayout()
        avatar_row.addWidget(QtWidgets.QLabel("Avatar:"))
        self.avatar_combo = QtWidgets.QComboBox()
        self.avatar_combo.setToolTip("Avatars loaded with Load Selected.")
        self.avatar_combo.currentIndexChanged.connect(self.handle_avatar_changed)
        avatar_row.addWidget(self.avatar_combo, 1)

        load_button = QtWidgets.QPushButton("Load Selected")
        load_button.setToolTip("Load the selected avatar group, or some of its meshes.")
        load_button.clicked.connect(self.handle_load_selected)
        avatar_row.addWidget(load_button)

        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.setToolTip("Read the targets again, for example after changes in the Shape Editor.")
        refresh_button.clicked.connect(self.handle_refresh)
        avatar_row.addWidget(refresh_button)
        layout.addLayout(avatar_row)

        self.target_tree = QtWidgets.QTreeWidget()
        self.target_tree.setColumnCount(3)
        self.target_tree.setHeaderLabels(["", "Name", "Weight"])
        self.target_tree.headerItem().setIcon(VISIBILITY_COLUMN, QtGui.QIcon(VISIBILITY_ICON))
        self.target_tree.headerItem().setToolTip(VISIBILITY_COLUMN, "Visibility")
        self.target_tree.header().setSectionResizeMode(VISIBILITY_COLUMN, QtWidgets.QHeaderView.Fixed)
        self.target_tree.setColumnWidth(VISIBILITY_COLUMN, VISIBILITY_COLUMN_WIDTH)
        self.target_tree.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.target_tree.setIconSize(QtCore.QSize(ROW_ICON_SIZE, ROW_ICON_SIZE))
        # fold arrows next to the names, not in the first column with the dots
        self.target_tree.setTreePosition(NAME_COLUMN)
        self.target_tree.header().setSectionResizeMode(NAME_COLUMN, QtWidgets.QHeaderView.ResizeToContents)
        self.target_tree.header().setDefaultAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.target_tree)

    def refresh(self):
        """Reads the picked avatar's targets from the scene and rebuilds the list."""
        self.target_tree.clear()
        index = self.avatar_combo.currentIndex()
        # nothing loaded yet
        if index == -1:
            return

        avatar = self.avatars[index]
        global_targets = blendshapeToolkitCore.find_global_targets(list(avatar.meshes))
        avatar_mesh_count = len(find_avatar_meshes(global_targets))

        avatar_item = QtWidgets.QTreeWidgetItem(["", build_avatar_label(avatar.group_name, avatar_mesh_count)])
        avatar_item.setIcon(NAME_COLUMN, QtGui.QIcon(AVATAR_ICON))
        avatar_font = avatar_item.font(NAME_COLUMN)
        avatar_font.setBold(True)
        avatar_item.setFont(NAME_COLUMN, avatar_font)
        avatar_item.setSizeHint(WEIGHT_COLUMN, QtCore.QSize(0, ROW_HEIGHT))
        self.target_tree.addTopLevelItem(avatar_item)
        only_on_one_mesh_item = QtWidgets.QTreeWidgetItem(["", ONLY_ON_ONE_MESH_TEXT])
        only_on_one_mesh_item.setSizeHint(WEIGHT_COLUMN, QtCore.QSize(0, ROW_HEIGHT))

        target_items = []
        for global_target in global_targets:
            target_item = self._build_target_item(global_target)
            target_items.append(target_item)
            if len(global_target.targets) > 1:
                self._show_missing_meshes(target_item, global_target, avatar_mesh_count)
                avatar_item.addChild(target_item)
            else:
                only_on_one_mesh_item.addChild(target_item)

        if only_on_one_mesh_item.childCount() > 0:
            avatar_item.addChild(only_on_one_mesh_item)
        # these only work once the rows are in the tree
        avatar_item.setExpanded(True)
        only_on_one_mesh_item.setExpanded(False)
        for position, global_target in enumerate(global_targets):
            shared_value = blendshapeToolkitCore.find_shared_value(global_target)
            visibility_box = self._build_visibility_box(global_target, shared_value)
            self.target_tree.setItemWidget(target_items[position], VISIBILITY_COLUMN, visibility_box)
            weight_row = self._build_weight_row(global_target, shared_value)
            self.target_tree.setItemWidget(target_items[position], WEIGHT_COLUMN, weight_row)

    def _build_target_item(self, global_target):
        target_item = QtWidgets.QTreeWidgetItem(["", global_target.target_name])
        target_item.setToolTip(NAME_COLUMN, build_target_tooltip(global_target))
        target_item.setSizeHint(WEIGHT_COLUMN, QtCore.QSize(0, ROW_HEIGHT))
        return target_item

    def _build_visibility_box(self, global_target, shared_value):
        box_holder = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(box_holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        visibility_box = QtWidgets.QCheckBox()
        visibility_box.setStyleSheet(VISIBILITY_DOT_STYLE)
        visibility_box.setToolTip("Show or hide this target on every mesh.")
        if shared_value.is_visibility_mixed:
            visibility_box.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            visibility_box.setChecked(shared_value.is_visible)
        # clicked only comes from the artist, not from setting the box above
        visibility_box.clicked.connect(
            lambda checked: self.handle_visibility_clicked(global_target, checked, visibility_box)
        )
        layout.addWidget(visibility_box)
        return box_holder

    def _show_missing_meshes(self, target_item, global_target, avatar_mesh_count):
        """Adds "4 of 6" after the name when some of the avatar's meshes don't have the target."""
        target_mesh_count = len(find_target_meshes(global_target))
        if target_mesh_count < avatar_mesh_count:
            target_item.setText(NAME_COLUMN, f"{global_target.target_name}   {target_mesh_count} of {avatar_mesh_count}")

    def _build_weight_row(self, global_target, shared_value):
        """The number field, the slider, and the "mixed" and "2 of 3" markers."""
        weight_row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(weight_row)
        layout.setContentsMargins(WEIGHT_ROW_LEFT_GAP, 0, 0, 0)

        weight_field = QtWidgets.QDoubleSpinBox()
        weight_field.setDecimals(blendshapeToolkitCore.WEIGHT_DECIMALS)
        weight_field.setRange(WEIGHT_TYPED_MIN, WEIGHT_TYPED_MAX)
        weight_field.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        # sets the weights on Enter, not on every typed character
        weight_field.setKeyboardTracking(False)
        weight_field.setFixedWidth(WEIGHT_FIELD_WIDTH)
        weight_field.setValue(shared_value.weight)
        layout.addWidget(weight_field)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(0, WEIGHT_SLIDER_STEPS)
        slider.setStyleSheet(WEIGHT_SLIDER_STYLE)
        slider.setValue(round(shared_value.weight * WEIGHT_SLIDER_STEPS))
        slider.setFixedWidth(WEIGHT_SLIDER_WIDTH)
        layout.addWidget(slider)

        mixed_label = build_marker_label("mixed", "These targets had different weights at the last Refresh.")
        mixed_label.setVisible(shared_value.is_weight_mixed)
        layout.addWidget(mixed_label)
        skipped_targets = blendshapeToolkitCore.find_targets_that_cannot_be_set(global_target)
        if skipped_targets:
            layout.addWidget(self._build_skipped_label(global_target, skipped_targets))
        layout.addStretch()

        slider.valueChanged.connect(
            lambda slider_value: self.handle_slider_moved(global_target, slider_value, weight_field, mixed_label)
        )
        slider.sliderPressed.connect(lambda: self.handle_slider_pressed(global_target.target_name))
        slider.sliderReleased.connect(self.handle_slider_released)
        weight_field.valueChanged.connect(
            lambda weight: self.handle_weight_typed(global_target, weight, slider, mixed_label)
        )
        return weight_row

    def _build_skipped_label(self, global_target, skipped_targets):
        """Returns "2 of 3": how many targets the row sets, with the skipped ones on hover."""
        lines = ["Skipped, because they're keyed, connected or locked:"]
        for target in skipped_targets:
            lines.append(f"{blendshapeToolkitCore.get_short_name(target.mesh)} ({target.node})")
        set_count = len(global_target.targets) - len(skipped_targets)
        return build_marker_label(f"{set_count} of {len(global_target.targets)}", "\n".join(lines))

    def handle_load_selected(self):
        try:
            avatar = blendshapeToolkitCore.get_avatar_selection()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        # so the dropdown doesn't refresh on every change; refresh runs once below
        self.avatar_combo.blockSignals(True)
        # an avatar that's already loaded is picked, not added twice
        if avatar in self.avatars:
            self.avatar_combo.setCurrentIndex(self.avatars.index(avatar))
        else:
            self.avatars.append(avatar)
            self.avatar_combo.addItem(build_avatar_label(avatar.group_name, len(avatar.meshes)))
            self.avatar_combo.setCurrentIndex(len(self.avatars) - 1)
        self.avatar_combo.blockSignals(False)
        self.refresh()

    def handle_avatar_changed(self, index):
        self.refresh()

    def handle_slider_moved(self, global_target, slider_value, weight_field, mixed_label):
        weight = slider_value / WEIGHT_SLIDER_STEPS
        try:
            blendshapeToolkitCore.set_global_weight(global_target, weight)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        # so the field doesn't set the weights a second time
        weight_field.blockSignals(True)
        weight_field.setValue(weight)
        weight_field.blockSignals(False)
        mixed_label.hide()

    def handle_weight_typed(self, global_target, weight, slider, mixed_label):
        try:
            blendshapeToolkitCore.set_global_weight(global_target, weight)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        slider.blockSignals(True)
        slider.setValue(round(weight * WEIGHT_SLIDER_STEPS))
        slider.blockSignals(False)
        mixed_label.hide()

    def handle_visibility_clicked(self, global_target, checked, visibility_box):
        # after a click every target is the same, so no more half tick
        visibility_box.setTristate(False)
        try:
            blendshapeToolkitCore.set_global_visibility(global_target, visible=checked)
        except RuntimeError as error:
            cmds.warning(str(error))

    def handle_slider_pressed(self, target_name):
        # the whole drag is one undo step, closed in handle_slider_released
        cmds.undoInfo(openChunk=True, chunkName=f"Drag {target_name}")

    def handle_slider_released(self):
        cmds.undoInfo(closeChunk=True)

    def handle_refresh(self):
        self.refresh()


def showUI():
    """Opens the Global Shape Controller, closing the old one first."""
    if cmds.workspaceControl(WORKSPACE_CONTROL_NAME, exists=True):
        cmds.deleteUI(WORKSPACE_CONTROL_NAME)

    ui = GlobalShapeControllerUI()
    # retain=False: Maya won't bring back an empty dock after a restart
    ui.show(dockable=True, retain=False)
    ui.start_refresh_after_undo()
    return ui
