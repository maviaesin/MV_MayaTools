from maya import cmds
from MV_UtilityScripts.Qt import QtWidgets, QtCore, QtGui
from MV_UtilityScripts import maya_utilities, object_utilities, constants_library
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

        ### CREATE MAIN LAYOUT
        layout = QtWidgets.QVBoxLayout()

        ### CREATE CHECKBOXES FOR DISPLAY OPTIONS
        checkbox_layout = QtWidgets.QHBoxLayout()

        # Checkbox to show/hide objects with correct prefixes
        self.showCorrectPrefixesCheckbox = QtWidgets.QCheckBox("Show/Hide objects with correct prefixes")
        self.showCorrectPrefixesCheckbox.stateChanged.connect(self.refresh)

        # Checkbox to select/deselect all items
        self.selectAllCheckbox = QtWidgets.QCheckBox("Select All")
        self.selectAllCheckbox.stateChanged.connect(self.toggle_all_checkboxes)

        checkbox_layout.addWidget(self.showCorrectPrefixesCheckbox)
        checkbox_layout.addWidget(self.selectAllCheckbox)
        checkbox_layout.addStretch()

        layout.addLayout(checkbox_layout)

        ### ADD COLOR LEGEND
        self.legendLabel = QtWidgets.QLabel(
            '<span style="color: lightgray;">⬤ No Prefix</span> &nbsp; '
            '<span style="color: lightGreen;">⬤ Correct Prefix</span> &nbsp; '
            '<span style="color: Red;">⬤ Incorrect Prefix</span>'
        )
        self.legendLabel.setAlignment(QtCore.Qt.AlignLeft)
        layout.addWidget(self.legendLabel)

        ### CREATE TABLE FOR DISPLAYING OBJECTS
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", "Name", "Detected Type", "Detected Prefix"])

        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(0, 20)

        for col in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.Stretch)

        layout.addWidget(self.table)

        ### CREATE ACTION BUTTONS
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

        ### SET FINAL LAYOUT
        self.setLayout(layout)

    def refresh(self):
        """Refreshes the table data based on the current filter settings and resizes the window dynamically."""

        ### SELECT DATASET BASED ON CHECKBOX STATE
        if self.showCorrectPrefixesCheckbox.isChecked():
            data_to_display = self.renamer_tool.configure_operable_object_dictionary()["objects"]
        else:
            data_to_display = self.renamer_tool.exclude_objects_with_correct_prefixes()

        self.current_data = data_to_display

        ### CLEAR TABLE CONTENT
        self.table.setRowCount(0)

        ### POPULATE TABLE WITH FILTERED OBJECTS
        for obj in data_to_display:

            if not obj["DetectedPrefix"]:  # Skip objects without a detected prefix
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
            else:
                self.table.setCellWidget(row_index, 0, None)

            ### CREATE TABLE ITEMS
            name_item = QtWidgets.QTableWidgetItem(obj["Name"])
            type_item = QtWidgets.QTableWidgetItem(obj["DetectedType"])
            prefix_item = QtWidgets.QTableWidgetItem(obj["DetectedPrefix"])

            ### APPLY COLOR CODING BASED ON PREFIX STATUS
            if obj["PrefixStatus"] == "no_prefix":
                color = QtGui.QColor("lightgrey")
            elif obj["PrefixStatus"] == "incorrect_prefix":
                color = QtGui.QColor("Red")
            else:
                color = QtGui.QColor("lightGreen")

            name_item.setForeground(color)
            type_item.setForeground(color)
            prefix_item.setForeground(color)

            ### ADD ITEMS TO TABLE
            self.table.setItem(row_index, 1, name_item)
            self.table.setItem(row_index, 2, type_item)
            self.table.setItem(row_index, 3, prefix_item)

        ### ADJUST WINDOW SIZE DYNAMICALLY
        row_count = self.table.rowCount()
        new_height = 250 + (row_count * 20)
        max_height = 800
        self.resize(700, min(new_height, max_height))

    def get_checked_objects(self):
        """
        Retrieves objects that have their checkboxes checked in the UI table.
        Returns a list of selected objects for renaming.
        """
        selected_objects_to_rename = []

        ### LOOP THROUGH TABLE ROWS TO CHECK CHECKBOX STATES
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)

            if widget:
                checkbox = widget.findChild(QtWidgets.QCheckBox)

                if checkbox and checkbox.isChecked():
                    obj_name = self.table.item(row, 1).text()
                    obj_type = self.table.item(row, 2).text()

                    ### MATCH WITH OPERABLE OBJECTS LIST
                    for obj in renamer.configure_operable_object_dictionary()["objects"]:
                        if obj["Name"] == obj_name and obj["DetectedType"] == obj_type:
                            selected_objects_to_rename.append(obj)
                            break

        return selected_objects_to_rename

    def handle_rename_selected(self):
        """Renames only the objects that have their checkboxes checked in the UI."""

        selected_objects = self.get_checked_objects()

        if selected_objects:
            rename_objects(selected_objects)

        self.close()

    def handle_rename_all(self):
        """Renames all objects that need renaming and closes the UI."""

        rename_objects(renamer.exclude_objects_with_correct_prefixes())
        self.close()

    def toggle_all_checkboxes(self, state):
        """
        Toggles all checkboxes based on the state of the 'Select All' checkbox.
        """
        is_checked = self.selectAllCheckbox.isChecked()

        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)

            if widget:
                checkbox = widget.findChild(QtWidgets.QCheckBox)

                if checkbox:
                    checkbox.setChecked(is_checked)


def showUI():
    """
    Launches the Renamer UI as a modal dialog.
    Prevents interaction with the Maya UI while open.
    """
    ui = RenamerUI()
    ui.exec()

    return ui
