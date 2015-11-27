# -*- coding: gbk -*-
from __future__ import unicode_literals
import os
import time
import threading
import win32process
import win32con
from PyQt4 import QtGui, QtCore
import sip

UM_SHOW = win32con.WM_USER + 100


class TrayMixIn(object):
	def __init__(self, app, title, style=1):
		self.app = app
		self.title = title
		self.style = style	# 0=ʹ����С���˵�����1=ʹ�û��ֱ���˵�����
		# ��ʼ������ͼ��
		self.create_trayactions()
		self.create_trayicon()
		app.installEventFilter(self)

	def center_window(self, width, height):
		center_window(self, width, height)

	def create_trayactions(self):
		self.actTitle = QtGui.QAction(self.title, self)
		self.actTitle.setEnabled(False)
		self.actMinimize = QtGui.QAction("��С��", self)
		self.connect(self.actMinimize, QtCore.SIGNAL("triggered()"), QtCore.SLOT("hide()"))
		self.actRestore = QtGui.QAction("��ʾ����", self)
		self.connect(self.actRestore, QtCore.SIGNAL("triggered()"), QtCore.SLOT("show()"))
		self.actQuit = QtGui.QAction("�˳�", self)
		self.connect(self.actQuit, QtCore.SIGNAL("triggered()"), self.on_actQuit_triggered)

	def create_trayicon(self):
		self.mnuTray = QtGui.QMenu()
		self.mnuTray.setStyleSheet('font: 9pt "����";')
		if self.style == 0:
			self.mnuTray.addAction(self.actMinimize)
			self.mnuTray.addAction(self.actRestore)
		else:
			self.mnuTray.addAction(self.actTitle)
		self.mnuTray.addSeparator()
		self.mnuTray.addAction(self.actQuit)

		self.trayIcon = QtGui.QSystemTrayIcon(self)
		self.trayIcon.setContextMenu(self.mnuTray)
		self.connect(self.trayIcon, QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"),
			self.trayIconActivated)

		self.icon = QtGui.QIcon(":/images/images/icon.png")
		self.trayIcon.setIcon(self.icon)
		self.trayIcon.setToolTip(self.windowTitle())
		self.trayIcon.show()
		self.setWindowIcon(self.icon)

	def enable_trayicon(self, enable=True):
		'''
		�ɽ����Ҽ��˵���ֹ�û��ظ����
		@param enable: �Ƿ�����
		'''
		self.trayIcon.setContextMenu(self.mnuTray if enable else None)

	def trayIconActivated(self, reason):
		'''
		���û�������½�����ͼ��ʱ����
		@param reason: ����¼���˫�����ǵ����ȣ�
		'''
		if reason == QtGui.QSystemTrayIcon.DoubleClick:
			state = int(self.windowState())
			if state & QtCore.Qt.WindowMaximized:
				self.showMaximized()
			elif state & QtCore.Qt.WindowFullScreen:
				self.showFullScreen()
			else:
				self.showNormal()
			self.raise_()
			self.activateWindow()

	@QtCore.pyqtSignature("")
	def on_actQuit_triggered(self):
		'''
		�˵����˳�
		'''
		if msgbox(self, "���Ҫ�˳���", title=self.title, question=True):
			self.quit()

	def closeEvent(self, event):
		'''
		�����Ͻǹر�ʱ��С��������
		'''
		event.ignore()
		self.hide()

	def eventFilter(self, target, event):
		if event.type() == QtCore.QEvent.WindowStateChange and self.isMinimized():
			# ��������
			QtCore.QTimer.singleShot(0, self, QtCore.SLOT("hide()"))
			return True

		return self.eventFilter2(target, event)

	def eventFilter2(self, target, event):
		'''
		������������ش˺���
		'''
		return self.app.eventFilter(target, event)

	def winEvent(self, msg):
		if msg.message == UM_SHOW:
			print "UM_SHOW"
			self.show()
			self.raise_()
			self.activateWindow()
		return False, 0

	def quit(self, force=False):
		self.trayIcon.setToolTip("�����˳�...")
		self.hide()
		self.trayIcon.hide()
		if force:
			win32process.ExitProcess(0)		# ǿ���˳��������˳����������⡣
		self.app.exit()


