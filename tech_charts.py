from PyQt5 import QtWidgets, QtCore, QtGui

WIDTH, HEIGHT = 800, 480


class AnalysisTrends(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setStyleSheet("background:#0b0b0b; color:white;")
        self.hide()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QtWidgets.QLabel("Analysis & Trends")
        title.setStyleSheet("font-size:28px; font-weight:700;")
        root.addWidget(title)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setSpacing(24)

        layout.addWidget(self._severity_block(
            "TVOC",
            "Elevated chemical levels detected",
            "Recommended actions: Increase ventilation, reduce VOC sources"
        ))

        layout.addWidget(self._severity_block(
            "Carbon Dioxide (CO₂)",
            "CO₂ above optimal range",
            "Recommended actions: Improve fresh air exchange"
        ))

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        back = QtWidgets.QPushButton("← Back")
        back.clicked.connect(self.hide)
        root.addWidget(back)

    def _severity_block(self, title, finding, action):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background:#151515; border-radius:16px;")

        layout = QtWidgets.QVBoxLayout(frame)

        lbl = QtWidgets.QLabel(title)
        lbl.setStyleSheet("font-size:22px; font-weight:600;")
        layout.addWidget(lbl)

        bar = QtWidgets.QFrame()
        bar.setFixedHeight(140)
        bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 #2ecc71,
                    stop:0.5 #f1c40f,
                    stop:1 #e74c3c
                );
                border-radius:8px;
            }
        """)
        layout.addWidget(bar)

        layout.addWidget(QtWidgets.QLabel(f"Finding: {finding}"))
        layout.addWidget(QtWidgets.QLabel(f"Action: {action}"))

        return frame
