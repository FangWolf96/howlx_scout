from PyQt5 import QtWidgets, QtGui, QtCore

WIDTH, HEIGHT = 800, 480

class TechnicianMode(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color:#0b0b0b; color:white;")
        self.hide()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ---------------------------
        # Header
        # ---------------------------
        header = QtWidgets.QHBoxLayout()

        title = QtWidgets.QLabel("Technician Mode")
        title.setStyleSheet("font-size:28px; font-weight:700;")
        header.addWidget(title)

        header.addStretch()

        root.addLayout(header)

        subtitle = QtWidgets.QLabel(
            "Advanced diagnostics, trends, and sensor-level analysis"
        )
        subtitle.setStyleSheet("font-size:14px; color:#aaaaaa;")
        root.addWidget(subtitle)

        # ---------------------------
        # Placeholder chart panel
        # ---------------------------
        panel = QtWidgets.QFrame()
        panel.setStyleSheet("""
            QFrame {
                background:#141414;
                border-radius:16px;
                border:1px dashed #333;
            }
        """)
        panel_layout = QtWidgets.QVBoxLayout(panel)

        placeholder = QtWidgets.QLabel(
            "📈 Analysis charts will appear here\n\n"
            "• PM2.5 rolling trends\n"
            "• CO₂ decay / ventilation response\n"
            "• VOC baseline drift\n"
            "• Raw vs processed sensor data"
        )
        placeholder.setAlignment(QtCore.Qt.AlignCenter)
        placeholder.setStyleSheet("font-size:16px; color:#777777;")

        panel_layout.addStretch()
        panel_layout.addWidget(placeholder)
        panel_layout.addStretch()

        root.addWidget(panel, stretch=1)

        # ---------------------------
        # Footer
        # ---------------------------
        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()

        back = QtWidgets.QPushButton("← Back to Dashboard")
        back.setFixedHeight(44)
        back.clicked.connect(self.hide)

        footer.addWidget(back)
        root.addLayout(footer)
