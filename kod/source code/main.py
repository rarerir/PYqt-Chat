import time
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QApplication, QMenu, QFileDialog
from RegistrationForm.UI import Ui_regform
from MainWindow.UI import Ui_chat
from AvatarWindow.UI import Ui_Avatar
import sqlite3
import typing
import sys
import os
from datetime import datetime
from threading import Thread
import traceback

CON = sqlite3.connect('..\\chat.db')
CUR = CON.cursor()


class Message:
    def __init__(self, _id, text, _time, user_id, server_id, isdeleted):
        self.id = _id
        self.text = text
        self.time = _time
        self.user_id = user_id
        self.server_id = server_id
        self.isdeleted = isdeleted

    def getdate(self):
        return self.time[11::]

    def __str__(self):
        return f'{self.id} + {self.text} + {self.time} + {self.user_id} + {self.server_id} + {self.isdeleted}'


class Regform(Ui_regform):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.passwd.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.securetype.toggled.connect(self.passwdshow)
        self.signin.clicked.connect(self.log)
        self.regist.clicked.connect(self.sign)
        self.account: typing.Optional[list[tuple]] = None
        self.chatwindow: typing.Optional[MainWindow] = None
        try:
            self.checkforsaved()
        except Exception as ex:
            self.res.setText("Ошибка при чтении файла сохранённого аккаунта: " + str(ex))

    def passwdshow(self):
        if str(self.securetype.checkState()) == 'CheckState.Checked':
            self.passwd.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
        else:
            self.passwd.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

    def checkforsaved(self):
        with open("savedacc.txt", "r") as f:
            a = f.readlines()
            if a:
                self.nickname.setText(a[0])
                self.passwd.setText(a[1])

    def remember(self):
        with open("savedacc.txt", "w+") as f:
            f.write(f'{self.nickname.text()}\n{self.passwd.text()}')

    def sign(self):
        try:
            if len(self.nickname.text().strip()) > 30 or len(self.passwd.text().strip()) > 70:
                raise ValueError("Слишком большой ник/пароль")
            CUR.execute("INSERT INTO accounts VALUES (NULL, ?, ?, 0, 0, NULL)",
                        (self.nickname.text().strip(), self.passwd.text().strip()))
            print("Регистрация прошла успешно")
        except Exception as ex:
            self.res.setText("Произошла ошибка: " + str(ex))

    def log(self):
        try:
            self.account = CUR.execute("SELECT * FROM accounts WHERE (nickname, password) = (?, ?)",
                                       (self.nickname.text().strip(), self.passwd.text().strip())).fetchone()
            if self.account:
                if self.account[3] == 0:
                    self.chatwindow = MainWindow(self.account[4], self.account)
                    self.chatwindow.show()
                    CUR.execute('UPDATE accounts SET isActive = ? WHERE ID = ?', (1, self.account[0]))
                    CON.commit()
                    print("Вход завершён")
                    if str(self.doyoremember21stnight.checkState()) == 'CheckState.Checked':
                        self.remember()
                    self.hide()
                else:
                    self.res.setText("Произошла ошибка: аккаунт уже активен")
                    raise ValueError("Произошла ошибка: аккаунт уже активен")
            else:
                self.res.setText("Произошла ошибка: логин или пароль неправильные")
                raise ValueError("Произошла ошибка: логин или пароль неправильные")
        except Exception as ex:
            self.res.setText("Произошла ошибка: " + str(ex))

    def closeEvent(self, _: typing.Optional[QtGui.QCloseEvent]):
        try:
            CUR.execute('UPDATE accounts SET isActive = ? WHERE ID = ?', (0, self.account[0]))
            CON.commit()
        except Exception as ex:
            print(ex)
            pass