class QssMixIn(object):
	'''
	����������ʹ��QSS���������ʱ���Զ�������������/��С����ť�¼���״̬��֧�ֺ�TrayMixInһ��ʹ�á�
	������������һ������ΪfraTitleBar��QFrame��������4����ťbtHelp��btMin��btMax��btClose��
	����btMax���Խ�ֹ����/��󻯴��ڡ�
	'''
	def __init__(self, app, qss_file):
		self.app = app
		self.qss_file = qss_file
		self.qss_enabled = True
		self.qss_encoding = "gbk"

		# ��ʼ����������ť��ʾ
		self.btHelp.setToolTip("����")
		self.btMin.setToolTip("��С��")
		self.btMax.setToolTip("���")
		self.btClose.setToolTip("�ر�")
		# ȥ����������ť�Ľ���
		self.btHelp.setFocusPolicy(QtCore.Qt.NoFocus)
		self.btMin.setFocusPolicy(QtCore.Qt.NoFocus)
		self.btMax.setFocusPolicy(QtCore.Qt.NoFocus)
		self.btClose.setFocusPolicy(QtCore.Qt.NoFocus)

		# �ҽ�winEvent
		self.prv_winEvent = getattr(self, "winEvent", None)
		self.winEvent = self.qss_winEvent

		# �ҽ�eventFilter
		self.prv_eventFilter = getattr(self, "eventFilter", None)
		self.eventFilter = self.qss_eventFilter
		self.app.installEventFilter(self)

	def qss_avalible(self, qss_file=""):
		if not qss_file:
			qss_file = self.qss_file
		return os.path.isfile(qss_file)

	def qss_apply_style(self, qss_file=""):
		if not qss_file:
			qss_file = self.qss_file
		if self.qss_avalible(qss_file):
			# ���ô���Ϊ�ޱ������ޱ߿���ʽ
			if self.windowFlags() & QtCore.Qt.FramelessWindowHint != QtCore.Qt.FramelessWindowHint:
				self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
			QtGui.qApp.setStyleSheet(unicode(open(qss_file).read(), self.qss_encoding))

	@QtCore.pyqtSignature("")
	def on_btHelp_clicked(self):
		self.qss_apply_style()

	@QtCore.pyqtSignature("")
	def on_btMin_clicked(self):
		self.close()

	@QtCore.pyqtSignature("")
	def on_btMax_clicked(self):
		if self.btMax.objectName() == "btMax":
			self.showMaximized()
		else:
			self.showNormal()

	@QtCore.pyqtSignature("")
	def on_btClose_clicked(self):
		self.close()

	def qss_allow_maximize(self):
		return self.btMax.isVisible()

	def qss_winEvent(self, msg):
		if self.qss_enabled:
			if msg.message == win32con.WM_NCHITTEST:
				x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
				y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
				# �ж��Ƿ�RESIZE����
				is_rszpos = check_resize_pos(self, x, y)
				if is_rszpos and self.qss_allow_maximize() and not self.isMaximized():
					return True, is_rszpos

				# ����������Ϊ��չ���fraTop���򣨰������ڵ�2�����ر߿�
				rect = self.fraTitleBar.geometry()
				rect.setTop(0)
				rect.setLeft(0)
				rect.setWidth(self.width())
				# �жϱ���������ʱ�ų��������İ�ť
				if rect.contains(x, y) and \
					not isinstance(self.childAt(x, y), QtGui.QPushButton):
					# ��������Ѿ���󻯣�Ϊ���ⱻ�϶������뷵�ز��ڷǿͻ�����
					# ͬʱΪ��ʵ��˫����������ԭ����Ҫ���� WM_LBUTTONDBLCLK��
					if not self.isMaximized():
						return True, win32con.HTCAPTION

			elif msg.message == win32con.WM_NCLBUTTONDBLCLK:
				if self.qss_allow_maximize():
					# ��� <-> ��ԭ
					if self.isMaximized():
						self.showNormal()
					else:
						x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
						y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
						# �ж��Ƿ�RESIZE����
						is_rszpos = check_resize_pos(self, x, y)
						if not is_rszpos:
							self.showMaximized()
					return True, 0

			# ʵ�ִ�����󻯺��˫����������ԭ
			elif msg.message == win32con.WM_LBUTTONDBLCLK:
				if self.qss_allow_maximize():
					x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
					y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
					if self.isMaximized():
						# ����������Ϊ��չ���fraTop���򣨰������ڵ�2�����ر߿�
						rect = self.fraTitleBar.geometry()
						rect.setTop(0)
						rect.setLeft(0)
						rect.setWidth(self.width())
						# �жϱ���������ʱ�ų��������İ�ť
						if rect.contains(x, y) and \
							not isinstance(self.childAt(x, y), QtGui.QPushButton):
							self.showNormal()
							return True, 0

		if self.prv_winEvent:
			return self.prv_winEvent(msg)
		return False, 0

	def qss_eventFilter(self, target, event):
		if self.qss_enabled:
			if event.type() == QtCore.QEvent.WindowStateChange:
				if self.isMaximized():
					# ������󻯺�ť״̬��Ȼ��hover������
					ev = QtGui.QMouseEvent(QtCore.QEvent.Leave,
										   QtCore.QPoint(0, 0),
										   QtCore.Qt.NoButton,
										   QtCore.Qt.MouseButtons(),
										   QtCore.Qt.KeyboardModifiers())
					self.app.sendEvent(self.btMax, ev)
					# �ı䰴ť��ʽ�����->��ԭ
					self.btMax.setObjectName("btRestore")
					self.btMax.style().unpolish(self.btMax)
					self.btMax.style().polish(self.btMax)
					self.btMax.setToolTip("��ԭ")
					self.btMax.update()
				else:
					# �ı䰴ť��ʽ����ԭ->��󻯣�
					self.btMax.setObjectName("btMax")
					self.btMax.style().unpolish(self.btMax)
					self.btMax.style().polish(self.btMax)
					self.btMax.setToolTip("���")
					self.btMax.update()
				return True

		if self.prv_eventFilter:
			return self.prv_eventFilter(target, event)
		return self.app.eventFilter(target, event)


