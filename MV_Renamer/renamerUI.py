from maya import cmds
from MV_UtilityScripts.Qt import QtWidgets, QtCore, QtGui
from MV_UtilityScripts import maya_utilities, object_utilities, constants_library
from importlib import reload
from . import renamer

reload(renamer)

class RenamerUI(QtWidgets.QDialog):

    def __init__(self):
        super().__init__(None)

        ## Initialize window properties
        self.setWindowTitle("Renamer")
        self.renamer_tool = renamer
        self.resize(700, 350)
        self.buildUI()
        self.refresh()

    def buildUI(self):
        print("Building UI")

        ## Create the **main vertical layout** to add everything inside
        layout = QtWidgets.QVBoxLayout()

        # Create the checkbox for showing objects with correct prefixes
        self.showCorrectPrefixesCheckbox = QtWidgets.QCheckBox("Show/Hide objects with correct prefixes")

        # Connect the stateChanged signal to the refresh method so the table updates when toggled
        self.showCorrectPrefixesCheckbox.stateChanged.connect(self.refresh)

        #  Create a horizontal layout for the checkbox, align it to the left
        checkbox_layout = QtWidgets.QHBoxLayout()
        checkbox_layout.addWidget(self.showCorrectPrefixesCheckbox)
        checkbox_layout.addStretch()  # Pushes checkbox to the left but how??

        # Add the checkbox layout to the main layout
        layout.addLayout(checkbox_layout)

        # Create table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)  # 4 columns
        self.table.setHorizontalHeaderLabels(["", "Name", "Detected Type", "Detected Prefix"])

        # Narrow down the tickbox column by setting a fixed width
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(0, 20)  # Adjust width as needed

        # Enable resizing of columns
        for col in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.Stretch)

        # Add the table to the same main layout
        layout.addWidget(self.table)

        # Create a horizontal layout for action buttons at the bottom
        button_layout = QtWidgets.QHBoxLayout()

        # Left-aligned buttons: Rename Selected and Rename All
        self.renameSelectedButton = QtWidgets.QPushButton("Rename Selected")
        self.renameSelectedButton.clicked.connect(self.rename_selected)
        button_layout.addWidget(self.renameSelectedButton)

        self.renameAllButton = QtWidgets.QPushButton("Rename All")
        self.renameAllButton.clicked.connect(self.rename_all)
        button_layout.addWidget(self.renameAllButton)

        # Spacer to push the Cancel button to the right
        button_layout.addStretch()

        # Right-aligned Cancel button
        self.cancelButton = QtWidgets.QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.close)
        button_layout.addWidget(self.cancelButton)

        layout.addLayout(button_layout)

        # ✅ Set the final layout (this is crucial)
        self.setLayout(layout)

    def refresh(self):
        print("Refreshed to show/hide objects with correct prefixes.")

        # Choose the data based on checkbox state:
        # If checked, show all objects; if not, show only objects needing renaming.
        if self.showCorrectPrefixesCheckbox.isChecked():
            data_to_display = self.renamer_tool.operable_objects["objects"]
        else:
            data_to_display = self.renamer_tool.obj_to_operate

        # Store the current data for later use (e.g., in rename_selected)
        self.current_data = data_to_display

        # Clear current table content
        self.table.setRowCount(0)

        # Loop through each object in the chosen data and insert it into the table
        for obj in data_to_display:
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)

            # Only add a tickbox if the object needs renaming
            if obj["PrefixStatus"] in ["no_prefix", "incorrect_prefix"]:
                checkbox = QtWidgets.QCheckBox()
                # Apply a style sheet to force a contrasting background
                checkbox.setStyleSheet("QCheckBox { background-color: darkGray; }")
                self.table.setCellWidget(row_index, 0, checkbox)
            else:
                self.table.setCellWidget(row_index, 0, None)

            # Create table items for each column (starting with column 1)
            name_item = QtWidgets.QTableWidgetItem(obj["Name"])
            type_item = QtWidgets.QTableWidgetItem(obj["DetectedType"])
            prefix_item = QtWidgets.QTableWidgetItem(obj["DetectedPrefix"])

            # Optional: Color code rows based on prefix status
            if obj["PrefixStatus"] == "no_prefix":
                color = QtGui.QColor("darkCyan")
            elif obj["PrefixStatus"] == "incorrect_prefix":
                color = QtGui.QColor("darkRed")
            else:  # For correct prefixes
                color = QtGui.QColor("darkGreen")

            # Apply the background color to each item
            name_item.setBackground(color)
            type_item.setBackground(color)
            prefix_item.setBackground(color)

            # Insert the items into the table.
            # Note: Column 0 is left blank (could be used later for a selection checkbox)
            self.table.setItem(row_index, 1, name_item)
            self.table.setItem(row_index, 2, type_item)
            self.table.setItem(row_index, 3, prefix_item)

    def rename_selected(self):
        pass
    def rename_all(self):
        pass


def showUI():
    ui = RenamerUI()
    ui.exec() ## No interaction with Maya UI, to prevent selection changes.

    return ui


