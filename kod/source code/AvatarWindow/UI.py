from PyQt6 import QtCore
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class Ui_Avatar(QWidget):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        layout = QVBoxLayout()
        self.changeavatar = QLabel(self)
        self.changeavatar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.change = QPushButton("Изменить", self)
        layout.addWidget(self.changeavatar)
        layout.addWidget(self.change)
        self.setLayout(layout)
        self.retranslateUi(MainWindow)
        MainWindow.resize(400, 400)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Выбор аватара"))
        self.change.setText(_translate("MainWindow", "Изменить"))
