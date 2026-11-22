from importlib import reload

from maya import OpenMayaUI as omui
from maya import cmds

from MV_BlendShapeManager import blendshapeToolkitCore, blendshapeTemplatesCore
from MV_UtilityScripts import maya_utilities
from MV_UtilityScripts.Qt import QtCompat, QtCore, QtGui, QtWidgets

reload(blendshapeTemplatesCore)
reload(blendshapeToolkitCore)

WINDOW_OBJECT_NAME = "MV_BlendShapeTemplatesWindow"
VALIDATE_TAB_INDEX = 1
MAX_TARGET_COUNT = 500
EXAMPLE_LABEL = " (example)"
EMPTY_TEMPLATE = blendshapeTemplatesCore.BlendShapeTemplate("", "", ("",))

# Validate colors: blue for what's on the mesh, lilac for the template, green and red for pass and fail
MESH_COLOR = "#5fb4ff"
TEMPLATE_COLOR = "#c792ea"
PASS_COLOR = "lightGreen"
FAIL_COLOR = "#ff6b6b"


def get_maya_main_window():
    main_window_pointer = omui.MQtUtil.mainWindow()
    return QtCompat.wrapInstance(int(main_window_pointer), QtWidgets.QWidget)


def color_text(text, color):
    """Wraps text in a span, so a QLabel shows it in that color, like Renamer's legend."""
    return f'<span style="color: {color};">{text}</span>'


def build_check_line(text, passed):
    if passed:
        return color_text(f"✔ {text}", PASS_COLOR)
    return color_text(f"✘ {text}", FAIL_COLOR)


def fill_name_list(name_list, names, color):
    name_list.clear()
    for name in names:
        item = QtWidgets.QListWidgetItem(name)
        item.setForeground(QtGui.QColor(color))
        name_list.addItem(item)