class EmitCallMixIn(object):
	'''
	�����߳�ͬ�����ڹ����߳�����Ҫ��QT�����̵߳��ú���ʱʹ�á�
	self.emit_call(self.slot_button_clicked, "abc", 123)
	'''
	def __init__(self):
		self.connect(self, QtCore.SIGNAL("emit_call"), self.emit_call_func)

	def emit_call(self, func, *args, **kwargs):
		self.emit(QtCore.SIGNAL("emit_call"), func, *args, **kwargs)

	def emit_call_func(self, func, *args, **kwargs):
		func(*args, **kwargs)


class EmitCallDecorator(object):
	'''
	����EmitCallMixIn.emit_call()ʹ�õ�һ������װ������
	����֧��д@EmitCallDecorator.create���ã���Ϊ���صĻ���һ�����������Ƕ���ķ�������
	g.agent.status.state_changed.add_listener(EmitCallDecorator.create(self.slot_agent_statechanged))
	'''
	local = threading.local()
	local.instances = []

	def __init__(self, func, *args, **kw):
		self.func = func
		self.args = args
		self.kw = kw

	def __call__(self, *args, **kw):
		self.func.im_self.emit_call(self.func, *args, **kw)

	@staticmethod
	def create(func):
		'''
		����������ڽ��Event.add_listenerʹ�ã���Ϊ���߲��������ã�
		����Ҫ�����ɵ�ʵ���������instances�б���������������
		'''
		instance = EmitCallDecorator(func)
		EmitCallDecorator.local.instances.append(instance)
		return instance.__call__


