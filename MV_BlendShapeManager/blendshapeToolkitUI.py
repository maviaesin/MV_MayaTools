from dataclasses import dataclass
from enum import Enum
from importlib import reload

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from MV_BlendShapeManager import (
    blendshapeActionWindowsUI,
    blendshapeGlobalControllerUI,
    blendshapeTemplatesUI,
    blendshapeToolkitCore,
)
from MV_UtilityScripts import maya_utilities
from MV_UtilityScripts.Qt import QtCore, QtGui, QtWidgets

reload(blendshapeToolkitCore)
reload(blendshapeTemplatesUI)
reload(blendshapeActionWindowsUI)
reload(blendshapeGlobalControllerUI)

WINDOW_OBJECT_NAME = "MV_BlendShapeToolkit"
# Maya docks the window inside a workspace control with this name
WORKSPACE_CONTROL_NAME = WINDOW_OBJECT_NAME + "WorkspaceControl"
REBUILT_NAME_ENDING = "_rebuilt"
EXPLANATION_INDENT = 20
ACTION_ICON_SIZE = 20
SECTION_TITLE_EXTRA_PIXELS = 2
SECTION_TITLE_EXTRA_POINTS = 1.5
# a styled button loses Maya's own look, so Maya's button colors are set by hand
ACTION_BUTTON_STYLE = (
    "QPushButton { text-align: left; padding: 3px 6px; background-color: #5d5d5d; "
    "border: 1px solid #5d5d5d; border-radius: 2px; }"
    "QPushButton:hover { background-color: #707070; }"
    "QPushButton:pressed { background-color: #1d1d1d; }"
)
# buttons that open Maya's own tools get an outline in Maya's selection blue
MAYA_TOOL_BUTTON_STYLE = ACTION_BUTTON_STYLE + "QPushButton { border: 1px solid #5285a6; }"


class RebuildMode(Enum):
    REPLACE_TARGET = "replace"
    NEW_TARGET = "new"


@dataclass(frozen=True)
class RebuildDestination:
    """Where Merge and Bake Weights writes: into an existing target, or a new one with this name."""

    mode: RebuildMode
    target_name: str


