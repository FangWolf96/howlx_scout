from PyQt5 import QtWidgets, QtCore, QtGui

WIDTH, HEIGHT = 800, 480


class TechnicianMode(QtWidgets.QWidget):
    """
    Technician Mode shell.
    - Tile-based navigation
    - No sensor logic
    - No touch / gesture changes
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setStyleSheet("background-color:#0b0b0b; color:white;")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.hide()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # =========================
        # Header
        # =========================
        header = QtWidgets.QVBoxLayout()
        logo = QtWidgets.QLabel()
        pix = QtGui.QPixmap("assets/tech_logo.png").scaled(
            120, 120,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        logo.setPixmap(pix)
        logo.setAlignment(QtCore.Qt.AlignLeft)

        header.addWidget(logo)

        title = QtWidgets.QLabel("Technician Mode")
        title.setStyleSheet("font-size:32px; font-weight:700;")

        subtitle = QtWidgets.QLabel(
            "Advanced diagnostics, trends, and sensor-level analysis"
        )
        subtitle.setStyleSheet("font-size:16px; color:#aaaaaa;")

        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        # =========================
        # Tile grid
        # =========================
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(16)

        self.tiles = {}

        tiles = [
            ("📈 Analysis & Trends", self.open_charts),
            ("🧪 Sensor Diagnostics", self.open_diagnostics),
            ("⚙ Calibration (Coming Soon)", self.open_calibration),
        ]

        for i, (label, handler) in enumerate(tiles):
            tile = self._build_tile(label)
            tile.mousePressEvent = lambda e, h=handler: h()
            grid.addWidget(tile, i // 2, i % 2)

        root.addLayout(grid)
        root.addStretch()

        # =========================
        # Back button
        # =========================
        back = QtWidgets.QPushButton("← Back to Dashboard")
        back.setFixedHeight(44)
        back.setStyleSheet("""
            QPushButton {
                background:#1e1e1e;
                color:white;
                border-radius:10px;
                font-size:16px;
            }
            QPushButton:pressed {
                background:#111;
            }
        """)
        back.clicked.connect(self.close)
        root.addWidget(back)

    # =====================================================
    # Tile builder (safe, static)
    # =====================================================
    def _build_tile(self, text):
        frame = QtWidgets.QFrame()
        frame.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        frame.setStyleSheet("""
            QFrame {
                background:#151515;
                border-radius:16px;
            }
            QFrame:hover {
                background:#1c1c1c;
            }
        """)
        frame.setMinimumHeight(120)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("font-size:20px; font-weight:600;")

        sub = QtWidgets.QLabel("Tap to open")
        sub.setAlignment(QtCore.Qt.AlignCenter)
        sub.setStyleSheet("font-size:14px; color:#888888;")

        layout.addWidget(label)
        layout.addSpacing(6)
        layout.addWidget(sub)

        return frame

    # =====================================================
    # Navigation stubs (NO LOGIC YET)
    # =====================================================
    def open_charts(self):
        print("Technician → Analysis & Trends (stub)")
        # future: self.charts.show()

    def open_diagnostics(self):
        print("Technician → Sensor Diagnostics (stub)")
        # future: self.diagnostics.show()

    def open_calibration(self):
        print("Technician → Calibration (stub)")
        # future: self.calibration.show()