class RowHeightItemDelegateMixIn(object):
	'''
	���ڵ���QTreeView���и߲�����̫С
	'''
	def sizeHint(self, option, index):
		size = QtGui.QItemDelegate.sizeHint(self, option, index)
		size.setHeight(size.height() + 6)
		return size


class HighlightFixItemDelegateMixIn(object):
	'''
	��������QTreeViewѡ����Ĭ�ϸ��������������ɫ������
	'''
	def paint(self, painter, option, index):
		variant = index.data(QtCore.Qt.ForegroundRole)
		if variant.isValid():
			brush = QtGui.QBrush(variant)
			textcolor = brush.color()
			if textcolor != option.palette.color(QtGui.QPalette.WindowText):
				option.palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)
				option.palette.setColor(QtGui.QPalette.Highlight, textcolor)
		QtGui.QItemDelegate.paint(self, painter, option, index)


class MixedItemDelegate(QtGui.QItemDelegate,
						RowHeightItemDelegateMixIn,
						HighlightFixItemDelegateMixIn):
	pass


class QssMsgBox(QtGui.QMessageBox):
	def __init__(self, qss):
		QtGui.QMessageBox.__init__(self)
		self.setStyleSheet(qss)
		self.setFixedSize(1400, 300)
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

	def info(self, text):
		self.setText(text)
		self.setIcon(QtGui.QMessageBox.Information)
		self.setStandardButtons(QtGui.QMessageBox.Ok)
		self.setButtonText(QtGui.QMessageBox.Ok, "ȷ��")
		return self.exec_()

	def warn(self, text):
		self.setText(text)
		self.setIcon(QtGui.QMessageBox.Warning)
		self.setStandardButtons(QtGui.QMessageBox.Ok)
		self.setButtonText(QtGui.QMessageBox.Ok, "ȷ��")
		return self.exec_()

	def question(self, text):
		self.setText(text)
		self.setIcon(QtGui.QMessageBox.Question)
		self.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
		self.setButtonText(QtGui.QMessageBox.Yes, "��")
		self.setButtonText(QtGui.QMessageBox.No, "��")
		return self.exec_() == QtGui.QMessageBox.Yes

	def __call__(self, parent, msg, *args, **kwargs):
		'''
		�ṩ��msgbox()����һ�µĽӿ�
		'''
		title = kwargs.get("title")
		if title is None:
			title = getattr(self, "title", None)
		if title is None:
			title = getattr(parent, "title", None)
		if title is None:
			func = getattr(parent, "windowTitle", None)
			if func:
				title = func()
		if title is None:
			title = "��ʾ"
		warning = kwargs.get("warning", False)
		question = kwargs.get("question", False)

		if warning:
			self.warn(msg)
		elif question:
			return self.question(msg)
		else:
			self.info(msg)

	def winEvent(self, msg):
		if msg.message == win32con.WM_NCHITTEST:
			x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
			y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
			# �жϱ���������ʱ�ų���ť
			if not isinstance(self.childAt(x, y), QtGui.QPushButton):
				return True, win32con.HTCAPTION
		return False, 0