# the mixin comes first, so its show() can dock the window
class BlendShapeToolkitUI(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("MV_BlendShape_Toolkit")
        self.setObjectName(WINDOW_OBJECT_NAME)

        self.buildUI()

    def buildUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setMenuBar(self._build_menu_bar())

        global_controller_button = self._build_action_button(
            "Global Shape Controller...",
            "polySphere.png",
            "One slider per target name, for every mesh of an avatar.",
        )
        global_controller_button.clicked.connect(self.handle_open_global_controller)
        layout.addWidget(global_controller_button)

        layout.addWidget(self._build_better_methods_section())
        actions_section, actions_layout = self._build_section("Weight Actions")
        # two buttons per row, like Maya's Modeling Toolkit
        button_grid = QtWidgets.QGridLayout()

        paint_weights_button = self._build_action_button(
            "Paint Weights",
            "paintBlendshape.png",
            "Open Maya's Paint Blend Shape Weights tool.",
            is_maya_tool=True,
        )
        paint_weights_button.clicked.connect(self.handle_paint_weights)
        button_grid.addWidget(paint_weights_button, 0, 0)

        reset_weights_button = self._build_action_button(
            "Reset Weights...",
            "menuIconReset.png",
            "Flood the painted weights of the targets or nodes selected in the Shape Editor with 1.",
        )
        reset_weights_button.clicked.connect(self.handle_reset_weights)
        button_grid.addWidget(reset_weights_button, 0, 1)

        bake_weights_button = self._build_action_button(
            "Bake Weights...",
            "bakeBlendShape.png",
            "Bake the painted weights of the target selected in the Shape Editor into its shape, so FBX keeps them.",
        )
        bake_weights_button.clicked.connect(self.handle_bake_weights)
        button_grid.addWidget(bake_weights_button, 1, 0)

        copy_weights_button = self._build_action_button(
            "Copy Weights...",
            "copySkinWeight.png",
            "Copy one target's painted weights to other targets on the same node.",
        )
        copy_weights_button.clicked.connect(self.handle_open_copy_weights)
        button_grid.addWidget(copy_weights_button, 1, 1)

        rebuild_button = self._build_action_button(
            "Merge and Bake Weights...",
            "blendShape.png",
            "Turn what the selected target's node shows right now, painted weights included, into a target.",
        )
        rebuild_button.clicked.connect(self.handle_rebuild_with_weights)
        # across both columns
        button_grid.addWidget(rebuild_button, 2, 0, 1, 2)

        actions_layout.addLayout(button_grid)
        layout.addWidget(actions_section)
        layout.addWidget(self._build_proxy_wrap_section())

        # keeps the window buttons at the bottom
        layout.addStretch()

        templates_button = QtWidgets.QPushButton("Templates...")
        templates_button.setToolTip("Make, edit and share templates.")
        templates_button.clicked.connect(self.handle_open_templates)
        layout.addWidget(templates_button)

        validate_button = QtWidgets.QPushButton("Validate...")
        validate_button.setToolTip(
            "Check a blendshape node against a template: missing, extra, misspelled and empty targets."
        )
        validate_button.clicked.connect(self.handle_open_validate)
        layout.addWidget(validate_button)

    def _build_better_methods_section(self):
        """BSM's safer versions of Maya's own buttons."""
        better_methods_section, better_methods_layout = self._build_section("Better Methods")
        create_blend_shape_button = self._build_action_button(
            "Create Blendshape",
            "blendShape.png",
            "Add an empty blendshape node to the selected mesh, before its skinCluster.",
        )
        create_blend_shape_button.clicked.connect(self.handle_create_blend_shape)
        better_methods_layout.addWidget(create_blend_shape_button)

        from_template_button = self._build_action_button(
            "Create Blendshape from Template...",
            "blendShape.png",
            "Add a blendshape node with a template's targets to the selected meshes, or to every mesh in a group.",
        )
        from_template_button.clicked.connect(self.handle_create_blend_shape_from_template)
        better_methods_layout.addWidget(from_template_button)
        return better_methods_section

    def _build_proxy_wrap_section(self):
        proxy_wrap_section, proxy_wrap_layout = self._build_section("Proxy Wrap")
        wrapped_proxies_button = self._build_action_button(
            "Create Wrapped Proxies...",
            "proximityWrap.png",
            "Copy meshes like clothing and wrap them to the body, to test how they follow its sliders. "
            "Select the meshes, then the body.",
        )
        wrapped_proxies_button.clicked.connect(self.handle_open_wrapped_proxies)
        proxy_wrap_layout.addWidget(wrapped_proxies_button)

        add_proxy_button = self._build_action_button(
            "Add Proxy as Target...",
            "blendShapePlus.png",
            "Save the shape the selected proxies show right now as a target on the meshes they were copied from.",
        )
        add_proxy_button.clicked.connect(self.handle_add_proxy_as_target)
        proxy_wrap_layout.addWidget(add_proxy_button)
        return proxy_wrap_section

    def _build_action_button(self, text, icon_name, tooltip, is_maya_tool=False):
        """A button with one of Maya's icons, like in Maya's toolkits. is_maya_tool adds a blue outline."""
        # ":/" loads one of Maya's built-in icons by name
        button = QtWidgets.QPushButton(QtGui.QIcon(f":/{icon_name}"), text)
        button.setIconSize(QtCore.QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        button.setToolTip(tooltip)
        if is_maya_tool:
            button.setStyleSheet(MAYA_TOOL_BUTTON_STYLE)
        else:
            button.setStyleSheet(ACTION_BUTTON_STYLE)
        return button

    def _build_section(self, title):
        """A section that folds away under its title. Returns the section and the layout for its buttons."""
        section = QtWidgets.QWidget()
        section_layout = QtWidgets.QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)

        # a QToolButton can show an arrow next to its text
        title_button = QtWidgets.QToolButton()
        title_button.setText(title)
        title_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        title_button.setArrowType(QtCore.Qt.DownArrow)
        title_button.setCheckable(True)
        title_button.setChecked(True)
        title_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        title_font = title_button.font()
        title_font.setBold(True)
        # Maya sets fonts in pixels; outside Maya they're in points
        if title_font.pixelSize() > 0:
            title_font.setPixelSize(title_font.pixelSize() + SECTION_TITLE_EXTRA_PIXELS)
        else:
            title_font.setPointSizeF(title_font.pointSizeF() + SECTION_TITLE_EXTRA_POINTS)
        title_button.setFont(title_font)
        section_layout.addWidget(title_button)

        contents = QtWidgets.QWidget()
        contents_layout = QtWidgets.QVBoxLayout(contents)
        section_layout.addWidget(contents)

        title_button.toggled.connect(lambda opened: self.handle_section_toggled(title_button, contents, opened))
        return section, contents_layout

    def _build_menu_bar(self):
        # without a parent, Qt can delete the menu right away
        menu_bar = QtWidgets.QMenuBar(self)
        help_menu = QtWidgets.QMenu("Help", menu_bar)
        menu_bar.addMenu(help_menu)
        readme_action = help_menu.addAction("Open README")
        readme_action.triggered.connect(self.handle_open_readme)
        return menu_bar

    def handle_section_toggled(self, title_button, contents, opened):
        contents.setVisible(opened)
        if opened:
            title_button.setArrowType(QtCore.Qt.DownArrow)
        else:
            title_button.setArrowType(QtCore.Qt.RightArrow)

    def handle_open_readme(self):
        try:
            readme_path = blendshapeToolkitCore.get_readme_path()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        opened = QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(readme_path))
        if not opened:
            cmds.warning(f"No app on this computer opens .md files. The README is at {readme_path}.")

    def _ask_rebuild_destination(self, node, selected_target_name):
        """Asks whether to replace a target or make a new one. Returns None if the user cancels."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Merge and Bake Weights")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel(f"Where should the shape {node} shows right now go?"))

        replace_button = QtWidgets.QRadioButton("Replace an existing target")
        replace_button.setChecked(True)
        layout.addWidget(replace_button)
        target_combo = QtWidgets.QComboBox()
        target_combo.addItems(blendshapeToolkitCore.get_target_names(node))
        # starts on the target picked in the Shape Editor
        target_combo.setCurrentText(selected_target_name)
        layout.addWidget(target_combo)

        new_button = QtWidgets.QRadioButton("Make a new target")
        layout.addWidget(new_button)
        name_field = QtWidgets.QLineEdit(selected_target_name + REBUILT_NAME_ENDING)
        name_field.setEnabled(False)
        layout.addWidget(name_field)

        replace_button.toggled.connect(target_combo.setEnabled)
        new_button.toggled.connect(name_field.setEnabled)

        button_row = QtWidgets.QHBoxLayout()
        rebuild_button = QtWidgets.QPushButton("Merge and Bake")
        rebuild_button.clicked.connect(dialog.accept)
        button_row.addWidget(rebuild_button)
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return None
        if replace_button.isChecked():
            return RebuildDestination(mode=RebuildMode.REPLACE_TARGET, target_name=target_combo.currentText())
        return RebuildDestination(mode=RebuildMode.NEW_TARGET, target_name=name_field.text().strip())

    def _ask_to_continue_with_active_targets(self, active_targets):
        """Lists the targets that are on and asks to continue. Returns True right away if none are."""
        if not active_targets.on_this_node and not active_targets.on_other_nodes:
            return True

        lines = []
        if active_targets.on_this_node:
            lines.append("These are on and will be part of the result:")
            for target in active_targets.on_this_node:
                lines.append(f"    {target.target_name}  {target.weight:.2f}")
        if active_targets.on_other_nodes:
            lines.append("These are on in the viewport but will NOT be part of the result:")
            for target in active_targets.on_other_nodes:
                lines.append(f"    {target.node}: {target.target_name}  {target.weight:.2f}")

        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle("Other targets are on")
        message_box.setText("\n".join(lines))
        continue_button = message_box.addButton("Continue", QtWidgets.QMessageBox.AcceptRole)
        message_box.addButton("Go Back", QtWidgets.QMessageBox.RejectRole)
        message_box.exec()
        return message_box.clickedButton() == continue_button

    def handle_rebuild_with_weights(self):
        try:
            selected_targets = blendshapeToolkitCore.get_shape_editor_selected_targets()
            node = blendshapeToolkitCore.check_targets_share_one_node(selected_targets)
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        selected_target_name = selected_targets[0].target_name
        destination = self._ask_rebuild_destination(node, selected_target_name)
        if destination is None:
            return

        # the target being replaced, or the one worked on, isn't "another" target that's on
        if destination.mode == RebuildMode.REPLACE_TARGET:
            target_being_rebuilt = destination.target_name
        else:
            target_being_rebuilt = selected_target_name
        active_targets = blendshapeToolkitCore.find_active_targets(node, except_target_name=target_being_rebuilt)
        # Go Back closes everything, so the sliders can be fixed in the Shape Editor
        if not self._ask_to_continue_with_active_targets(active_targets):
            return

        try:
            if destination.mode == RebuildMode.REPLACE_TARGET:
                blendshapeToolkitCore.rebuild_with_weights_into_target(node, destination.target_name)
                message = (
                    f"Merged and baked into {destination.target_name}. "
                    "Reset its painted weights to 1 to see it the way it will export."
                )
            else:
                blendshapeToolkitCore.rebuild_with_weights_into_new_target(node, destination.target_name)
                message = f"Added {destination.target_name} to {node}."
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        QtWidgets.QMessageBox.information(self, "Merge and Bake Weights", message)

    def _ask_which_node_weights(self, nodes):
        """Asks which painted weights of the selected nodes to flood with 1. Returns None if the user cancels."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Reset Weights")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel(f"Which painted weights of {', '.join(nodes)} should be flooded with 1?"))

        choices = [
            (
                blendshapeToolkitCore.NodeWeights.TARGET_WEIGHTS,
                "Every target's weights",
                "Like resetting all of the node's targets. The node's base weights stay as they are.",
            ),
            (
                blendshapeToolkitCore.NodeWeights.BASE_WEIGHTS,
                "The node's base weights",
                "The painting on the node itself, which scales every target. "
                "Maya's paint tool paints it when the node is picked.",
            ),
            (
                blendshapeToolkitCore.NodeWeights.BOTH,
                "Both",
                "The node goes back to no painting at all.",
            ),
        ]
        radio_buttons = []
        for weights_to_reset, title, explanation in choices:
            radio_button = QtWidgets.QRadioButton(title)
            layout.addWidget(radio_button)
            explanation_label = QtWidgets.QLabel(explanation)
            explanation_label.setWordWrap(True)
            explanation_label.setEnabled(False)
            explanation_label.setContentsMargins(EXPLANATION_INDENT, 0, 0, 0)
            layout.addWidget(explanation_label)
            radio_buttons.append((radio_button, weights_to_reset))
        radio_buttons[0][0].setChecked(True)

        button_row = QtWidgets.QHBoxLayout()
        ok_button = QtWidgets.QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        button_row.addWidget(ok_button)
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return None
        for radio_button, weights_to_reset in radio_buttons:
            if radio_button.isChecked():
                return weights_to_reset
        raise AssertionError("One radio button is always checked.")

    def _reset_selected_node_weights(self, nodes):
        weights_to_reset = self._ask_which_node_weights(nodes)
        if weights_to_reset is None:
            return
        try:
            blendshapeToolkitCore.reset_node_weights(nodes, weights_to_reset=weights_to_reset)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        self._show_reset_message(nodes)

    def _reset_selected_target_weights(self):
        try:
            selected_targets = blendshapeToolkitCore.get_shape_editor_selected_targets()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        target_names = []
        for selected_target in selected_targets:
            target_names.append(selected_target.target_name)
        answer = QtWidgets.QMessageBox.question(
            self,
            "Reset Weights",
            f"The painted weights of {', '.join(target_names)} will be flooded with 1.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
        )
        if answer != QtWidgets.QMessageBox.Ok:
            return

        try:
            blendshapeToolkitCore.reset_painted_weights(selected_targets)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        self._show_reset_message(target_names)

    def _show_reset_message(self, names):
        cmds.inViewMessage(assistMessage=f"Reset painted weights: {', '.join(names)}", position="topCenter", fade=True)

    def handle_reset_weights(self):
        try:
            selected_nodes = blendshapeToolkitCore.get_shape_editor_selected_nodes()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        # a selected node means the whole node; otherwise it's the selected targets
        if selected_nodes:
            self._reset_selected_node_weights(selected_nodes)
        else:
            self._reset_selected_target_weights()

    def handle_bake_weights(self):
        try:
            selected_targets = blendshapeToolkitCore.get_shape_editor_selected_targets()
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        if len(selected_targets) != 1:
            cmds.warning("Bake Weights works on one target. Select exactly one target in the Shape Editor.")
            return

        target = selected_targets[0]
        answer = QtWidgets.QMessageBox.question(
            self,
            "Bake Weights",
            f"{target.target_name}'s painted weights will become part of its shape, "
            "and its weights will be flooded with 1.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
        )
        if answer != QtWidgets.QMessageBox.Ok:
            return

        try:
            blendshapeToolkitCore.bake_painted_weights(target.node, target.target_name)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        cmds.inViewMessage(assistMessage=f"Baked painted weights: {target.target_name}", position="topCenter", fade=True)

    def handle_paint_weights(self):
        blendshapeToolkitCore.start_paint_blendshape_weights_tool()

    def handle_open_copy_weights(self):
        blendshapeActionWindowsUI.show_copy_weights_window()

    def handle_create_blend_shape(self):
        try:
            mesh = maya_utilities.get_user_mesh_selection()
            node = blendshapeToolkitCore.create_blend_shape_node(mesh)
        except blendshapeToolkitCore.DeformersAfterSkinClusterError as error:
            # a popup, because the mesh has to be fixed before trying again
            QtWidgets.QMessageBox.information(self, "Create Blendshape", str(error))
            return
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        mesh_name = blendshapeToolkitCore.get_short_name(mesh)
        cmds.inViewMessage(assistMessage=f"Created {node} on {mesh_name}", position="topCenter", fade=True)

    def handle_open_wrapped_proxies(self):
        blendshapeActionWindowsUI.show_wrapped_proxies_window()

    def _ask_proxy_target_name(self, proxies):
        """Asks for the target name, starting on the body slider that is on the most. None means Cancel."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add Proxy as Target")
        layout = QtWidgets.QVBoxLayout(dialog)
        proxy_names = []
        for proxy in proxies:
            proxy_names.append(blendshapeToolkitCore.get_short_name(proxy))
        explanation_label = QtWidgets.QLabel(
            f"The shape {', '.join(proxy_names)} shows right now becomes a target "
            "on the mesh it was copied from. Target name:"
        )
        explanation_label.setWordWrap(True)
        layout.addWidget(explanation_label)

        # editable, so a new name can be typed
        name_combo = QtWidgets.QComboBox()
        name_combo.setEditable(True)
        name_combo.addItems(blendshapeToolkitCore.list_proxy_mesh_target_names(proxies))
        body_targets_that_are_on = blendshapeToolkitCore.find_targets_that_are_on(
            blendshapeToolkitCore.find_proxy_wrap_to_meshes(proxies)
        )
        name_combo.setEditText(blendshapeToolkitCore.suggest_proxy_target_name(body_targets_that_are_on))
        layout.addWidget(name_combo)

        check_label = QtWidgets.QLabel()
        check_label.setWordWrap(True)
        layout.addWidget(check_label)

        button_row = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Add")
        add_button.clicked.connect(dialog.accept)
        button_row.addWidget(add_button)
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        # fires on typing and on picking from the list
        name_combo.editTextChanged.connect(
            lambda text: self._show_proxy_target_check(proxies, text.strip(), check_label, add_button)
        )
        self._show_proxy_target_check(proxies, name_combo.currentText().strip(), check_label, add_button)

        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return None
        return name_combo.currentText().strip()

    def _show_proxy_target_check(self, proxies, target_name, check_label, add_button):
        """Shows what stops Add in red, what to know first in yellow, and turns Add on only when it can run."""
        check = blendshapeToolkitCore.check_proxies_as_target(proxies, target_name)
        lines = []
        for problem in check.problems:
            lines.append(blendshapeTemplatesUI.build_check_line(problem, passed=False))
        for warning in check.warnings:
            lines.append(blendshapeActionWindowsUI.build_warning_line(warning))
        if not check.problems and check.meshes_without_target:
            mesh_names = []
            for mesh in check.meshes_without_target:
                mesh_names.append(blendshapeToolkitCore.get_short_name(mesh))
            lines.append(blendshapeTemplatesUI.build_check_line(
                f"Adds {target_name} as a new target to {', '.join(mesh_names)}", passed=True
            ))
        check_label.setText("<br>".join(lines))
        add_button.setEnabled(not check.problems)

    def handle_add_proxy_as_target(self):
        try:
            proxies = blendshapeToolkitCore.get_selected_proxies()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        target_name = self._ask_proxy_target_name(proxies)
        if target_name is None:
            return
        try:
            blendshapeToolkitCore.add_proxies_as_target(proxies, target_name)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        cmds.inViewMessage(assistMessage=f"Added proxy as target: {target_name}", position="topCenter", fade=True)

    def handle_open_global_controller(self):
        blendshapeGlobalControllerUI.showUI()

    def handle_open_templates(self):
        blendshapeTemplatesUI.showUI()

    def handle_create_blend_shape_from_template(self):
        # opens the Templates window for now; this button gets its own window later
        blendshapeTemplatesUI.showUI()

    def handle_open_validate(self):
        blendshapeTemplatesUI.showUI(open_validate_tab=True)


def showUI():
    """Opens the Blendshape Toolkit, closing the old one first."""
    if cmds.workspaceControl(WORKSPACE_CONTROL_NAME, exists=True):
        cmds.deleteUI(WORKSPACE_CONTROL_NAME)

    ui = BlendShapeToolkitUI()
    # retain=False: Maya won't bring back an empty dock after a restart
    ui.show(dockable=True, retain=False)
    return ui
