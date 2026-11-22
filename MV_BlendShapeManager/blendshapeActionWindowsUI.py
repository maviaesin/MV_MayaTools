from importlib import reload

from maya import cmds

from MV_BlendShapeManager import blendshapeToolkitCore
from MV_BlendShapeManager.blendshapeTemplatesUI import (
    MESH_COLOR,
    PASS_COLOR,
    TEMPLATE_COLOR,
    build_check_line,
    color_text,
    get_maya_main_window,
)
from MV_UtilityScripts.Qt import QtCore, QtGui, QtWidgets

reload(blendshapeToolkitCore)

COPY_WEIGHTS_WINDOW_OBJECT_NAME = "MV_BlendShapeCopyWeights"
# Validate's colors: lilac for the source, blue for the destinations
DESTINATION_COLOR = MESH_COLOR
SOURCE_COLOR = TEMPLATE_COLOR
UNPAINTED_COLOR = "grey"
WARNING_COLOR = "#ffd166"
DIVIDER_TEXT = "──── no painting ────"

WRAPPED_PROXIES_WINDOW_OBJECT_NAME = "MV_BlendShapeWrappedProxies"
# Validate's colors: lilac for the mesh to follow, blue for the meshes that follow it
WRAP_TO_COLOR = TEMPLATE_COLOR
MESHES_TO_WRAP_COLOR = MESH_COLOR


def build_warning_line(text):
    return color_text(f"⚠ {text}", WARNING_COLOR)


def bold_text(text):
    return f"<b>{text}</b>"


def bold_target_names(message, target_names):
    """Makes the target names in a message bold."""
    words = []
    for word in message.split(" "):
        # names can sit next to punctuation, like "EyesClosed," or "'Frown'."
        name = word.strip(".,'")
        if name in target_names:
            word = word.replace(name, bold_text(name))
        words.append(word)
    return " ".join(words)