class QssInputBox(QtGui.QInputDialog):
	def __init__(self, qss):
		QtGui.QInputDialog.__init__(self)
		self.setStyleSheet(qss)
		self.setFixedSize(200, 117)	# height���ܿ���
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setOkButtonText("ȷ��")
		self.setCancelButtonText("ȡ��")

	def getInteger(self, parent, title, text, default, min_, max_, step):
		val = None
		self.setWindowFlags(parent.windowFlags())
		self.setWindowTitle(title)
		self.setLabelText(text)
		self.setIntRange(min_, max_)
		self.setIntValue(default)
		self.setIntStep(step)
		self.setpos(parent)
		ok = self.exec_()
		if ok:
			val = self.intValue()
		return val, ok

	def setpos(self, parent):
		rect = self.geometry()
		rect.moveCenter(parent.geometry().center())
		self.setGeometry(rect)

	def winEvent(self, msg):
		if msg.message == win32con.WM_NCHITTEST:
			x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
			y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
			# �жϱ���������ʱ�ų���ť
			ctrl = self.childAt(x, y)
			if not ctrl or isinstance(ctrl, (QtGui.QLabel,)):
				return True, win32con.HTCAPTION
		return False, 0


class AnimationImgMixIn(object):
	def __init__(self, pixs, interval):
		self._aim_pixs = pixs
		self._aim_interval = interval
		self._aim_timer = QtCore.QTimer(self)
		self._aim_idx = 0
		QtGui.qApp.connect(self._aim_timer, QtCore.SIGNAL("timeout()"), self.on_aim_timeout)
		self._aim_timer.start(interval)

	def on_aim_timeout(self):
		self.setPixmap(self._aim_pixs[self._aim_idx])
		self._aim_idx = (self._aim_idx + 1) % len(self._aim_pixs)


class QClickableLabel(QtGui.QLabel):
	# ���º��ͷ���갴���ڼ䣬�������ƶ����볬�������ֵ���ж�Ϊ��ק���ǵ����
	TOLERANCE = 0

	def __init__(self, parent=None):
		super(QClickableLabel, self).__init__(parent)
		self.down_pos = None

	def mousePressEvent(self, ev):
		self.down_pos = ev.globalPos()

	def mouseReleaseEvent(self, ev):
		if ev.button() != QtCore.Qt.LeftButton:
			return
		pt = ev.globalPos() - self.down_pos
		if pt.manhattanLength() <= self.TOLERANCE:
			self.emit(QtCore.SIGNAL("clicked"))
		self.down_pos = None

	def click(self):
		self.emit(QtCore.SIGNAL("clicked"))

	def paintEvent(self, ev):
		'''
		������ʾQPixmap
		'''
		if self.pixmap() is None:
			QtGui.QLabel.paintEvent(self, ev)
			return

		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)

		pix_size = QtCore.QSize(self.pixmap().size())
#		pix_size.scale(ev.rect().size(), QtCore.Qt.KeepAspectRatio)

#		scaledPix = QtGui.QPixmap(self.pixmap().scaled(pix_size, QtCore.Qt.KeepAspectRatio,
#			QtCore.Qt.SmoothTransformation))

#		painter.drawPixmap(QtCore.QPoint(), scaledPix)
		pt = QtCore.QPoint()
		pt.setX((self.width() - pix_size.width()) / 2)
		pt.setY((self.height() - pix_size.height()) / 2)
		painter.drawPixmap(pt, self.pixmap())
#		painter.drawRect(self.rect())


class QDoubleClickableLabel(QClickableLabel):
	def __init__(self, parent=None):
		super(QDoubleClickableLabel, self).__init__(parent)

		self.last_releasetime = 0
		self.id_run = None
		self.dblclick_time = 300

	def mousePressEvent(self, ev):
		pass

	def mouseReleaseEvent(self, ev):
		if ev.button() != QtCore.Qt.LeftButton:
			return

		if self.rect().contains(ev.pos()):
			tick = time.clock()
			if self.last_releasetime:
				if tick - self.last_releasetime < self.dblclick_time:
					if self.id_run:
						self.killTimer(self.id_run)
#					print "doubleClicked - %s" % self.objectName()
					self.last_releasetime = 0
					self.emit(QtCore.SIGNAL("doubleClicked"))
			else:
				self.id_run = self.startTimer(self.dblclick_time)
				self.last_releasetime = tick