# Главное окно
class MainWindow(Ui_chat):
    def __init__(self, isadmin, account):
        super().__init__()
        self.isadmin = isadmin
        self.account = account
        self.item = None
        self.maxid = None
        self.setupUi(self)

        self.send.clicked.connect(self.send_message)
        self.avatar.clicked.connect(self.avatare)
        self.update.clicked.connect(self.updatems)
        self.signout.clicked.connect(self.signoute)
        self.nicklabel.setText(QtCore.QCoreApplication.translate("chat", f"Добро пожаловать {account[1]}!"))
        self.serverpick.currentTextChanged.connect(self.parse_messages)

        self.context_menu = QMenu(self)
        self.chatbox.installEventFilter(self)

        self.parse_servers()
        self.detectavatars()
        self.parse_messages()

        self.awindow = Avatar(self.account)

        self.closedflag = False
        self.tread = Thread(target=self.updatethread)
        self.tread.start()

    def parse_servers(self):
        try:
            self.serverpick.currentTextChanged.disconnect(self.parse_messages)
            isold = False
            servers = CUR.execute("SELECT name FROM servers").fetchall()
            if self.serverpick.currentText():
                olds = self.serverpick.currentText()

                self.serverpick.clear()
                for i in servers:
                    if olds in i[0]:
                        isold = True
                    self.serverpick.addItem(i[0])
                if isold:
                    self.serverpick.setCurrentText(olds)
                self.serverpick.currentTextChanged.connect(self.parse_messages)
                self.parse_messages()
            else:
                self.serverpick.clear()
                for i in servers:
                    self.serverpick.addItem(i[0])
                self.serverpick.currentTextChanged.connect(self.parse_messages)
        except Exception as ex:
            print("Парсинг серверов завершён с ошибкой: " + str(ex))

    def parse_messages(self):
        try:
            messages = CUR.execute(
                "SELECT * FROM message WHERE `server-id` = (SELECT ID FROM servers WHERE name = ?)",
                (str(self.serverpick.currentText()),)).fetchall()
            self.chatbox.clear()
            if messages:
                # Обработка сообщений для админов
                if self.isadmin == 1:
                    for i in messages:
                        message = Message(i[0], i[1], i[2], i[3], i[4], i[5])
                        path = f'{message.user_id}.jpg'
                        print(path)
                        icon = QtGui.QIcon(path)
                        if message.isdeleted == 1:
                            rq = "SELECT nickname FROM accounts WHERE ID = ?"
                            it = QtWidgets.QListWidgetItem(icon, f'[{message.getdate()}]'
                                                                 f' {CUR.execute(rq, (message.user_id,)).fetchone()[0]}'
                                                                 f': {message.text} {message.id} [БЫЛО УДАЛЕНО]')
                            self.chatbox.addItem(it)
                        else:
                            rq = "SELECT nickname FROM accounts WHERE ID = ?"
                            it = QtWidgets.QListWidgetItem(icon, f'[{message.getdate()}]'
                                                                 f' {CUR.execute(rq, (message.user_id,)).fetchone()[0]}'
                                                                 f': {message.text} {message.id}')
                            self.chatbox.addItem(it)
                        self.chatbox.setCurrentRow(len(self.chatbox) - 1)
                        self.chatbox.currentItem().setData(4, message)
                    print("Парсинг сообщений завершён успешно")
                    self.chatbox.scrollToBottom()
                # Обработка сообщений для обычных пользователей
                else:
                    for i in messages:
                        message = Message(i[0], i[1], i[2], i[3], i[4], i[5])
                        if message.isdeleted == 1:
                            pass
                        else:
                            path = f'{message.user_id}.jpg'
                            icon = QtGui.QIcon(path)
                            rq = "SELECT nickname FROM accounts WHERE ID = ?"
                            it = QtWidgets.QListWidgetItem(icon, f'[{message.getdate()}]'
                                                                 f' {CUR.execute(rq, (message.user_id,)).fetchone()[0]}'
                                                                 f': {message.text}')
                            self.chatbox.addItem(it)
                            self.chatbox.setCurrentRow(len(self.chatbox) - 1)
                            self.chatbox.currentItem().setData(4, message)
                    print("Парсинг сообщений завершён успешно")
                    self.chatbox.scrollToBottom()
        except Exception as ex:
            print("Парсинг сообщений завершён с ошибкой: " + str(ex))

    def detectavatars(self):
        accounts = CUR.execute("SELECT * FROM accounts").fetchall()
        _id = None
        for i in accounts:
            binary = i[5]
            _id = i[0]
            self.convert_data(binary, _id)
        self.maxid = _id

    def updatethread(self):
        while self.closedflag is False:
            self.update.clicked.emit()
            time.sleep(5)

    def updatems(self):
        self.parse_servers()
        self.detectavatars()
        self.parse_messages()

    def send_message(self):
        try:
            ctime = str(datetime.now())[0:19:1]
            sid = CUR.execute("SELECT ID FROM servers WHERE name = ?",
                              (str(self.serverpick.currentText()),)).fetchone()
            if self.message.text():
                CUR.execute("INSERT INTO message VALUES (NULL, ?, ?, ?, ?, 0)",
                            (self.message.text(), ctime, self.account[0], sid[0]))
                CON.commit()
                r = "SELECT * FROM message WHERE "
                r += "(`text`, `date`, `user-id`, `server-id`, `isDeleted`) = (?, ?, ?, ?, ?)"
                a = CUR.execute(r,
                                (self.message.text(), ctime, self.account[0], sid[0], 0)).fetchone()
                msg = Message(a[0], a[1], a[2], a[3], a[4], a[5])
                path = f'{msg.user_id}.jpg'
                icon = QtGui.QIcon(path)
                rq = "SELECT nickname FROM accounts WHERE ID = ?"
                item = QtWidgets.QListWidgetItem(icon, f'[{msg.getdate()}]'
                                                       f' {CUR.execute(rq, (msg.user_id,)).fetchone()[0]}'
                                                       f': {msg.text}')
                self.chatbox.addItem(item)
                self.chatbox.setCurrentRow(len(self.chatbox) - 1)
                self.chatbox.currentItem().setData(4, msg)
                self.message.setText("")
            else:
                raise ValueError("не надо")
            print("Сообщение было отправлено")
            self.chatbox.scrollToBottom()
        except Exception as ex:
            print("Отправка сообщения завершена с ошибкой: " + str(ex))

    def deletemsg(self):
        if self.isadmin == 1:
            if self.chatbox.selectedItems():
                print("Выбранное сообщение: " + str(self.item.data(4).id))
                CUR.execute('UPDATE message SET isDeleted = ? WHERE ID = ?', (1, self.item.data(4).id,))
                CON.commit()
                self.parse_messages()
        else:
            print("Выбранное сообщение: " + str(self.item.data(4).id))
            CUR.execute('UPDATE message SET isDeleted = ? WHERE ID = ?', (1, self.item.data(4).id,))
            CON.commit()
            self.parse_messages()

    def deletefrombd(self):
        print(self.chatbox.selectedItems())
        if self.chatbox.selectedItems():
            print("Выбранное сообщение: " + str(self.item.data(4).id))
            CUR.execute('DELETE FROM message WHERE ID = ?', (self.item.data(4).id,))
            CON.commit()
            self.parse_messages()

    def answere(self):
        answernickname = CUR.execute("SELECT nickname FROM accounts WHERE ID = ?",
                                     (self.item.data(4).user_id,)).fetchone()[0]
        self.message.setText(f"Ответ {answernickname}'у:")

    def signoute(self):
        CUR.execute('UPDATE accounts SET isActive = ? WHERE ID = ?', (0, self.account[0]))
        CON.commit()
        self.hide()
        exe.show()

    def eventFilter(self, source, event):
        # Фильтр событий
        if str(event.type()) == 'Type.ContextMenu' or str(event.type()) == '82' and source is self.chatbox:

            if self.chatbox.currentItemChanged:
                self.item = self.chatbox.selectedItems()[0]
                print("Контекстное меню вызвано")
                # Проверка на привилегии пользователя
                if self.isadmin == 1:
                    self.context_menu.clear()
                    delete = self.context_menu.addAction("Удалить")
                    deletefrombd = self.context_menu.addAction("Удалить из БД")
                    if self.item.data(4).user_id != self.account[0]:
                        answer = self.context_menu.addAction("Ответить")
                        answer.triggered.connect(self.answere)
                    delete.triggered.connect(self.deletemsg)
                    deletefrombd.triggered.connect(self.deletefrombd)
                    self.context_menu.exec(event.globalPos())
                    return True
                else:
                    self.context_menu.clear()
                    # Проверка на ник
                    if self.item.data(4).user_id == self.account[0]:
                        delete = self.context_menu.addAction("Удалить")
                        delete.triggered.connect(self.deletemsg)
                        self.context_menu.exec(event.globalPos())
                    else:
                        answer = self.context_menu.addAction("Ответить")
                        answer.triggered.connect(self.answere)
                        self.context_menu.exec(event.globalPos())
                    return True
        return super().eventFilter(source, event)

    @staticmethod
    def convert_data(data, name):
        # Конвертация из байткода
        try:
            with open(fr"{name}.jpg", "wb+") as f:
                f.write(data)
            return fr"{os.getcwd()}\{name}.jpg"
        except Exception as ex:
            print("Ошибка при конвертировании:" + str(ex))

    def avatare(self):
        self.awindow.show()

    def closeEvent(self, _: typing.Optional[QtGui.QCloseEvent]):
        if self.account:
            CUR.execute('UPDATE accounts SET isActive = ? WHERE ID = ?', (0, self.account[0]))
            CON.commit()
            for i in range(self.maxid):
                os.remove(f'{i + 1}.jpg')
        self.closedflag = True
        self.tread.join()
        sys.exit()


