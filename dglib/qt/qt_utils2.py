# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
import time
import threading
import win32process
import win32con
import functools
from PyQt4 import QtGui, QtCore
import sip

UM_SHOW = win32con.WM_USER + 100

__all__ = ['UM_SHOW', 'TrayMixIn', 'QssMixIn', 'EmitCallMixIn', 'EmitCallDecorator',
		   'ThreadingInvokeStubInMainThread', 'threadingInvokeStubInMainThread', 'callFromThread',
		   'callFromThread_wrap', 'RowHeightItemDelegateMixIn', 'HighlightFixItemDelegateMixIn',
		   'MixedItemDelegate', 'QssMsgBox', 'QssInputBox', 'AnimationImgMixIn', 'QClickableLabel',
		   'QDoubleClickableLabel', 'GET_X_LPARAM', 'GET_Y_LPARAM', 'check_resize_pos', 'msgbox',
		   'inputbox', 'resolve_xp_font_problem', 'center_window', 'move_center',
		   'move_rightbottom', 'center_to', 'change_widget_class', 'gbk', 'utf8', 'uni', 'uni8',
		   'loadqss']


class TrayMixIn(object):
	def __init__(self, app, title, style=1):
		self.app = app
		self.title = title
		self.style = style  # 0=使用最小化菜单项风格，1=使用灰字标题菜单项风格
		# 初始化托盘图标
		self.create_trayactions()
		self.create_trayicon()
		app.installEventFilter(self)

	def center_window(self, width, height):
		center_window(self, width, height)

	def create_trayactions(self):
		self.actTitle = QtGui.QAction(self.title, self)
		self.actTitle.setEnabled(False)
		self.actMinimize = QtGui.QAction('最小化', self)
		self.connect(self.actMinimize, QtCore.SIGNAL('triggered()'), QtCore.SLOT('hide()'))
		self.actRestore = QtGui.QAction('显示窗体', self)
		self.connect(self.actRestore, QtCore.SIGNAL('triggered()'), QtCore.SLOT('show()'))
		self.actQuit = QtGui.QAction('退出', self)
		self.connect(self.actQuit, QtCore.SIGNAL('triggered()'), self.on_actQuit_triggered)

	def create_trayicon(self):
		self.mnuTray = QtGui.QMenu()
		self.mnuTray.setStyleSheet('font: 9pt "宋体";')
		if self.style == 0:
			self.mnuTray.addAction(self.actMinimize)
			self.mnuTray.addAction(self.actRestore)
		else:
			self.mnuTray.addAction(self.actTitle)
		self.mnuTray.addSeparator()
		self.mnuTray.addAction(self.actQuit)

		self.trayIcon = QtGui.QSystemTrayIcon(self)
		self.trayIcon.setContextMenu(self.mnuTray)
		self.connect(self.trayIcon, QtCore.SIGNAL('activated(QSystemTrayIcon::ActivationReason)'),
					 self.trayIconActivated)

		self.icon = QtGui.QIcon(':/images/images/icon.png')
		self.trayIcon.setIcon(self.icon)
		self.trayIcon.setToolTip(self.windowTitle())
		self.trayIcon.show()
		self.setWindowIcon(self.icon)

	def enable_trayicon(self, enable=True):
		'''
		可禁用右键菜单防止用户重复点击
		@param enable: 是否启用
		'''
		self.trayIcon.setContextMenu(self.mnuTray if enable else None)

	def trayIconActivated(self, reason):
		'''
		当用户点击右下角托盘图标时调用
		@param reason: 鼠标事件（双击或是单击等）
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

	@QtCore.pyqtSignature('')
	def on_actQuit_triggered(self):
		'''
		菜单：退出
		'''
		if msgbox(self, '真的要退出吗？', title=self.title, question=True):
			self.quit()

	def closeEvent(self, event):
		'''
		点右上角关闭时最小化到托盘
		'''
		event.ignore()
		self.hide()

	def eventFilter(self, target, event):
		if event.type() == QtCore.QEvent.WindowStateChange and self.isMinimized():
			# 设置隐藏
			QtCore.QTimer.singleShot(0, self, QtCore.SLOT('hide()'))
			return True

		return self.eventFilter2(target, event)

	def eventFilter2(self, target, event):
		'''
		派生类可以重载此函数
		'''
		return self.app.eventFilter(target, event)

	def winEvent(self, msg):
		if msg.message == UM_SHOW:
			print 'UM_SHOW'
			self.show()
			self.raise_()
			self.activateWindow()
		return False, 0

	def quit(self, force=False):
		self.trayIcon.setToolTip('正在退出...')
		self.hide()
		self.trayIcon.hide()
		if force:
			win32process.ExitProcess(0)  # 强制退出，避免退出较慢的问题。
		self.app.exit()


class QssMixIn(object):
	'''
	这个类帮助在使用QSS美化界面的时候，自动处理标题栏最大化/最小化按钮事件和状态，支持和TrayMixIn一起使用。
	标题栏必须是一个命名为fraTitleBar的QFrame，其中有4个按钮btHelp、btMin、btMax、btClose。
	隐藏btMax可以禁止缩放/最大化窗口。
	'''

	def __init__(self, app, qss_file):
		self.app = app
		self.qss_file = qss_file
		self.qss_enabled = True
		self.qss_encoding = 'gbk'

		# 初始化标题栏按钮提示
		self.btHelp.setToolTip('帮助')
		self.btMin.setToolTip('最小化')
		self.btMax.setToolTip('最大化')
		self.btClose.setToolTip('关闭')
		# 去除标题栏按钮的焦点
		self.btHelp.setFocusPolicy(QtCore.Qt.NoFocus)
		self.btMin.setFocusPolicy(QtCore.Qt.NoFocus)
		self.btMax.setFocusPolicy(QtCore.Qt.NoFocus)
		self.btClose.setFocusPolicy(QtCore.Qt.NoFocus)

		# 挂接winEvent
		self.prv_winEvent = getattr(self, 'winEvent', None)
		self.winEvent = self.qss_winEvent

		# 挂接eventFilter
		self.prv_eventFilter = getattr(self, 'eventFilter', None)
		self.eventFilter = self.qss_eventFilter
		self.app.installEventFilter(self)

	def qss_avalible(self, qss_file=''):
		if not qss_file:
			qss_file = self.qss_file
		return os.path.isfile(qss_file)

	def qss_apply_style(self, qss_file=''):
		if not qss_file:
			qss_file = self.qss_file
		if self.qss_avalible(qss_file):
			# 设置窗体为无标题栏无边框样式
			if self.windowFlags() & QtCore.Qt.FramelessWindowHint != QtCore.Qt.FramelessWindowHint:
				self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
			QtGui.qApp.setStyleSheet(unicode(open(qss_file).read(), self.qss_encoding))

	@QtCore.pyqtSignature('')
	def on_btHelp_clicked(self):
		self.qss_apply_style()

	@QtCore.pyqtSignature('')
	def on_btMin_clicked(self):
		self.close()

	@QtCore.pyqtSignature('')
	def on_btMax_clicked(self):
		if self.btMax.objectName() == 'btMax':
			self.showMaximized()
		else:
			self.showNormal()

	@QtCore.pyqtSignature('')
	def on_btClose_clicked(self):
		self.close()

	def qss_allow_maximize(self):
		return self.btMax.isVisible()

	def qss_winEvent(self, msg):
		if self.qss_enabled:
			if msg.message == win32con.WM_NCHITTEST:
				x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
				y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
				# 判断是否RESIZE区域
				is_rszpos = check_resize_pos(self, x, y)
				if is_rszpos and self.qss_allow_maximize() and not self.isMaximized():
					return True, is_rszpos

				# 标题栏区域为扩展后的fraTop区域（包括窗口的2个像素边框）
				rect = self.fraTitleBar.geometry()
				rect.setTop(0)
				rect.setLeft(0)
				rect.setWidth(self.width())
				# 判断标题栏区域时排除标题栏的按钮
				if rect.contains(x, y) and \
						not isinstance(self.childAt(x, y), QtGui.QPushButton):
					# 如果窗口已经最大化，为避免被拖动，必须返回不在非客户区。
					# 同时为了实现双击标题栏还原，需要处理 WM_LBUTTONDBLCLK。
					if not self.isMaximized():
						return True, win32con.HTCAPTION

			elif msg.message == win32con.WM_NCLBUTTONDBLCLK:
				if self.qss_allow_maximize():
					# 最大化 <-> 还原
					if self.isMaximized():
						self.showNormal()
					else:
						x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
						y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
						# 判断是否RESIZE区域
						is_rszpos = check_resize_pos(self, x, y)
						if not is_rszpos:
							self.showMaximized()
					return True, 0

			# 实现窗口最大化后可双击标题栏还原
			elif msg.message == win32con.WM_LBUTTONDBLCLK:
				if self.qss_allow_maximize():
					x = GET_X_LPARAM(msg.lParam) - self.frameGeometry().x()
					y = GET_Y_LPARAM(msg.lParam) - self.frameGeometry().y()
					if self.isMaximized():
						# 标题栏区域为扩展后的fraTop区域（包括窗口的2个像素边框）
						rect = self.fraTitleBar.geometry()
						rect.setTop(0)
						rect.setLeft(0)
						rect.setWidth(self.width())
						# 判断标题栏区域时排除标题栏的按钮
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
					# 修正最大化后按钮状态仍然是hover的问题
					ev = QtGui.QMouseEvent(QtCore.QEvent.Leave,
										   QtCore.QPoint(0, 0),
										   QtCore.Qt.NoButton,
										   QtCore.Qt.MouseButtons(),
										   QtCore.Qt.KeyboardModifiers())
					self.app.sendEvent(self.btMax, ev)
					# 改变按钮样式（最大化->还原
					self.btMax.setObjectName('btRestore')
					self.btMax.style().unpolish(self.btMax)
					self.btMax.style().polish(self.btMax)
					self.btMax.setToolTip('还原')
					self.btMax.update()
				else:
					# 改变按钮样式（还原->最大化）
					self.btMax.setObjectName('btMax')
					self.btMax.style().unpolish(self.btMax)
					self.btMax.style().polish(self.btMax)
					self.btMax.setToolTip('最大化')
					self.btMax.update()
				return True

		if self.prv_eventFilter:
			return self.prv_eventFilter(target, event)
		return self.app.eventFilter(target, event)


class EmitCallMixIn(object):
	'''
	用于线程同步，在工作线程中需要以QT界面线程调用函数时使用。
	self.emit_call(self.slot_button_clicked, 'abc', 123)
	Qt的emit()方法并不支持字典参数，因此emit_call也不支持kwargs参数，
	对于这种情况建议使用后面的ThreadingInvokeStubInMainThread代替。
	'''

	def __init__(self):
		self.connect(self, QtCore.SIGNAL('emit_call'), self.emit_call_func)

	def emit_call(self, func, *args):
		'''
		emit()方法并不支持kwargs参数
		'''
		self.emit(QtCore.SIGNAL('emit_call'), func, *args)

	def emit_call_func(self, func, *args):
		func(*args)


class EmitCallDecorator(object):
	'''
	方便EmitCallMixIn.emit_call()使用的一个函数装饰器，
	但不支持写@EmitCallDecorator.create来用（因为返回的会是一个函数而不是对象的方法）。
	g.agent.status.state_changed.add_listener(EmitCallDecorator.create(self.slot_agent_statechanged))
	'''
	local = threading.local()
	local.instances = []

	def __init__(self, func, *args):
		self.func = func
		self.args = args

	def __call__(self, *args):
		self.func.im_self.emit_call(self.func, *args)

	@staticmethod
	def create(func):
		'''
		这个方法便于结合Event.add_listener使用，因为后者产生弱引用，
		故需要将生成的实例放入类的instances列表里，避免过早析构。
		'''
		instance = EmitCallDecorator(func)
		EmitCallDecorator.local.instances.append(instance)
		return instance.__call__


class ThreadingInvokeStubInMainThread(QtCore.QObject):
	'''
	参考自http://www.newsmth.net/bbscon.php?bid=1099&id=7877
	'''
	instances = set()

	def __init__(self):
		QtCore.QObject.__init__(self)

	@QtCore.pyqtSlot('PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject', 'PyQt_PyObject')
	def callMethod(self, resultObject, func, args, kwargs):
		resultObject['value'] = func(*args, **kwargs)

	@staticmethod
	def callMethodInMainThread(func, *args, **kwargs):
		resultObject = {}
		QtCore.QMetaObject.invokeMethod(threadingInvokeStubInMainThread, 'callMethod',
										QtCore.Qt.AutoConnection, QtCore.Q_ARG('PyQt_PyObject', resultObject),
										QtCore.Q_ARG('PyQt_PyObject', func), QtCore.Q_ARG('PyQt_PyObject', args),
										QtCore.Q_ARG('PyQt_PyObject', kwargs))
		return resultObject.get('value')

	@classmethod
	def wrap(cls, func):
		'''
		包装一个目标函数以便在非Qt界面线程中调用，被包装的函数会在PyQt主线程中执行。
		通常只由PyQt主线程调用，因此instances简单地作为类成员变量，无需使用线程本地存储。
		暂时未考虑func和类之间循环引用的问题。
		'''
		instance = functools.partial(callFromThread, func)
		ThreadingInvokeStubInMainThread.instances.add(instance)
		return instance


threadingInvokeStubInMainThread = ThreadingInvokeStubInMainThread()

# usage: In a work thread function, call it directly:
#  callFromThread(self.slot_play_progress, *args, **kwargs)
callFromThread = ThreadingInvokeStubInMainThread.callMethodInMainThread

# usage: In a place which need a callback function, call it to wrap a function:
# 	SIGNAL_PLAY_PROGRESS.connect(callFromThread_wrap(self.slot_play_progress))
callFromThread_wrap = ThreadingInvokeStubInMainThread.wrap


class RowHeightItemDelegateMixIn(object):
	'''
	用于调整QTreeView的行高不至于太小
	'''

	def sizeHint(self, option, index):
		size = QtGui.QItemDelegate.sizeHint(self, option, index)
		size.setHeight(size.height() + 6)
		return size


class HighlightFixItemDelegateMixIn(object):
	'''
	用于修正QTreeView选中行默认高亮会清除文字颜色的问题
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
		self.setButtonText(QtGui.QMessageBox.Ok, '确定')
		return self.exec_()

	def warn(self, text):
		self.setText(text)
		self.setIcon(QtGui.QMessageBox.Warning)
		self.setStandardButtons(QtGui.QMessageBox.Ok)
		self.setButtonText(QtGui.QMessageBox.Ok, '确定')
		return self.exec_()

	def question(self, text):
		self.setText(text)
		self.setIcon(QtGui.QMessageBox.Question)
		self.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
		self.setButtonText(QtGui.QMessageBox.Yes, '是')
		self.setButtonText(QtGui.QMessageBox.No, '否')
		return self.exec_() == QtGui.QMessageBox.Yes

	def __call__(self, parent, msg, *args, **kwargs):
		'''
		提供与msgbox()函数一致的接口
		'''
		title = kwargs.get('title')
		if title is None:
			title = getattr(self, 'title', None)
		if title is None:
			title = getattr(parent, 'title', None)
		if title is None:
			func = getattr(parent, 'windowTitle', None)
			if func:
				title = func()
		if title is None:
			title = '提示'
		warning = kwargs.get('warning', False)
		question = kwargs.get('question', False)

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
			# 判断标题栏区域时排除按钮
			if not isinstance(self.childAt(x, y), QtGui.QPushButton):
				return True, win32con.HTCAPTION
		return False, 0