#	def mouseDoubleClickEvent(self, ev):
#		print "mouseDoubleClickEvent", ev.button()

	def timerEvent(self, ev):
		if ev.timerId() == self.id_run:
#			print "clicked - %s" % self.objectName()
			self.last_releasetime = 0
			self.killTimer(self.id_run)
			self.id_run = None
			self.emit(QtCore.SIGNAL("clicked"))


def GET_X_LPARAM(lParam):
	# ���ж����ʾ����ʱ������ֵ
	return int(lParam & 0xFFFF)


def GET_Y_LPARAM(lParam):
	# ���ж����ʾ����ʱ������ֵ
	return int(lParam >> 16 & 0xFFFF)


def check_resize_pos(widget, x, y, bordersize=4):
	result = 0
	xl = x in range(bordersize + 1)
	xr = x in range(widget.width() - bordersize, widget.width() + 1)
	yt = y in range(bordersize + 1)
	yb = y in range(widget.height() - bordersize, widget.height() + 1)
	if xl and yt:
		result = win32con.HTTOPLEFT
	elif xr and yt:
		result = win32con.HTTOPRIGHT
	elif xl and yb:
		result = win32con.HTBOTTOMLEFT
	elif xr and yb:
		result = win32con.HTBOTTOMRIGHT
	elif xl:
		result = win32con.HTLEFT
	elif xr:
		result = win32con.HTRIGHT
	elif yt:
		result = win32con.HTTOP
	elif yb:
		result = win32con.HTBOTTOM
	return result


def msgbox(parent, msg, **kwargs):
	# title = "", warning = False, question = False
	title = kwargs.get("title")
	if title is None:
		title = getattr(msgbox, "title", None)
	if title is None:
		title = getattr(parent, "title", None)
	if title is None:
		func = getattr(parent, "windowTitle", None)
		if func:
			title = func()
	if title is None:
		title = "��ʾ"
	warning = kwargs.get("warning", False)
	question = kwargs.get("question", False)

	if warning:
		QtGui.QMessageBox.warning(parent, title, msg, "ȷ��")
	elif question:
		reply = QtGui.QMessageBox.question(parent, title, msg, "��", "��")
		if reply == 0:
			return True
	else:
		QtGui.QMessageBox.information(parent, title, msg, "ȷ��")


def inputbox(parent, label, default="", **kwargs):
	# title = "", oktext = "ȷ��", canceltext = "ȡ��", inputmode = TextInput,
	# returndlg = False
	title = kwargs.get("title")
	if title is None:
		title = getattr(parent, "title", None)
	if title is None:
		func = getattr(parent, "windowTitle", None)
		if func:
			title = func()
	if title is None:
		title = "��ʾ"

	oktext = kwargs.get("oktext", "ȷ��")
	canceltext = kwargs.get("canceltext", "ȡ��")
	inputmode = kwargs.get("inputmode", QtGui.QInputDialog.TextInput)
	returndlg = kwargs.get("returndlg", False)

	dlg = QtGui.QInputDialog(parent)
	dlg.setWindowTitle(title)
	dlg.setLabelText(label)
	dlg.setInputMode(inputmode)
	if inputmode == QtGui.QInputDialog.TextInput:
		dlg.setTextValue(default)
	elif inputmode == QtGui.QInputDialog.IntInput:
		dlg.setIntValue(default)
	elif inputmode == QtGui.QInputDialog.DoubleInput:
		dlg.setDoubleValue(default)
	dlg.setOkButtonText(oktext)
	dlg.setCancelButtonText(canceltext)
	if not returndlg:
		if dlg.exec_():
			s = str(dlg.textValue().toAscii())
			return s
	else:
		return dlg


def resolve_xp_font_problem(dlg, tableview=None):
	# ���XP�±����ͷ��������Ϣ�������ѿ�����
	dlg.setStyleSheet('font: 9pt "����";')
	# ��ͷ���������淽���޷��޸�
	if tableview:
		tableview.horizontalHeader().setStyleSheet('QHeaderView::section { font: 9pt "����"; }')