class BlendShapeTemplatesUI(QtWidgets.QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("MV_BlendShape_Templates")
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.resize(380, 520)

        # what's in the template dropdown: user templates first, then the examples
        self.user_templates = []
        self.example_templates = []
        self.loaded_template = EMPTY_TEMPLATE
        self.current_index = -1
        # full path of the mesh loaded in the Validate tab, empty until the user loads one
        self.validate_mesh = ""

        self.buildUI()
        self.refresh()

    def buildUI(self):
        main_layout = QtWidgets.QVBoxLayout()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_templates_tab(), "Templates")
        self.tabs.addTab(self._build_validate_tab(), "Validate")

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def _build_templates_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        template_row = QtWidgets.QHBoxLayout()
        template_row.addWidget(QtWidgets.QLabel("Template:"))
        self.template_combo = QtWidgets.QComboBox()
        self.template_combo.currentIndexChanged.connect(self.handle_template_changed)
        template_row.addWidget(self.template_combo, 1)
        new_button = QtWidgets.QPushButton("New")
        new_button.clicked.connect(self.handle_new_template)
        template_row.addWidget(new_button)
        delete_button = QtWidgets.QPushButton("Delete")
        delete_button.clicked.connect(self.handle_delete_template)
        template_row.addWidget(delete_button)
        layout.addLayout(template_row)

        self.template_name_field = QtWidgets.QLineEdit()
        layout.addLayout(self._build_labeled_row("Template name:", self.template_name_field))
        self.node_name_field = QtWidgets.QLineEdit()
        layout.addLayout(self._build_labeled_row("Node name prefix:", self.node_name_field))
        self.target_count_box = QtWidgets.QSpinBox()
        self.target_count_box.setRange(1, MAX_TARGET_COUNT)
        self.target_count_box.valueChanged.connect(self.handle_target_count_changed)
        layout.addLayout(self._build_labeled_row("Targets:", self.target_count_box))

        self.target_table = QtWidgets.QTableWidget(1, 1)
        self.target_table.setHorizontalHeaderLabels(["Target name"])
        self.target_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.target_table)

        file_row = QtWidgets.QHBoxLayout()
        save_button = QtWidgets.QPushButton("Save")
        save_button.clicked.connect(self.handle_save_template)
        file_row.addWidget(save_button)
        import_button = QtWidgets.QPushButton("Import...")
        import_button.clicked.connect(self.handle_import_template)
        file_row.addWidget(import_button)
        export_button = QtWidgets.QPushButton("Export...")
        export_button.clicked.connect(self.handle_export_template)
        file_row.addWidget(export_button)
        layout.addLayout(file_row)

        add_button = QtWidgets.QPushButton("Create Blendshape from Template")
        add_button.setToolTip(
            "Add a blendshape node with this template's targets, empty and ready to sculpt, "
            "to the selected meshes, or to every mesh in the selected group."
        )
        add_button.clicked.connect(self.handle_add_blend_shapes)
        layout.addWidget(add_button)

        return tab

    def _build_validate_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        load_row = QtWidgets.QHBoxLayout()
        load_help_label = QtWidgets.QLabel("Select mesh with blendshape node to validate")
        # wrapping keeps the button from being cut off in a narrow window
        load_help_label.setWordWrap(True)
        load_row.addWidget(load_help_label, 1)
        load_button = QtWidgets.QPushButton("Load Selected Mesh")
        load_button.clicked.connect(self.handle_load_validate_mesh)
        load_row.addWidget(load_button)
        layout.addLayout(load_row)

        columns = QtWidgets.QHBoxLayout()
        columns.addLayout(self._build_validate_mesh_column())
        columns.addLayout(self._build_validate_template_column())
        layout.addLayout(columns)

        validate_button = QtWidgets.QPushButton("Validate")
        validate_button.clicked.connect(self.handle_validate)
        layout.addWidget(validate_button)

        self.validate_results_label = QtWidgets.QLabel()
        self.validate_results_label.setWordWrap(True)
        layout.addWidget(self.validate_results_label)

        self.add_missing_button = QtWidgets.QPushButton("Add Missing Targets")
        self.add_missing_button.setToolTip("Adds the missing targets empty, after the last target.")
        self.add_missing_button.setEnabled(False)
        self.add_missing_button.clicked.connect(self.handle_add_missing_targets)
        layout.addWidget(self.add_missing_button)

        return tab

    def _build_validate_mesh_column(self):
        column = QtWidgets.QVBoxLayout()
        self.validate_mesh_label = QtWidgets.QLabel(f"Mesh: {color_text('none loaded', MESH_COLOR)}")
        column.addWidget(self.validate_mesh_label)

        # a mesh can have several blendshape nodes, so the user picks which one to check
        node_row = QtWidgets.QHBoxLayout()
        node_row.addWidget(QtWidgets.QLabel("Node:"))
        self.validate_node_combo = QtWidgets.QComboBox()
        self.validate_node_combo.currentIndexChanged.connect(self.handle_validate_node_changed)
        node_row.addWidget(self.validate_node_combo, 1)
        column.addLayout(node_row)

        self.node_target_list = QtWidgets.QListWidget()
        column.addWidget(self.node_target_list)
        return column

    def _build_validate_template_column(self):
        column = QtWidgets.QVBoxLayout()
        column.addWidget(QtWidgets.QLabel(color_text("Template to validate with", TEMPLATE_COLOR)))

        self.validate_template_combo = QtWidgets.QComboBox()
        self.validate_template_combo.currentIndexChanged.connect(self.handle_validate_template_changed)
        column.addWidget(self.validate_template_combo)

        self.template_target_list = QtWidgets.QListWidget()
        column.addWidget(self.template_target_list)
        return column

    def _build_labeled_row(self, label, field):
        row = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel(label)
        name_label.setFixedWidth(90)
        row.addWidget(name_label)
        row.addWidget(field)
        return row

    def refresh(self, select_name="", select_example=False):
        """Reloads the template list and shows the template with select_name, or the first one."""
        self.user_templates = blendshapeTemplatesCore.list_templates(blendshapeTemplatesCore.get_templates_folder())
        self.example_templates = blendshapeTemplatesCore.list_shipped_templates(
            blendshapeTemplatesCore.get_shipped_templates_folder(), blendshapeTemplatesCore.get_hidden_templates_file()
        )

        # so filling the dropdown doesn't call handle_template_changed
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        for template in self.user_templates:
            self.template_combo.addItem(template.template_name)
        for template in self.example_templates:
            self.template_combo.addItem(template.template_name + EXAMPLE_LABEL)

        index = self._find_template_index(select_name, select_example)
        if index == -1 and self.template_combo.count() > 0:
            index = 0
        self.template_combo.setCurrentIndex(index)
        self.template_combo.blockSignals(False)

        self._show_template_at(index)
        self._fill_validate_template_combo()

    def _fill_validate_template_combo(self):
        """Fills the Validate tab's dropdown with the same templates, keeping the picked one if it's still there."""
        picked_text = self.validate_template_combo.currentText()

        self.validate_template_combo.blockSignals(True)
        self.validate_template_combo.clear()
        for template in self.user_templates:
            self.validate_template_combo.addItem(template.template_name)
        for template in self.example_templates:
            self.validate_template_combo.addItem(template.template_name + EXAMPLE_LABEL)

        index = self.validate_template_combo.findText(picked_text)
        if index == -1 and self.validate_template_combo.count() > 0:
            index = 0
        self.validate_template_combo.setCurrentIndex(index)
        self.validate_template_combo.blockSignals(False)

        self._show_validate_template()

    def _get_validate_template(self):
        index = self.validate_template_combo.currentIndex()
        if index == -1:
            return None
        return self._get_template_at(index)

    def _show_validate_template(self):
        """Shows the picked template and clears the old results, which no longer fit."""
        self.node_target_list.clear()
        self.validate_results_label.clear()
        self.add_missing_button.setEnabled(False)

        template = self._get_validate_template()
        if template is None:
            self.template_target_list.clear()
            return
        fill_name_list(self.template_target_list, template.target_names, TEMPLATE_COLOR)

    def _show_check(self, check, template):
        fill_name_list(self.node_target_list, check.node_target_names, MESH_COLOR)
        node_name = color_text(check.node, MESH_COLOR)
        template_name = color_text(template.template_name, TEMPLATE_COLOR)

        lines = []
        if check.missing_targets:
            missing_text = f"Missing from {node_name}: {', '.join(check.missing_targets)}"
            lines.append(build_check_line(missing_text, passed=False))
        else:
            lines.append(build_check_line("No targets are missing", passed=True))

        if check.extra_targets:
            extra_text = f"Not in {template_name}: {', '.join(check.extra_targets)}"
            lines.append(build_check_line(extra_text, passed=False))
        else:
            lines.append(build_check_line("No extra targets", passed=True))

        if check.likely_typos:
            for typo in check.likely_typos:
                typo_text = f"'{typo.scene_name}' in {node_name} should be '{typo.template_name}'"
                lines.append(build_check_line(typo_text, passed=False))
        else:
            lines.append(build_check_line("No likely typos", passed=True))

        if check.empty_targets:
            empty_text = f"No sculpted data in {node_name}: {', '.join(check.empty_targets)}"
            lines.append(build_check_line(empty_text, passed=False))
        else:
            lines.append(build_check_line("Every target has sculpted data", passed=True))

        target_names_match = not check.missing_targets and not check.extra_targets and not check.likely_typos
        if target_names_match and not check.empty_targets:
            summary = f"Node {node_name} has the same targets as template {template_name}, all sculpted"
            lines.insert(0, build_check_line(summary, passed=True))

        self.validate_results_label.setText("<br>".join(lines))
        self.add_missing_button.setEnabled(len(check.missing_targets) > 0)

    def _find_template_index(self, template_name, is_example):
        if is_example:
            for index, template in enumerate(self.example_templates):
                if template.template_name == template_name:
                    return len(self.user_templates) + index
            return -1

        for index, template in enumerate(self.user_templates):
            if template.template_name == template_name:
                return index
        return -1

    def _get_template_at(self, index):
        if index < len(self.user_templates):
            return self.user_templates[index]
        return self.example_templates[index - len(self.user_templates)]

    def _is_example_at(self, index):
        return index >= len(self.user_templates)

    def _show_template_at(self, index):
        if index == -1:
            template = EMPTY_TEMPLATE
        else:
            template = self._get_template_at(index)

        self.template_name_field.setText(template.template_name)
        self.node_name_field.setText(template.node_name)

        self.target_count_box.blockSignals(True)
        self.target_count_box.setValue(len(template.target_names))
        self.target_count_box.blockSignals(False)

        self.target_table.setRowCount(len(template.target_names))
        for row, target_name in enumerate(template.target_names):
            self.target_table.setItem(row, 0, QtWidgets.QTableWidgetItem(target_name))

        self.loaded_template = template
        self.current_index = index

    def _read_template_from_fields(self):
        target_names = []
        for row in range(self.target_table.rowCount()):
            item = self.target_table.item(row, 0)
            if item is None:
                target_names.append("")
            else:
                target_names.append(item.text().strip())

        return blendshapeTemplatesCore.BlendShapeTemplate(
            template_name=self.template_name_field.text().strip(),
            node_name=self.node_name_field.text().strip(),
            target_names=tuple(target_names),
        )

    def _save_fields(self):
        """Saves what's in the fields to the user folder. Returns False if it couldn't."""
        template = self._read_template_from_fields()
        try:
            blendshapeTemplatesCore.save_template(template, blendshapeTemplatesCore.get_templates_folder())
        except RuntimeError as error:
            cmds.warning(str(error))
            return False

        self.refresh(template.template_name)
        return True

    def _ask_to_save_changes(self):
        """Asks to save unsaved edits first. Returns False if the user picked Cancel."""
        # dataclasses compare field by field, so == tells us if anything was edited
        if self._read_template_from_fields() == self.loaded_template:
            return True

        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle("Save changes?")
        message_box.setText(f"'{self.loaded_template.template_name}' has unsaved changes.")
        message_box.setStandardButtons(
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
        )
        message_box.button(QtWidgets.QMessageBox.Discard).setText("Don't Save")
        message_box.exec()
        answer = message_box.standardButton(message_box.clickedButton())

        if answer == QtWidgets.QMessageBox.Cancel:
            return False
        if answer == QtWidgets.QMessageBox.Save:
            return self._save_fields()
        return True

    def handle_template_changed(self, index):
        picked_template = self._get_template_at(index)
        picked_is_example = self._is_example_at(index)

        # put the dropdown back for now, in case the user cancels
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentIndex(self.current_index)
        self.template_combo.blockSignals(False)

        if not self._ask_to_save_changes():
            return

        # saving can change the list, so find the picked template again by name
        new_index = self._find_template_index(picked_template.template_name, picked_is_example)
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentIndex(new_index)
        self.template_combo.blockSignals(False)
        self._show_template_at(new_index)

    def handle_target_count_changed(self, count):
        self.target_table.setRowCount(count)

    def handle_new_template(self):
        if not self._ask_to_save_changes():
            return

        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentIndex(-1)
        self.template_combo.blockSignals(False)
        self._show_template_at(-1)

    def handle_save_template(self):
        # TODO: renaming saves a new copy and leaves the old one behind.
        # check this after user testing, if deleting the old one by hand is annoying, fix it
        self._save_fields()

    def handle_delete_template(self):
        if self.current_index == -1:
            cmds.warning("Pick a template to delete.")
            return

        template_name = self.loaded_template.template_name
        answer = QtWidgets.QMessageBox.question(self, "Delete template", f"Delete '{template_name}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:
            if self._is_example_at(self.current_index):
                blendshapeTemplatesCore.hide_shipped_template(template_name, blendshapeTemplatesCore.get_hidden_templates_file())
            else:
                blendshapeTemplatesCore.delete_template(template_name, blendshapeTemplatesCore.get_templates_folder())
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        self.refresh()

    def handle_import_template(self):
        if not self._ask_to_save_changes():
            return

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Template", "", "Template files (*.json)"
        )
        if not file_path:
            return

        try:
            template = blendshapeTemplatesCore.read_template_file(file_path)
            blendshapeTemplatesCore.save_template(template, blendshapeTemplatesCore.get_templates_folder())
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        self.refresh(template.template_name)

    def handle_export_template(self):
        template = self._read_template_from_fields()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Template", f"{template.template_name}.json", "Template files (*.json)"
        )
        if not file_path:
            return

        try:
            blendshapeTemplatesCore.write_template_file(template, file_path)
        except RuntimeError as error:
            cmds.warning(str(error))

    def handle_add_blend_shapes(self):
        template = self._read_template_from_fields()
        try:
            selection = blendshapeToolkitCore.get_template_selection()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        # for meshes, their top group is only a guess, so the artist checks it in the popup
        asset_name = selection.asset_name
        if asset_name is None:
            asset_name = blendshapeToolkitCore.find_asset_name(selection.meshes[0])
        choice = self._ask_meshes_and_asset_name(list(selection.meshes), template, asset_name)
        if choice is None:
            return
        meshes, asset_name = choice
        if not meshes:
            cmds.warning("No mesh was ticked, so nothing was created.")
            return

        self._create_from_template(meshes, template, asset_name)

    def _ask_meshes_and_asset_name(self, meshes, template, asset_name):
        """Asks for the asset name and which meshes to use. Returns None if the user cancels."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Create Blendshape from Template")
        layout = QtWidgets.QVBoxLayout(dialog)

        asset_name_field = QtWidgets.QLineEdit(asset_name)
        asset_name_field.setToolTip("Usually the avatar's group. Leave it empty for <prefix>_<mesh>.")
        layout.addLayout(self._build_labeled_row("Asset name:", asset_name_field))
        example_label = QtWidgets.QLabel()
        layout.addWidget(example_label)
        self._show_node_name_example(example_label, template, asset_name, meshes[0])
        asset_name_field.textChanged.connect(
            lambda text: self._show_node_name_example(example_label, template, text.strip(), meshes[0])
        )

        layout.addWidget(QtWidgets.QLabel("Untick the meshes that need no targets, like eyes, teeth or LODs."))
        mesh_list = QtWidgets.QListWidget()
        for mesh in meshes:
            # a little space between the tick and the name
            item = QtWidgets.QListWidgetItem(f"  {blendshapeToolkitCore.get_short_name(mesh)}")
            # the full path on hover, for meshes with the same name
            item.setToolTip(mesh)
            # adds a tick box; every mesh starts ticked
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)
            mesh_list.addItem(item)
        layout.addWidget(mesh_list)

        button_row = QtWidgets.QHBoxLayout()
        create_button = QtWidgets.QPushButton("Create")
        create_button.clicked.connect(dialog.accept)
        button_row.addWidget(create_button)
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return None
        # the rows are in the same order as meshes
        ticked_meshes = []
        for row, mesh in enumerate(meshes):
            if mesh_list.item(row).checkState() == QtCore.Qt.Checked:
                ticked_meshes.append(mesh)
        return ticked_meshes, asset_name_field.text().strip()

    def _show_node_name_example(self, example_label, template, asset_name, mesh):
        node_name = blendshapeToolkitCore.build_template_node_name(template.node_name, asset_name, mesh)
        example_label.setText(f"Nodes are named like {node_name}")

    def _create_from_template(self, meshes, template, asset_name):
        """Checks every mesh first and shows all the problems in one popup, then creates every node."""
        try:
            check = blendshapeToolkitCore.check_template_creation(meshes, template, asset_name)
        except RuntimeError as error:
            cmds.warning(str(error))
            return
        if check.refusals:
            QtWidgets.QMessageBox.information(
                self, "Blendshapes", "\n\n".join(check.refusals) + "\n\nNothing was changed."
            )
            return

        # read these before adding, so the message can name them
        existing_blend_shapes_per_mesh = []
        for mesh in meshes:
            existing_blend_shapes_per_mesh.append(maya_utilities.find_blend_shape_nodes(mesh))

        try:
            nodes = blendshapeToolkitCore.add_blend_shapes_from_template(meshes, template, asset_name)
        except blendshapeToolkitCore.NodeNameTakenError as error:
            if not self._ask_to_create_anyway(str(error)):
                return
            nodes = blendshapeToolkitCore.add_blend_shapes_from_template(
                meshes, template, asset_name, allow_renamed_nodes=True
            )
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        message_lines = []
        for position, mesh in enumerate(meshes):
            message_lines.append(
                self._build_added_message(mesh, nodes[position], existing_blend_shapes_per_mesh[position])
            )
        message = "\n".join(message_lines)
        if not asset_name:
            message += (
                f"\n\nNo asset name. Maya can't have two nodes with the same name: if another avatar with a "
                f"{nodes[0]} is imported, Maya quietly renames one of them to {nodes[0]}1, and anything that finds "
                "the node by its name will miss it."
            )
        QtWidgets.QMessageBox.information(self, "Blendshapes", message)

    def _build_added_message(self, mesh, node, existing_blend_shapes):
        mesh_name = mesh.split("|")[-1]
        is_skinned = maya_utilities.check_object_is_skeletal_mesh(mesh)

        if not existing_blend_shapes:
            if is_skinned:
                return f"Added {node} before the skinCluster."
            return f"Added {node} to {mesh_name}."

        if len(existing_blend_shapes) == 1:
            it_or_them = "it"
        else:
            it_or_them = "them"

        message = f"{mesh_name} already had {', '.join(existing_blend_shapes)}. {node} was added after {it_or_them}"
        if is_skinned:
            return message + " and before the skinCluster."
        return message + "."

    def handle_load_validate_mesh(self):
        try:
            self.validate_mesh = maya_utilities.get_user_mesh_selection()
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        mesh_name = self.validate_mesh.split("|")[-1]
        self.validate_mesh_label.setText(f"Mesh: {color_text(mesh_name, MESH_COLOR)}")
        blend_shape_nodes = maya_utilities.find_blend_shape_nodes(self.validate_mesh)

        self.validate_node_combo.blockSignals(True)
        self.validate_node_combo.clear()
        self.validate_node_combo.addItems(blend_shape_nodes)
        # start on the template's node if the mesh has it
        template = self._get_validate_template()
        if template is not None:
            template_node = blendshapeToolkitCore.find_template_node(self.validate_mesh, template)
            if template_node is not None:
                self.validate_node_combo.setCurrentIndex(blend_shape_nodes.index(template_node))
        self.validate_node_combo.blockSignals(False)

        self._show_validate_template()
        if not blend_shape_nodes:
            cmds.warning(f"{mesh_name} has no blendshape node. Use Create Blendshape from Template.")

    def handle_validate_template_changed(self, index):
        self._show_validate_template()

    def handle_validate_node_changed(self, index):
        self._show_validate_template()

    def handle_validate(self):
        template = self._get_validate_template()
        if template is None:
            cmds.warning("Pick a template to validate with.")
            return
        node = self.validate_node_combo.currentText()
        if not node:
            cmds.warning("Select a mesh with a blendshape node and click Load Selected Mesh first.")
            return

        try:
            check = blendshapeToolkitCore.validate_against_template(node, template)
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        self._show_check(check, template)

    def handle_add_missing_targets(self):
        template = self._get_validate_template()
        try:
            added_targets = blendshapeToolkitCore.add_missing_targets(
                self.validate_mesh, self.validate_node_combo.currentText(), template
            )
        except RuntimeError as error:
            cmds.warning(str(error))
            return

        if added_targets:
            message = f"Added {', '.join(added_targets)} after the last target."
        else:
            message = "Nothing was missing."
        QtWidgets.QMessageBox.information(self, "Blendshapes", message)

        # show the node as it is now
        self.handle_validate()

    def _ask_to_create_anyway(self, message):
        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle("Node name already used")
        message_box.setText(message)
        create_button = message_box.addButton("Create Anyway", QtWidgets.QMessageBox.AcceptRole)
        message_box.addButton(QtWidgets.QMessageBox.Cancel)
        message_box.exec()
        return message_box.clickedButton() == create_button


def showUI(open_validate_tab=False):
    """Opens the Templates window, on the Validate tab if asked, closing the old one first."""
    main_window = get_maya_main_window()
    for old_window in main_window.findChildren(QtWidgets.QDialog, WINDOW_OBJECT_NAME):
        old_window.close()
        old_window.deleteLater()

    try:
        ui = BlendShapeTemplatesUI(main_window)
    except RuntimeError as error:
        cmds.warning(str(error))
        return None

    if open_validate_tab:
        ui.tabs.setCurrentIndex(VALIDATE_TAB_INDEX)
    ui.show()
    return ui