class Avatar(Ui_Avatar):
    def __init__(self, account):
        super().__init__()
        self.account = account
        self.setupUi(self)
        self.change.clicked.connect(self.changee)
        self.firstrun()

    def firstrun(self):
        self.update_image(f'{self.account[0]}.jpg')

    def update_image(self, file_path):
        try:
            if file_path:
                pixmap = QtGui.QPixmap(file_path)
                self.changeavatar.setPixmap(pixmap.scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                                          QtCore.Qt.TransformationMode.SmoothTransformation))
                self.resize(pixmap.width(), pixmap.height() + self.change.height())
                with open(file_path, 'rb') as file:
                    binary = file.read()
            return self.uploadtodb(binary)
        except Exception as ex:
            print("Ошибка при выборе файла:" + str(ex))

    def changee(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Поставить аватар', r"", "Картинки (*.jpg)")
        self.update_image(file_path)

    def uploadtodb(self, binary):
        try:
            CUR.execute("UPDATE accounts SET `avatar` = ? WHERE ID = ?", (binary, self.account[0]))
            CON.commit()
        except Exception as ex:
            print("Ошибка при отправке фала в дб:" + str(ex))


# Хендлер исключений
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print(f"Exception: {exc_value}")
    traceback.print_tb(exc_traceback)


# Запуск
if __name__ == '__main__':
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    exe = Regform()
    exe.show()
    sys.exit(app.exec())
CON.close()