class BlendShapeCopyWeightsUI(QtWidgets.QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("MV_BlendShape_CopyWeights")
        self.setObjectName(COPY_WEIGHTS_WINDOW_OBJECT_NAME)
        self.resize(380, 460)
        # shown above the check when the Shape Editor has targets from several nodes
        self.selection_warning = ""

        self.buildUI()
        self.handle_use_shape_editor_selection()

    def buildUI(self):
        layout = QtWidgets.QVBoxLayout(self)

        node_row = QtWidgets.QHBoxLayout()
        node_row.addWidget(QtWidgets.QLabel("Node:"))
        self.node_combo = QtWidgets.QComboBox()
        self.node_combo.currentIndexChanged.connect(self.handle_node_changed)
        node_row.addWidget(self.node_combo, 1)
        use_selection_button = QtWidgets.QPushButton("Use Shape Editor Selection")
        use_selection_button.setToolTip(
            "Use the node selected in the Shape Editor."
        )
        use_selection_button.clicked.connect(self.handle_use_shape_editor_selection)
        node_row.addWidget(use_selection_button)
        layout.addLayout(node_row)

        columns = QtWidgets.QHBoxLayout()
        self.source_list = QtWidgets.QListWidget()
        self.source_list.itemSelectionChanged.connect(self.handle_picked_targets_changed)
        columns.addLayout(self._build_column("Copy from (select one)", SOURCE_COLOR, self.source_list))
        self.destination_list = QtWidgets.QListWidget()
        self.destination_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.destination_list.itemSelectionChanged.connect(self.handle_picked_targets_changed)
        columns.addLayout(self._build_column("Copy to (one or more)", DESTINATION_COLOR, self.destination_list))
        layout.addLayout(columns)

        self.copy_button = QtWidgets.QPushButton("Copy")
        self.copy_button.setToolTip(
            "Give the targets on the right the painted weights of the target on the left."
        )
        self.copy_button.clicked.connect(self.handle_copy)
        layout.addWidget(self.copy_button)

        self.results_label = QtWidgets.QLabel()
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)

    def _build_column(self, title, color, target_list):
        column = QtWidgets.QVBoxLayout()
        column.addWidget(QtWidgets.QLabel(color_text(title, color)))
        column.addWidget(target_list)
        return column

    def refresh(self):
        """Reloads the picked node's targets into both lists, and shows what Copy would do."""
        self.destination_list.clear()
        self.source_list.clear()
        node = self.node_combo.currentText()
        if node and cmds.objExists(node):
            target_names = blendshapeToolkitCore.get_target_names(node)
            painted_targets = blendshapeToolkitCore.find_painted_targets(node)
            self._fill_target_list(self.destination_list, target_names, painted_targets, DESTINATION_COLOR)
            self._fill_target_list(self.source_list, target_names, painted_targets, SOURCE_COLOR)
        self._show_check()

    def _fill_target_list(self, target_list, target_names, painted_targets, color):
        """Painted targets first, then a line, then the targets with no painting, in grey."""
        unpainted_names = []
        for target_name in target_names:
            if target_name in painted_targets:
                self._add_target_item(target_list, target_name, color)
            else:
                unpainted_names.append(target_name)

        if painted_targets and unpainted_names:
            divider = QtWidgets.QListWidgetItem(DIVIDER_TEXT)
            # the line can't be picked, so it's never read as a target
            divider.setFlags(QtCore.Qt.NoItemFlags)
            divider.setForeground(QtGui.QColor(UNPAINTED_COLOR))
            target_list.addItem(divider)
        for target_name in unpainted_names:
            self._add_target_item(target_list, target_name, UNPAINTED_COLOR)

    def _add_target_item(self, target_list, target_name, color):
        item = QtWidgets.QListWidgetItem(target_name)
        item.setForeground(QtGui.QColor(color))
        target_list.addItem(item)

    def _get_picked_source(self):
        selected_items = self.source_list.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].text()

    def _get_picked_destinations(self):
        destination_names = []
        for item in self.destination_list.selectedItems():
            destination_names.append(item.text())
        return destination_names

    def _show_check(self, done_line=""):
        """Shows what stops Copy in red, what to know first in yellow, and turns Copy on only when it can run."""
        lines = []
        if done_line:
            lines.append(done_line)
        if self.selection_warning:
            lines.append(build_warning_line(self.selection_warning))

        node = self.node_combo.currentText()
        if not node:
            lines.append(build_check_line("There is no blendshape node in the scene.", passed=False))
            self.results_label.setText("<br>".join(lines))
            self.copy_button.setEnabled(False)
            return

        source = self._get_picked_source()
        destinations = self._get_picked_destinations()
        check = blendshapeToolkitCore.check_copy_weights(node, source, destinations)
        target_names = []
        if cmds.objExists(node):
            target_names = blendshapeToolkitCore.get_target_names(node)
        for problem in check.problems:
            lines.append(build_check_line(bold_target_names(problem, target_names), passed=False))
        for warning in check.warnings:
            lines.append(build_warning_line(bold_target_names(warning, target_names)))
        if not check.problems:
            source_name = color_text(bold_text(source), SOURCE_COLOR)
            destination_names = color_text(bold_text(", ".join(destinations)), DESTINATION_COLOR)
            ready_text = f"Ready to copy {source_name}'s painted weights to {destination_names}"
            lines.append(color_text(f"✔ {ready_text}", PASS_COLOR))

        self.results_label.setText("<br>".join(lines))
        self.copy_button.setEnabled(not check.problems)

    def handle_use_shape_editor_selection(self):
        try:
            shape_editor_nodes = blendshapeToolkitCore.find_shape_editor_nodes()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        self.selection_warning = ""
        if len(shape_editor_nodes) > 1:
            self.selection_warning = (
                f"The Shape Editor has more than one node selected ({', '.join(shape_editor_nodes)}). "
                f"Showing {shape_editor_nodes[0]}; pick another one above."
            )

        all_nodes = blendshapeToolkitCore.list_blend_shape_nodes()
        # so filling the dropdown doesn't refresh once per node
        self.node_combo.blockSignals(True)
        self.node_combo.clear()
        self.node_combo.addItems(all_nodes)
        if shape_editor_nodes:
            self.node_combo.setCurrentIndex(all_nodes.index(shape_editor_nodes[0]))
        self.node_combo.blockSignals(False)
        self.refresh()

    def handle_node_changed(self, index):
        # a node picked by hand replaces what the Shape Editor had, so its warning no longer fits
        self.selection_warning = ""
        self.refresh()

    def handle_picked_targets_changed(self):
        self._show_check()

    def handle_copy(self):
        node = self.node_combo.currentText()
        source = self._get_picked_source()
        destinations = self._get_picked_destinations()

        answer = QtWidgets.QMessageBox.question(
            self,
            "Copy Weights",
            f"{source}'s painted weights will replace the painted weights of {', '.join(destinations)}.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
        )
        if answer != QtWidgets.QMessageBox.Ok:
            return

        try:
            blendshapeToolkitCore.copy_painted_weights(node, source, destinations)
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        # the copied targets are painted now, so their colors change
        self.refresh()
        for item in self.source_list.findItems(source, QtCore.Qt.MatchExactly):
            item.setSelected(True)
        done_text = f"Copied {bold_text(source)}'s painted weights to {bold_text(', '.join(destinations))}"
        self._show_check(done_line=build_check_line(done_text, passed=True))


