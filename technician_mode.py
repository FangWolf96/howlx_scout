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
        from tech_charts import AnalysisTrends
        from tech_diagnostics import SensorDiagnostics

        self.charts = AnalysisTrends(self)
        self.diagnostics = SensorDiagnostics(self)


        # =========================
        # Header
        # =========================
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(16)

        logo = QtWidgets.QLabel()
        pix = QtGui.QPixmap("assets/tech_logo.png").scaled(
            140, 140,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        logo.setPixmap(pix)
        logo.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        header.addWidget(logo)

        title_stack = QtWidgets.QVBoxLayout()
        title_stack.setAlignment(QtCore.Qt.AlignTop)
        title_stack.setSpacing(4)

        title = QtWidgets.QLabel("Technician Mode")
        title.setStyleSheet("font-size:34px; font-weight:700;")

        subtitle = QtWidgets.QLabel(
            "Advanced diagnostics, trends, and sensor-level analysis"
        )
        subtitle.setStyleSheet("font-size:16px; color:#aaaaaa;")

        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        title_stack.addStretch()

        header.addLayout(title_stack)
        header.addStretch()

        root.addLayout(header)

        # =========================
        # Scroll container
        # =========================
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(240)

        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)


        # =========================
        # Tile grid
        # =========================
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(16)

        tiles = [
            ("Analysis & Trends", "assets/icons/analysis.svg", self.open_charts),
            ("Sensor Diagnostics", "assets/icons/sensors.svg", self.open_diagnostics),
            ("Calibration (Coming Soon)", "assets/icons/calibration.svg", self.open_calibration),
        ]


        for i, (label, icon, handler) in enumerate(tiles):
            tile = self._build_tile(label, icon)
            tile.mousePressEvent = lambda e, h=handler: h()
            grid.addWidget(tile, i // 2, i % 2)
        
        scroll_layout.addLayout(grid)
        scroll.setWidget(scroll_widget)
        root.addWidget(scroll, stretch=1)

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
    # Tile builder
    # =====================================================
    def _build_tile(self, text, icon_path):
        frame = QtWidgets.QFrame()
        frame.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        frame.setStyleSheet("""
            QFrame {
                background:#151515;
                border-radius:18px;
            }
            QFrame:hover {
                background:#1f1f1f;
            }
        """)
        frame.setMinimumHeight(140)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10)

        icon = QtWidgets.QLabel()
        icon.setAlignment(QtCore.Qt.AlignCenter)
        icon.setPixmap(
            QtGui.QPixmap(icon_path).scaled(
                48, 48,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )

        title = QtWidgets.QLabel(text)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("font-size:20px; font-weight:600;")

        sub = QtWidgets.QLabel("Tap to open")
        sub.setAlignment(QtCore.Qt.AlignCenter)
        sub.setStyleSheet("font-size:14px; color:#888888;")

        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addStretch()

        return frame

    # =====================================================
    # Navigation stubs
    # =====================================================
    def open_charts(self):
        self.charts.show()
        self.charts.raise_()


    def open_diagnostics(self):
        self.diagnostics.show()
        self.diagnostics.raise_()


    def open_calibration(self):
        print("Technician → Calibration (stub)")
