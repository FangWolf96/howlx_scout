from PyQt5 import QtWidgets, QtCore

WIDTH, HEIGHT = 800, 480


class SensorDiagnostics(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setStyleSheet("background:#0b0b0b; color:white;")
        self.hide()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        title = QtWidgets.QLabel("Sensor Diagnostics")
        title.setStyleSheet("font-size:28px; font-weight:700;")
        root.addWidget(title)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Sensor", "Status", "Value", "Last Update"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("QTableWidget { background:#151515; }")

        root.addWidget(self.table, stretch=1)

        back = QtWidgets.QPushButton("← Back")
        back.clicked.connect(self.hide)
        root.addWidget(back)

    def update(self, sensor_state):
        self.table.setRowCount(0)
        for name, data in sensor_state.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(data["status"]))
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(data["value"])))
            self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(data["last"]))