class QssInputBox(QtGui.QInputDialog):
	def __init__(self, qss):
		QtGui.QInputDialog.__init__(self)
		self.setStyleSheet(qss)
		self.setFixedSize(200, 117)  # height不受控制
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setOkButtonText('确定')
		self.setCancelButtonText('取消')

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
			# 判断标题栏区域时排除按钮
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
		QtGui.qApp.connect(self._aim_timer, QtCore.SIGNAL('timeout()'), self.on_aim_timeout)
		self._aim_timer.start(interval)

	def on_aim_timeout(self):
		self.setPixmap(self._aim_pixs[self._aim_idx])
		self._aim_idx = (self._aim_idx + 1) % len(self._aim_pixs)


class QClickableLabel(QtGui.QLabel):
	# 按下和释放鼠标按键期间，如果鼠标移动距离超过这个阀值则判定为拖拽而非点击。
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
			self.emit(QtCore.SIGNAL('clicked'))
		self.down_pos = None

	def click(self):
		self.emit(QtCore.SIGNAL('clicked'))

	def paintEvent(self, ev):
		'''
		居中显示QPixmap
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
#					print 'doubleClicked - %s' % self.objectName()
					self.last_releasetime = 0
					self.emit(QtCore.SIGNAL('doubleClicked'))
			else:
				self.id_run = self.startTimer(self.dblclick_time)
				self.last_releasetime = tick

#	def mouseDoubleClickEvent(self, ev):
#		print 'mouseDoubleClickEvent', ev.button()

	def timerEvent(self, ev):
		if ev.timerId() == self.id_run:
			#			print 'clicked - %s' % self.objectName()
			self.last_releasetime = 0
			self.killTimer(self.id_run)
			self.id_run = None
			self.emit(QtCore.SIGNAL('clicked'))


def GET_X_LPARAM(lParam):
	# 在有多个显示器的时候允许负值
	return int(lParam & 0xFFFF)


def GET_Y_LPARAM(lParam):
	# 在有多个显示器的时候允许负值
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
	# title = '', warning = False, question = False
	title = kwargs.get('title')
	if title is None:
		title = getattr(msgbox, 'title', None)
	if title is None:
		title = getattr(parent, 'title', None)
	if title is None:
		func = getattr(parent, 'windowTitle', None)
		if func:
			title = func()
	if title is None:
		title = '提示'
	warning = kwargs.get('warning', False)
	question = kwargs.get('question', False)

	if warning:
		QtGui.QMessageBox.warning(parent, title, msg, '确定')
	elif question:
		reply = QtGui.QMessageBox.question(parent, title, msg, '是', '否')
		if reply == 0:
			return True
	else:
		QtGui.QMessageBox.information(parent, title, msg, '确定')


def inputbox(parent, label, default='', **kwargs):
	# title = '', oktext = '确定', canceltext = '取消', inputmode = TextInput,
	# returndlg = False
	title = kwargs.get('title')
	if title is None:
		title = getattr(parent, 'title', None)
	if title is None:
		func = getattr(parent, 'windowTitle', None)
		if func:
			title = func()
	if title is None:
		title = '提示'

	oktext = kwargs.get('oktext', '确定')
	canceltext = kwargs.get('canceltext', '取消')
	inputmode = kwargs.get('inputmode', QtGui.QInputDialog.TextInput)
	returndlg = kwargs.get('returndlg', False)
	size = kwargs.get('size')

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
	if size is not None:
		dlg.resize(*size)
	if not returndlg:
		if dlg.exec_():
			s = dlg.textValue()
			return s
	else:
		return dlg


def resolve_xp_font_problem(dlg, tableview=None):
	# 解决XP下表格列头、弹出消息框字体难看问题
	dlg.setStyleSheet('font: 9pt "宋体";')
	# 列头字体用上面方法无法修改
	if tableview:
		tableview.horizontalHeader().setStyleSheet('QHeaderView::section { font: 9pt "宋体"; }')


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
	if windowRect.x() < 0:
		windowRect.setX(0)
	if windowRect.y() < 0:
		windowRect.setY(0)
	win.setGeometry(windowRect)


def move_rightbottom(win, adjust_x=0, adjust_y=0):
	desktop = QtGui.qApp.desktop()
	desktopRect = desktop.availableGeometry(desktop.primaryScreen())  # 排除了任务栏区域
	windowRect = QtCore.QRect(0, 0, win.width(), win.height())
	windowRect.moveBottomRight(desktopRect.bottomRight())
	windowRect.adjust(adjust_x, adjust_y, adjust_x, adjust_y)
	win.setGeometry(windowRect)


def center_to(widget, refer_widget):
	'''
	对于同一个父容器的两个组件，移动一个组件到另一个组件的中心点。
	@param widget: 进行移动的目标组件
	@param refer_widget: 作为中心点参考的组件
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


