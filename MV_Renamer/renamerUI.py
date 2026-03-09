from maya import cmds
from MV_UtilityScripts.Qt import QtWidgets, QtCore, QtGui
from MV_UtilityScripts import maya_utilities, object_utilities, constants_library
from MV_UtilityScripts.constants_library import SUFFIXES
from importlib import reload
from . import renamer
from .renamer import rename_objects

reload(renamer)


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
            '<span style="color: lightRed;">⬤ Incorrect Prefix</span>'
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
                color = QtGui.QColor("Red")
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
