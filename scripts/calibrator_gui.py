#!/usr/bin/env python

import sys
import rospy
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

class CalibratorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        rospy.init_node('calibrator_gui_py', anonymous=True)
        self.init_ui()
        rospy.loginfo("Calibrator GUI (Python) Started")

    def init_ui(self):
        self.setWindowTitle('Calibrator GUI')
        self.setGeometry(100, 100, 400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        label = QLabel('Welcome to Calibrator GUI')
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        central_widget.setLayout(layout)

        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = CalibratorGUI()
    sys.exit(app.exec_())