def gbk(u, encoding='utf-8'):
	'''
	string convert (utf-8 -> gbk)
	'''
	if sip.getapi('QString') != 2:  # api=2时QString会自动变为str类型
		if isinstance(u, QtCore.QString):
			u = unicode(u)

	if isinstance(u, unicode):
		return u.encode('gbk')
	elif encoding == 'gbk':
		return u
	else:
		return unicode(u, encoding).encode('gbk')


def utf8(u, encoding='gbk'):
	'''
	string convert (gbk -> utf-8)
	'''
	if sip.getapi('QString') != 2:  # api=2时QString会自动变为str类型
		if isinstance(u, QtCore.QString):
			u = unicode(u)

	if isinstance(u, unicode):
		return u.encode('utf-8')
	elif encoding == 'utf-8':
		return u
	else:
		return unicode(u, encoding).encode('utf-8')


def uni(s, encoding='gbk'):
	if sip.getapi('QString') != 2:  # api=2时QString会自动变为str类型
		if isinstance(s, QtCore.QString):
			s = unicode(s)

	if isinstance(s, unicode):
		return s
	elif isinstance(s, str):
		return unicode(s, encoding)
	else:
		return unicode(s)


def uni8(s):
	return uni(s, encoding='utf-8')


def loadqss(name, encoding='gbk'):
	qssfile = '%s.qss' % name
	if os.path.isfile(qssfile):
		qssdata = unicode(open(qssfile).read(), encoding)
	else:
		f = QtCore.QFile(':/qss/%s.qss' % name)
		f.open(QtCore.QFile.ReadOnly)  # 打开失败返回False，继续readAll()返回空QByteArray
		qssdata = unicode(f.readAll(), encoding)
	return qssdata


def __update__all__():
	with open(__file__) as f:
		exports = []
		for line in f:
			m = re.match(b'(?:def|class)\s+([^(]+)\(', line)
			if not m:
				# 匹配 std_date = isoformat_date 这样的全局重命名
				m = re.match(b'([^\s]+) = .+', line)
			if m:
				item = m.group(1)
				if not item.startswith('_'):
					exports.append(item)
		print exports
	to = b'__all__ = %s' % exports
	print to
	before = open(__file__).read()
	r = re.compile(b'^__all__\s*=\s*\[[^]]*]', re.M)
	after = r.sub(to, before, 1)
	if after != before:
		open(__file__, 'w').write(after)


if __name__ == '__main__':
	__update__all__()