class BlendShapeWrappedProxiesUI(QtWidgets.QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("MV_BlendShape_CreateWrappedProxies")
        self.setObjectName(WRAPPED_PROXIES_WINDOW_OBJECT_NAME)
        self.resize(420, 380)
        # full paths; the lists below only show the short names
        self.wrap_to_mesh = None
        self.meshes_to_wrap = []

        self.buildUI()
        self.handle_use_selection()

    def buildUI(self):
        layout = QtWidgets.QVBoxLayout(self)

        columns = QtWidgets.QHBoxLayout()
        columns.addLayout(self._build_wrap_to_column())
        columns.addLayout(self._build_meshes_to_wrap_column())
        layout.addLayout(columns)

        button_row = QtWidgets.QHBoxLayout()
        self.set_sliders_to_zero_button = QtWidgets.QPushButton("Set Sliders to 0")
        self.set_sliders_to_zero_button.setToolTip(
            "Set every target on these meshes to 0, so the proxies start from the rest shape."
        )
        self.set_sliders_to_zero_button.clicked.connect(self.handle_set_sliders_to_zero)
        button_row.addWidget(self.set_sliders_to_zero_button)
        self.create_button = QtWidgets.QPushButton("Create Wrapped Proxies")
        self.create_button.setToolTip(
            "Copy the meshes on the right without skin or history, and wrap each copy to the mesh on the left. "
            "The real meshes don't change. Works best in bind pose with every slider at 0."
        )
        self.create_button.clicked.connect(self.handle_create)
        button_row.addWidget(self.create_button)
        layout.addLayout(button_row)

        self.results_label = QtWidgets.QLabel()
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)

    def _build_wrap_to_column(self):
        column = QtWidgets.QVBoxLayout()
        column.addWidget(QtWidgets.QLabel(color_text("Wrap To", WRAP_TO_COLOR)))
        self.wrap_to_field = QtWidgets.QLineEdit()
        # only Load Selected changes it
        self.wrap_to_field.setReadOnly(True)
        self.wrap_to_field.setPlaceholderText("The body, usually")
        column.addWidget(self.wrap_to_field)
        load_button = QtWidgets.QPushButton("Load Selected")
        load_button.setToolTip("Use the selected mesh, or the mesh of the selected blendshape node.")
        load_button.clicked.connect(self.handle_load_wrap_to)
        column.addWidget(load_button)
        column.addStretch()
        return column

    def _build_meshes_to_wrap_column(self):
        column = QtWidgets.QVBoxLayout()
        column.addWidget(QtWidgets.QLabel(color_text("Meshes to Wrap", MESHES_TO_WRAP_COLOR)))
        self.meshes_list = QtWidgets.QListWidget()
        self.meshes_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        column.addWidget(self.meshes_list)

        list_buttons = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add Selected")
        add_button.setToolTip("Add the selected meshes to the list.")
        add_button.clicked.connect(self.handle_add_meshes)
        list_buttons.addWidget(add_button)
        remove_button = QtWidgets.QPushButton("Remove")
        remove_button.setToolTip("Take the meshes picked in the list out of it. The scene doesn't change.")
        remove_button.clicked.connect(self.handle_remove_meshes)
        list_buttons.addWidget(remove_button)
        column.addLayout(list_buttons)
        return column

    def refresh(self):
        """Shows the picked meshes, and what Create would do."""
        if self.wrap_to_mesh is None:
            self.wrap_to_field.clear()
        else:
            self.wrap_to_field.setText(blendshapeToolkitCore.get_short_name(self.wrap_to_mesh))
            self.wrap_to_field.setToolTip(self.wrap_to_mesh)

        self.meshes_list.clear()
        for mesh in self.meshes_to_wrap:
            self.meshes_list.addItem(blendshapeToolkitCore.get_short_name(mesh))
            # the full path on hover, for two meshes with the same name in different groups
            self.meshes_list.item(self.meshes_list.count() - 1).setToolTip(mesh)
        self._show_check()

    def _show_check(self, done_line=""):
        """Shows what stops Create in red, what to know first in yellow, and turns the buttons on when they can run."""
        lines = []
        if done_line:
            lines.append(done_line)

        check = blendshapeToolkitCore.check_wrapped_proxies(self.wrap_to_mesh, self.meshes_to_wrap)
        for problem in check.problems:
            lines.append(build_check_line(problem, passed=False))
        for warning in check.warnings:
            lines.append(build_warning_line(warning))
        if not check.problems:
            wrap_to_name = color_text(bold_text(blendshapeToolkitCore.get_short_name(self.wrap_to_mesh)), WRAP_TO_COLOR)
            mesh_names = []
            for mesh in self.meshes_to_wrap:
                mesh_names.append(blendshapeToolkitCore.get_short_name(mesh))
            mesh_names_text = color_text(bold_text(", ".join(mesh_names)), MESHES_TO_WRAP_COLOR)
            ready_text = f"Ready to wrap proxies of {mesh_names_text} to {wrap_to_name}"
            lines.append(color_text(f"✔ {ready_text}", PASS_COLOR))

        self.results_label.setText("<br>".join(lines))
        self.create_button.setEnabled(not check.problems)
        self.set_sliders_to_zero_button.setEnabled(bool(check.targets_that_are_on))

    def handle_use_selection(self):
        # Maya's wrap order: the meshes that follow first, the mesh they follow last
        try:
            selected_meshes = blendshapeToolkitCore.get_selected_meshes_for_wrap()
        except RuntimeError as error:
            cmds.warning(str(error))
            self.refresh()
            return

        self.wrap_to_mesh = selected_meshes[-1]
        self.meshes_to_wrap = selected_meshes[:-1]
        self.refresh()

    def handle_load_wrap_to(self):
        try:
            selected_meshes = blendshapeToolkitCore.get_selected_meshes_for_wrap()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        # with several selected, the last one, as in Maya's wrap order
        self.wrap_to_mesh = selected_meshes[-1]
        self.refresh()

    def handle_add_meshes(self):
        try:
            selected_meshes = blendshapeToolkitCore.get_selected_meshes_for_wrap()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        for mesh in selected_meshes:
            if mesh not in self.meshes_to_wrap:
                self.meshes_to_wrap.append(mesh)
        self.refresh()

    def handle_remove_meshes(self):
        picked_meshes = []
        for item in self.meshes_list.selectedItems():
            # the list shows the meshes in the same order as self.meshes_to_wrap
            picked_meshes.append(self.meshes_to_wrap[self.meshes_list.row(item)])
        for mesh in picked_meshes:
            self.meshes_to_wrap.remove(mesh)
        self.refresh()

    def handle_set_sliders_to_zero(self):
        try:
            blendshapeToolkitCore.set_sliders_to_zero([self.wrap_to_mesh] + self.meshes_to_wrap)
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        self._show_check(done_line=build_check_line("Set every slider on these meshes to 0", passed=True))

    def handle_create(self):
        try:
            group = blendshapeToolkitCore.create_wrapped_proxies(self.wrap_to_mesh, self.meshes_to_wrap)
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        group_name = bold_text(blendshapeToolkitCore.get_short_name(group))
        wrap_to_name = bold_text(blendshapeToolkitCore.get_short_name(self.wrap_to_mesh))
        done_text = f"Created {group_name}. Hide the real meshes and move {wrap_to_name}'s sliders to test the fit"
        self._show_check(done_line=build_check_line(done_text, passed=True))


def show_copy_weights_window():
    """Opens the Copy Weights window, closing the old one first."""
    main_window = get_maya_main_window()
    for old_window in main_window.findChildren(QtWidgets.QDialog, COPY_WEIGHTS_WINDOW_OBJECT_NAME):
        old_window.close()
        old_window.deleteLater()

    try:
        ui = BlendShapeCopyWeightsUI(main_window)
    except RuntimeError as error:
        cmds.warning(str(error))
        return None

    ui.show()
    return ui


def show_wrapped_proxies_window():
    """Opens the Create Wrapped Proxies window, closing the old one first."""
    main_window = get_maya_main_window()
    for old_window in main_window.findChildren(QtWidgets.QDialog, WRAPPED_PROXIES_WINDOW_OBJECT_NAME):
        old_window.close()
        old_window.deleteLater()

    try:
        ui = BlendShapeWrappedProxiesUI(main_window)
    except RuntimeError as error:
        cmds.warning(str(error))
        return None

    ui.show()
    return ui