def center_window(win, width, height):
	desktop = QtGui.qApp.desktop()
	screenRect = desktop.screenGeometry(desktop.primaryScreen())
	windowRect = QtCore.QRect(0, 0, width, height)
	windowRect.moveCenter(screenRect.center())
	win.setGeometry(windowRect)


def move_center(win, adjust_x=0, adjust_y=0):
	desktop = QtGui.qApp.desktop()
	screenRect = desktop.screenGeometry(desktop.primaryScreen())
	windowRect = QtCore.QRect(0, 0, win.width(), win.height())
	windowRect.moveCenter(screenRect.center())
	windowRect.adjust(adjust_x, adjust_y, adjust_x, adjust_y)
	win.setGeometry(windowRect)


def move_rightbottom(win, adjust_x=0, adjust_y=0):
	desktop = QtGui.qApp.desktop()
	desktopRect = desktop.availableGeometry(desktop.primaryScreen())	# �ų�������������
	windowRect = QtCore.QRect(0, 0, win.width(), win.height())
	windowRect.moveBottomRight(desktopRect.bottomRight())
	windowRect.adjust(adjust_x, adjust_y, adjust_x, adjust_y)
	win.setGeometry(windowRect)


def center_to(widget, refer_widget):
	'''
	����ͬһ��������������������ƶ�һ���������һ����������ĵ㡣
	@param widget: �����ƶ���Ŀ�����
	@param refer_widget: ��Ϊ���ĵ�ο������
	'''
	geo = widget.geometry()
	geo.moveCenter(refer_widget.geometry().center())
	widget.setGeometry(geo)


def change_widget_class(widget, class_, visible=True):
	new_widget = class_(widget.parent())
	new_widget.setParent(widget.parent())
	new_widget.setGeometry(widget.geometry())
	new_widget.setStyleSheet(widget.styleSheet())
	new_widget.setVisible(visible)
	new_widget.setObjectName(widget.objectName())
	widget.deleteLater()
	return new_widget


def gbk(u, encoding="utf-8"):
	'''
	string convert (utf-8 -> gbk)
	'''
	if sip.getapi("QString") != 2:	# api=2ʱQString���Զ���Ϊstr����
		if isinstance(u, QtCore.QString):
			u = unicode(u)

	if isinstance(u, unicode):
		return u.encode("gbk")
	elif encoding == "gbk":
		return u
	else:
		return unicode(u, encoding).encode("gbk")


def utf8(u, encoding="gbk"):
	'''
	string convert (gbk -> utf-8)
	'''
	if sip.getapi("QString") != 2:	# api=2ʱQString���Զ���Ϊstr����
		if isinstance(u, QtCore.QString):
			u = unicode(u)

	if isinstance(u, unicode):
		return u.encode("utf-8")
	elif encoding == "utf-8":
		return u
	else:
		return unicode(u, encoding).encode("utf-8")


def uni(s, encoding="gbk"):
	if sip.getapi("QString") != 2:	# api=2ʱQString���Զ���Ϊstr����
		if isinstance(s, QtCore.QString):
			s = unicode(s)

	if isinstance(s, unicode):
		return s
	elif isinstance(s, str):
		return unicode(s, encoding)
	else:
		return unicode(s)


def uni8(s):
	return uni(s, encoding="utf-8")


def loadqss(name, encoding="gbk"):
	qssfile = "%s.qss" % name
	if os.path.isfile(qssfile):
		qssdata = unicode(open(qssfile).read(), encoding)
	else:
		f = QtCore.QFile(":/qss/%s.qss" % name)
		f.open(QtCore.QFile.ReadOnly)	# ��ʧ�ܷ���False������readAll()���ؿ�QByteArray
		qssdata = unicode(f.readAll(), encoding)
	return qssdata
