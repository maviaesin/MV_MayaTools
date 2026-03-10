from maya import cmds
from MV_UtilityScripts.Qt import QtWidgets, QtCore, QtGui
from MV_UtilityScripts import maya_utilities, object_utilities, constants_library
from MV_UtilityScripts.constants_library import SUFFIXES
from importlib import reload
from . import renamer
from .renamer import rename_objects, rename_materials, get_material_data

reload(renamer)


### pool of background colors used to distinguish objects with multiple materials
OBJECT_HIGHLIGHT_COLORS = [
    (180, 210, 240),  # blue
    (255, 200, 150),  # orange
    (200, 240, 200),  # green
    (240, 200, 240),  # purple
    (255, 245, 150),  # yellow
    (240, 190, 190),  # pink
    (180, 240, 240),  # cyan
    (220, 200, 170),  # tan
    (210, 195, 240),  # violet
    (195, 240, 215),  # mint
]


class RenamerUI(QtWidgets.QDialog):

    def __init__(self):
        """Initialize the Renamer UI window."""
        super().__init__(None)

        ### SET WINDOW PROPERTIES
        self.setWindowTitle("Renamer")
        self.renamer_tool = renamer
        self.resize(700, 250)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

        ### BUILD UI & LOAD DATA
        self.buildUI()
        self.refresh()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def buildUI(self):
        """Builds the UI layout and initializes UI components."""

        ### CREATE MAIN LAYOUT WITH TAB WIDGET
        main_layout = QtWidgets.QVBoxLayout()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_prefix_tab(), "Prefix")
        self.tabs.addTab(self._build_suffix_tab(), "Suffix")
        self.tabs.addTab(self._build_materials_tab(), "Materials")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    # ─────────────────────────────────────────
    # PREFIX TAB
    # ─────────────────────────────────────────

    def _build_prefix_tab(self):
        """Builds and returns the Prefix tab widget."""

        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        ### CHECKBOXES ROW
        checkbox_layout = QtWidgets.QHBoxLayout()

        self.showCorrectPrefixesCheckbox = QtWidgets.QCheckBox("Show/Hide objects with correct prefixes")
        self.showCorrectPrefixesCheckbox.stateChanged.connect(self.refresh)

        self.selectAllCheckbox = QtWidgets.QCheckBox("Select All")
        self.selectAllCheckbox.stateChanged.connect(self.toggle_all_checkboxes)

        checkbox_layout.addWidget(self.showCorrectPrefixesCheckbox)
        checkbox_layout.addWidget(self.selectAllCheckbox)
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)

        ### COLOR LEGEND
        self.legendLabel = QtWidgets.QLabel(
            '<span style="color: lightgray;">⬤ No Prefix</span> &nbsp; '
            '<span style="color: lightGreen;">⬤ Correct Prefix</span> &nbsp; '
            '<span style="color: #FFA500;">⬤ Incorrect Prefix</span>'
        )
        self.legendLabel.setAlignment(QtCore.Qt.AlignLeft)
        layout.addWidget(self.legendLabel)

        ### TABLE
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Name", "Detected Type", "Detected Prefix"])

        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(0, 20)

        for col in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.Stretch)

        layout.addWidget(self.table)

        ### ACTION BUTTONS
        button_layout = QtWidgets.QHBoxLayout()

        self.renameSelectedButton = QtWidgets.QPushButton("Rename Selected")
        self.renameSelectedButton.clicked.connect(self.handle_rename_selected)
        button_layout.addWidget(self.renameSelectedButton)

        self.renameAllButton = QtWidgets.QPushButton("Rename All")
        self.renameAllButton.clicked.connect(self.handle_rename_all)
        button_layout.addWidget(self.renameAllButton)

        button_layout.addStretch()

        self.cancelButton = QtWidgets.QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.close)
        button_layout.addWidget(self.cancelButton)

        layout.addLayout(button_layout)

        tab.setLayout(layout)
        return tab

    # ─────────────────────────────────────────
    # SUFFIX TAB
    # ─────────────────────────────────────────

    def _build_suffix_tab(self):
        """Builds and returns the Suffix tab widget."""

        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)

        ### PRESET SUFFIX BUTTONS
        preset_layout = QtWidgets.QHBoxLayout()

        self.lowButton = QtWidgets.QPushButton("_low")
        self.lowButton.clicked.connect(lambda: self.handle_add_suffix(SUFFIXES["low"]))
        preset_layout.addWidget(self.lowButton)

        self.highButton = QtWidgets.QPushButton("_high")
        self.highButton.clicked.connect(lambda: self.handle_add_suffix(SUFFIXES["high"]))
        preset_layout.addWidget(self.highButton)

        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        ### CUSTOM SUFFIX ROW
        custom_layout = QtWidgets.QHBoxLayout()

        custom_label = QtWidgets.QLabel("Custom:")
        self.customSuffixInput = QtWidgets.QLineEdit()
        self.customSuffixInput.setPlaceholderText("e.g. _UVTransfer")

        self.applyCustomButton = QtWidgets.QPushButton("Apply")
        self.applyCustomButton.clicked.connect(self.handle_add_custom_suffix)

        custom_layout.addWidget(custom_label)
        custom_layout.addWidget(self.customSuffixInput)
        custom_layout.addWidget(self.applyCustomButton)

        layout.addLayout(custom_layout)

        ### BOTTOM BUTTONS
        bottom_layout = QtWidgets.QHBoxLayout()

        self.removeSuffixButton = QtWidgets.QPushButton("Remove Suffix")
        self.removeSuffixButton.clicked.connect(self.handle_remove_suffix)
        bottom_layout.addWidget(self.removeSuffixButton)

        bottom_layout.addStretch()

        self.cancelSuffixButton = QtWidgets.QPushButton("Cancel")
        self.cancelSuffixButton.clicked.connect(self.close)
        bottom_layout.addWidget(self.cancelSuffixButton)

        layout.addLayout(bottom_layout)

        tab.setLayout(layout)
        return tab

    # ─────────────────────────────────────────
    # PREFIX METHODS
    # ─────────────────────────────────────────

    def refresh(self):
        """Refreshes the table data based on the current filter settings and resizes the window dynamically."""

        ### SELECT DATASET BASED ON CHECKBOX STATE
        if self.showCorrectPrefixesCheckbox.isChecked():
            data_to_display = self.renamer_tool.configure_operable_object_dictionary()["objects"]
        else:
            data_to_display = self.renamer_tool.exclude_objects_with_correct_prefixes()

        self.current_data = data_to_display
        self.row_checkboxes = []

        ### CLEAR TABLE CONTENT
        self.table.setRowCount(0)

        ### POPULATE TABLE WITH FILTERED OBJECTS
        for obj in data_to_display:

            if not obj["DetectedPrefix"]:
                continue

            row_index = self.table.rowCount()
            self.table.insertRow(row_index)

            ### ADD CHECKBOX FOR SELECTABLE ITEMS
            if obj["PrefixStatus"] in ["no_prefix", "incorrect_prefix"]:
                checkbox_widget = QtWidgets.QWidget()
                checkbox_layout = QtWidgets.QHBoxLayout()

                checkbox = QtWidgets.QCheckBox()
                checkbox.setStyleSheet("QCheckBox { background-color: White; color: black }")

                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                checkbox_widget.setLayout(checkbox_layout)

                self.table.setCellWidget(row_index, 0, checkbox_widget)
                self.row_checkboxes.append(checkbox)
            else:
                self.table.setCellWidget(row_index, 0, None)
                self.row_checkboxes.append(None)

            ### CREATE TABLE ITEMS
            name_item = QtWidgets.QTableWidgetItem(obj["Name"])
            type_item = QtWidgets.QTableWidgetItem(obj["DetectedType"])
            prefix_item = QtWidgets.QTableWidgetItem(obj["DetectedPrefix"])

            ### APPLY COLOR CODING
            if obj["PrefixStatus"] == "no_prefix":
                color = QtGui.QColor("lightgrey")
            elif obj["PrefixStatus"] == "incorrect_prefix":
                color = QtGui.QColor("#FFA500")
            else:
                color = QtGui.QColor("lightGreen")

            name_item.setForeground(color)
            type_item.setForeground(color)
            prefix_item.setForeground(color)

            self.table.setItem(row_index, 1, name_item)
            self.table.setItem(row_index, 2, type_item)
            self.table.setItem(row_index, 3, prefix_item)

        ### ADJUST WINDOW HEIGHT DYNAMICALLY
        row_count = self.table.rowCount()
        new_height = 250 + (row_count * 20)
        self.resize(700, min(new_height, 800))

    def get_checked_objects(self):
        """Returns a list of checked objects from the prefix table."""
        selected_objects_to_rename = []

        for row, checkbox in enumerate(self.row_checkboxes):
            if checkbox and checkbox.isChecked():
                obj_name = self.table.item(row, 1).text()
                obj_type = self.table.item(row, 2).text()

                for obj in renamer.configure_operable_object_dictionary()["objects"]:
                    if obj["Name"] == obj_name and obj["DetectedType"] == obj_type:
                        selected_objects_to_rename.append(obj)
                        break

        return selected_objects_to_rename

    def handle_rename_selected(self):
        """Renames only the checked objects in the prefix table."""
        selected_objects = self.get_checked_objects()
        if selected_objects:
            rename_objects(selected_objects)
        self.close()

    def handle_rename_all(self):
        """Renames all objects that need renaming."""
        rename_objects(renamer.exclude_objects_with_correct_prefixes())
        self.close()

    def toggle_all_checkboxes(self, state):
        """Toggles all prefix table checkboxes via the Select All checkbox."""
        is_checked = self.selectAllCheckbox.isChecked()
        for checkbox in self.row_checkboxes:
            if checkbox:
                checkbox.setChecked(is_checked)

    # ─────────────────────────────────────────
    # SUFFIX METHODS
    # ─────────────────────────────────────────

    def handle_add_suffix(self, suffix):
        """Applies a preset suffix to the current Maya selection."""
        renamer.add_suffix(suffix)
        self.close()

    def handle_add_custom_suffix(self):
        """Applies the custom suffix input to the current Maya selection."""
        suffix = self.customSuffixInput.text().strip()

        if not suffix:
            cmds.warning("Please enter a custom suffix.")
            return

        if not suffix.startswith("_"):
            suffix = f"_{suffix}"

        renamer.add_suffix(suffix)
        self.close()

    def handle_remove_suffix(self):
        """Removes any known suffix (preset or custom) from the current Maya selection."""
        custom = self.customSuffixInput.text().strip()
        if custom and not custom.startswith("_"):
            custom = f"_{custom}"

        known = list(SUFFIXES.values())
        if custom:
            known.append(custom)

        renamer.remove_suffix(known)
        self.close()


    # ─────────────────────────────────────────
    # MATERIALS TAB
    # ─────────────────────────────────────────

    def _build_materials_tab(self):
        """Sets up the Materials tab layout and widgets."""

        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)

        ### PREFIX SELECTOR ROW
        prefix_layout = QtWidgets.QHBoxLayout()
        prefix_label = QtWidgets.QLabel("Prefix:")
        prefix_layout.addWidget(prefix_label)

        self.prefixRadioM = QtWidgets.QRadioButton("M_")
        self.prefixRadioM.setChecked(True)
        self.prefixRadioMAT = QtWidgets.QRadioButton("MAT_")
        self.prefixRadioCustom = QtWidgets.QRadioButton("Custom:")
        self.prefixCustomInput = QtWidgets.QLineEdit()
        self.prefixCustomInput.setPlaceholderText("e.g. MTL_")
        self.prefixCustomInput.setMaximumWidth(100)
        self.prefixCustomInput.setEnabled(False)

        self.prefixRadioCustom.toggled.connect(
            lambda checked: self.prefixCustomInput.setEnabled(checked)
        )

        prefix_layout.addWidget(self.prefixRadioM)
        prefix_layout.addWidget(self.prefixRadioMAT)
        prefix_layout.addWidget(self.prefixRadioCustom)
        prefix_layout.addWidget(self.prefixCustomInput)
        prefix_layout.addStretch()
        layout.addLayout(prefix_layout)

        ### HIDE ALREADY-PREFIXED CHECKBOX
        self.hideCorrectMatPrefixCheckbox = QtWidgets.QCheckBox("Hide already-prefixed materials")
        self.hideCorrectMatPrefixCheckbox.stateChanged.connect(self.refresh_materials)
        layout.addWidget(self.hideCorrectMatPrefixCheckbox)

        ### MATERIALS TABLE
        self.materialsTable = QtWidgets.QTableWidget()
        self.materialsTable.setColumnCount(4)
        self.materialsTable.setHorizontalHeaderLabels(["", "Object", "Type", "Material Name"])

        self.materialsTable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.materialsTable.setColumnWidth(0, 20)
        for col in range(1, 4):
            self.materialsTable.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.Stretch)

        self.materialsTable.cellChanged.connect(self.on_mat_name_edited)
        layout.addWidget(self.materialsTable)

        ### ALSO AFFECTED BOX
        also_label = QtWidgets.QLabel("Also affected (shared materials, will also be updated):")
        layout.addWidget(also_label)
        self.alsoAffectedBox = QtWidgets.QPlainTextEdit()
        self.alsoAffectedBox.setReadOnly(True)
        layout.addWidget(self.alsoAffectedBox)

        ### EXCLUDED (LAMBERT1) BOX
        excluded_label = QtWidgets.QLabel(
            '<span style="color: #FFA500;">&#9888;  Maya\'s default material lambert1 shouldn\'t be edited. '
            'Please assign a different material to make changes:</span>'
        )
        layout.addWidget(excluded_label)
        self.excludedBox = QtWidgets.QPlainTextEdit()
        self.excludedBox.setReadOnly(True)
        self.excludedBox.setMaximumHeight(60)
        layout.addWidget(self.excludedBox)

        ### BOTTOM BUTTONS
        mat_button_layout = QtWidgets.QHBoxLayout()

        self.renameSelectedMatsButton = QtWidgets.QPushButton("Rename Selected")
        self.renameSelectedMatsButton.clicked.connect(self.handle_rename_selected_materials)
        mat_button_layout.addWidget(self.renameSelectedMatsButton)

        self.renameAllMatsButton = QtWidgets.QPushButton("Rename All")
        self.renameAllMatsButton.clicked.connect(self.handle_rename_all_materials)
        mat_button_layout.addWidget(self.renameAllMatsButton)

        mat_button_layout.addStretch()

        self.cancelMatsButton = QtWidgets.QPushButton("Cancel")
        self.cancelMatsButton.clicked.connect(self.close)
        mat_button_layout.addWidget(self.cancelMatsButton)

        layout.addLayout(mat_button_layout)

        tab.setLayout(layout)
        return tab

    def _on_tab_changed(self, index):
        """Reloads the materials table whenever the user switches to the Materials tab."""
        if self.tabs.tabText(index) == "Materials":
            self.refresh_materials()

    def refresh_materials(self):
        """Clears and rebuilds the materials table from whatever is currently selected in Maya."""

        ### block cellChanged while we fill the table so it doesnt fire on our own inserts
        self._populating_materials = True
        self.materialsTable.setRowCount(0)
        self.mat_row_checkboxes = []
        self.mat_row_data = []
        self.mat_original_names = {}

        rows, also_affected, lambert1_objects = get_material_data()

        ### filter out already-prefixed materials if the checkbox is on
        if self.hideCorrectMatPrefixCheckbox.isChecked():
            filtered_rows = []
            for r in rows:
                if r["PrefixStatus"] != "has_prefix":
                    filtered_rows.append(r)
            rows = filtered_rows

        ### count how many materials each object has
        object_count = {}
        for row in rows:
            obj = row["AssignedTo"]
            object_count[obj] = object_count.get(obj, 0) + 1

        ### build a color map for objects with more than one material
        object_color_map = {}
        color_index = 0
        for obj, count in object_count.items():
            if count > 1:
                r, g, b = OBJECT_HIGHLIGHT_COLORS[color_index % len(OBJECT_HIGHLIGHT_COLORS)]
                object_color_map[obj] = (r, g, b)
                color_index += 1

        ### POPULATE TABLE
        for row_data in rows:
            row_index = self.materialsTable.rowCount()
            self.materialsTable.insertRow(row_index)

            self.mat_original_names[row_index] = row_data["Name"]

            ### CHECKBOX
            checkbox_widget = QtWidgets.QWidget()
            cb_layout = QtWidgets.QHBoxLayout()
            checkbox = QtWidgets.QCheckBox()
            checkbox.setStyleSheet("QCheckBox { background-color: White; color: black }")
            cb_layout.addWidget(checkbox)
            cb_layout.setAlignment(QtCore.Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_widget.setLayout(cb_layout)
            self.materialsTable.setCellWidget(row_index, 0, checkbox_widget)
            self.mat_row_checkboxes.append(checkbox)
            self.mat_row_data.append(row_data)

            ### OBJECT CELL
            object_item = QtWidgets.QTableWidgetItem(row_data["AssignedTo"])
            object_item.setFlags(object_item.flags() & ~QtCore.Qt.ItemIsEditable)

            ### if this object has multiple materials, give it a pool color with black text
            if row_data["AssignedTo"] in object_color_map:
                r, g, b = object_color_map[row_data["AssignedTo"]]
                object_item.setBackground(QtGui.QColor(r, g, b))
                object_item.setForeground(QtGui.QColor("black"))

            ### TYPE CELL
            type_item = QtWidgets.QTableWidgetItem(row_data["Type"])
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)

            ### MATERIAL NAME CELL (editable)
            name_item = QtWidgets.QTableWidgetItem(row_data["Name"])
            name_item.setFlags(name_item.flags() | QtCore.Qt.ItemIsEditable)

            ### COLOR CODING
            if row_data["PrefixStatus"] == "has_prefix":
                color = QtGui.QColor("lightGreen")
            elif row_data["IsAutoNamed"]:
                color = QtGui.QColor("orange")
            else:
                color = QtGui.QColor("lightgrey")

            type_item.setForeground(color)
            name_item.setForeground(color)

            self.materialsTable.setItem(row_index, 1, object_item)
            self.materialsTable.setItem(row_index, 2, type_item)
            self.materialsTable.setItem(row_index, 3, name_item)

        self._populating_materials = False

        ### ALSO AFFECTED BOX
        if also_affected:
            lines = []
            for obj, mat in also_affected:
                lines.append(f"* {obj}  (uses {mat})")
            self.alsoAffectedBox.setPlainText("\n".join(lines))
        else:
            self.alsoAffectedBox.setPlainText("")

        ### EXCLUDED BOX
        if lambert1_objects:
            self.excludedBox.setPlainText(", ".join(lambert1_objects))
        else:
            self.excludedBox.setPlainText("")

    def on_mat_name_edited(self, row, col):
        """Highlights the material name cell if the user changed it from the original."""
        if getattr(self, '_populating_materials', False):
            return
        if col != 3:
            return

        item = self.materialsTable.item(row, col)
        if not item:
            return

        original = self.mat_original_names.get(row, "")

        ### if the name changed, give it a yellow background with black text so its readable
        if item.text() != original:
            item.setBackground(QtGui.QColor(255, 245, 150))
            item.setForeground(QtGui.QColor("black"))
        else:
            ### user typed back the original, reset background and restore the status color
            item.setData(QtCore.Qt.BackgroundRole, None)
            if row < len(self.mat_row_data):
                row_data = self.mat_row_data[row]
                if row_data["PrefixStatus"] == "has_prefix":
                    item.setForeground(QtGui.QColor("lightGreen"))
                elif row_data["IsAutoNamed"]:
                    item.setForeground(QtGui.QColor("orange"))
                else:
                    item.setForeground(QtGui.QColor("lightgrey"))

    def _get_selected_prefix(self):
        """Reads which prefix the user picked and returns it as a string."""
        if self.prefixRadioM.isChecked():
            return "M_"
        elif self.prefixRadioMAT.isChecked():
            return "MAT_"
        else:
            custom = self.prefixCustomInput.text().strip()
            if not custom:
                cmds.warning("Please enter a custom prefix.")
                return None
            if not custom.endswith("_"):
                custom = f"{custom}_"
            return custom

    def _collect_mat_rows_from_table(self, selected_only=False):
        """Reads the table and returns a list of material dicts ready for renaming.
        Picks up any name edits the user made directly in the table."""
        result = []
        for row_index in range(len(self.mat_row_checkboxes)):
            checkbox = self.mat_row_checkboxes[row_index]
            row_data = self.mat_row_data[row_index]

            if selected_only and not checkbox.isChecked():
                continue

            ### grab the name from the table cell in case the user edited it
            edited_name = self.materialsTable.item(row_index, 3).text()

            entry = dict(row_data)
            entry["Name"] = edited_name
            result.append(entry)

        return result

    def handle_rename_selected_materials(self):
        """Renames only the materials that are checked in the table."""
        prefix = self._get_selected_prefix()
        if prefix is None:
            return
        mat_list = self._collect_mat_rows_from_table(selected_only=True)
        if mat_list:
            rename_materials(mat_list, prefix)
        self.close()

    def handle_rename_all_materials(self):
        """Renames every material shown in the table."""
        prefix = self._get_selected_prefix()
        if prefix is None:
            return
        mat_list = self._collect_mat_rows_from_table(selected_only=False)
        rename_materials(mat_list, prefix)
        self.close()


def showUI():
    """
    Launches the Renamer UI as a modal dialog.
    Prevents interaction with the Maya UI while open.
    Warns the user if nothing is selected.
    """
    try:
        maya_utilities.get_user_object_selection()
    except RuntimeError as e:
        cmds.warning(str(e))
        return

    ui = RenamerUI()
    ui.exec()

    return ui
