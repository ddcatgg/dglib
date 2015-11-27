# -*- coding: GB2312 -*-
from PyQt4 import QtCore, QtGui, QtSql

def qv(s):
#	if isinstance(s, (str, unicode)):	# else is PyQt4.QtCore.QString
#		codec = QtCore.QTextCodec.codecForName("gb2312")
#		s = codec.toUnicode(s)
	return QtCore.QVariant(s)

def tr(*var):
	return QtGui.QApplication.translate(*var)

def GBK(s):
	return s if isinstance(s, str) else unicode(s).encode("GBK")

def set_header(model, list):
	for i in xrange(len(list)):
		model.setHeaderData(i, QtCore.Qt.Horizontal, qv(list[i]))

class MyMessageBox(QtGui.QMessageBox):
	def __init__(self, parent, title, msg):
		self.__class = MyMessageBox
		super(self.__class, self).__init__(parent)

		self.setFont(QtGui.QFont("Tahoma", 9))
		self.setWindowTitle(title)
		self.setText(msg)

def make_message_box(icon):
	def _render(func):
		def _f(parent, title, msg):
			msgbox = MyMessageBox(parent, title, msg)
			msgbox.setIcon(icon)
			bt_ok = msgbox.addButton("确定", QtGui.QMessageBox.AcceptRole)
			msgbox.exec_()
		return _f
	return _render

@make_message_box(QtGui.QMessageBox.Information)
def message_box(parent, title, msg):
	pass

@make_message_box(QtGui.QMessageBox.Warning)
def warning_box(parent, title, msg):
	pass

def question_box(parent, title, msg):
	msgbox = MyMessageBox(parent, title, msg)
	msgbox.setIcon(QtGui.QMessageBox.Question)
	bt_yes = msgbox.addButton("是", QtGui.QMessageBox.YesRole)
	bt_no = msgbox.addButton("否", QtGui.QMessageBox.NoRole)
	msgbox.exec_()
	return msgbox.clickedButton() == bt_yes

class CustomEditorItemDelegate(QtGui.QItemDelegate):
	editor_method = {
		QtGui.QLineEdit: ["text", "setText", "toString"],
		QtGui.QSpinBox: ["value", "setValue", "toInt"],
		QtGui.QDoubleSpinBox: ["value", "setValue", "toDouble"],
		QtGui.QDateTimeEdit: ["date", "setDate", "toDate"],
	}

	def __init__(self, parent=None, column_cast=[], column_edtype=[]):
		'''
		@param parent: 传递给父对象。
		@param column_cast: 从编辑器读取数据时，进行Qt->Python格式数据的类型转换。
		@param column_edtype: 编辑器描述符，实现自定义的日期、价格、数量等编辑。
		'''
		self.__class = CustomEditorItemDelegate
		super(self.__class, self).__init__(parent)

		self.column_cast = column_cast
		self.column_edtype = column_edtype

	def createEditor(self, parent, option, index):
		column = index.column()
		if self.column_edtype[column]:
			edtype, kwargs = self.column_edtype[column]
			editor = getattr(self, "create%sEditor" % edtype) \
				(parent, option, index, **kwargs)
		else:
			editor = QtGui.QLineEdit(parent)
		editor.setFrame(False)
		editor.installEventFilter(self)
		return editor

	def createDateEditor(self, parent, option, index, **kwargs):
		editor = QtGui.QDateTimeEdit(QtCore.QDate.currentDate(), parent)
		editor.setCalendarPopup(True)
#		editor.setDateRange(QtCore.QDate(2005, 1, 1), QtCore.QDate(2010, 12, 31))
		return editor

	def createPriceEditor(self, parent, option, index, **kwargs):
		editor = QtGui.QDoubleSpinBox(parent)
		range = kwargs.get("range", [0, 100000])
		editor.setRange(*range)
		editor.setPrefix("￥")
		editor.setAlignment(QtCore.Qt.AlignRight)
		return editor

	def createAmountEditor(self, parent, option, index, **kwargs):
		editor = QtGui.QSpinBox(parent)
		range = kwargs.get("range", [1, 1000])
		editor.setRange(*range)
		editor.setAlignment(QtCore.Qt.AlignRight)
		return editor

	def createTextEditor(self, parent, option, index, **kwargs):
		editor = QtGui.QLineEdit(parent)
		align = kwargs.get("align", "Left")
		editor.setAlignment(eval("QtCore.Qt.Align%s" % align))
		return editor

	def setModelData(self, editor, model, index):
		editor_str = qv(self.get_editor_value(editor)).toString()
		model_str = model.data(index, QtCore.Qt.EditRole).toString()
		if editor_str == model_str:
			return

		column = index.column()
		if self.column_edtype[column]:
			edtype, kwargs = self.column_edtype[column]
		else:
			edtype = None
		if edtype == "Date":		# 日期
			time = model.data(index, QtCore.Qt.EditRole).toDateTime().time()
			datetime = QtCore.QDateTime(editor.date(), time)
			if qv(datetime.date()).toString() != model_str[:10]:
				model.setData(index, qv(datetime), QtCore.Qt.EditRole)
				# 设置日期好像不会触发dataChanged信号，不得已手动触发。
				model.emit(QtCore.SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"), index, index)
		else:
#			super(self.__class, self).setModelData(editor, model, index)
			value = self.get_editor_value(editor)
			model.setData(index, qv(value), QtCore.Qt.EditRole)

#	def sizeHint(self, option, index):
#		print "sizeHint"
#		value = super(self.__class, self)(option, index)
#		value.setHeight(8)
#		return value

	def setEditorData(self, editor, index):
		column = index.column()
		value = getattr(index.model().data(index, QtCore.Qt.EditRole),
			self.column_cast[column])()
		if isinstance(value, tuple):
			value, ok = value
		self.set_editor_value(editor, value)

#	def setModelData(self, editor, model, index):
#		column = index.column()
#		value = self.get_editor_value(editor)
#		model.setData(index, qv(value), QtCore.Qt.EditRole)

	def get_editor_value(self, editor):
		for class_ in self.__class.editor_method.keys():
			get, set, typecast = self.__class.editor_method[class_]
			if isinstance(editor, class_):
				return getattr(editor, get)()

	def set_editor_value(self, editor, value):
		for class_ in self.__class.editor_method.keys():
			get, set, typecast = self.__class.editor_method[class_]
			if isinstance(editor, class_):
				getattr(editor, set)(value)

class ColumnProp(object):
	def __init__(self):
		self.align = "Left"
		self.editable = True
		self.ismoney = False
		self.isdate = False

class ColumnPropList(object):
	def __init__(self, count=1):
		self.__prop = [ColumnProp() for i in xrange(count)]

	def __str__(self):
		props = []
		for i in xrange(len(self.__prop)):
			prop = []
			for name, value in vars(self.__prop[i]).iteritems():
				prop.append("%s = %s" % (name, value))
			props.append("<%s>" % ", ".join(prop))
		return "<ColumnPropList(%d): %s>" % (len(self.__prop), ", ".join(props))

	def __getitem__(self, index):
		if 0 <= index < len(self.__prop):
			return self.__prop[index]

	def __getattr__(self, name):
		if name.startswith("set_"):
			if name[4:] in self.__prop[0].__dict__:
				self.prop_bind = name[4:]
				return self.set_method

	def set_method(self, columns, value):
		for col in columns:
			setattr(self.__prop[col], self.prop_bind, value)

#class ColumnEditableMixIn(object):
#	def flags(self, index):
#		flags = self._parentclass.flags(self, index)
#
#		col = index.column()
#		if not self.column_prop[col].editable:
#			flags &= ~QtCore.Qt.ItemIsEditable
#		else:
#			flags |= QtCore.Qt.ItemIsEditable
#		return flags

class ColumnPropsMixIn(object):
	def flags(self, index):
		flags = self._parentclass.flags(self, index)

		col = index.column()
		if not self.column_prop[col].editable:
			flags &= ~QtCore.Qt.ItemIsEditable
		else:
			flags |= QtCore.Qt.ItemIsEditable
		return flags

	def data(self, index, role=QtCore.Qt.DisplayRole):
		value = self._parentclass.data(self, index, role)

		col = index.column()
		if role == QtCore.Qt.DisplayRole:
			if self.column_prop[col].ismoney:
				return qv("￥%.2f" % value.toDouble()[0])
			elif self.column_prop[col].isdate:
				return qv(value.toString()[:10])

		elif role == QtCore.Qt.TextAlignmentRole:
			align = QtCore.Qt.AlignVCenter | \
				eval("QtCore.Qt.Align%s" % self.column_prop[col].align)
			return qv(align)

		elif role == QtCore.Qt.TextColorRole:
			if "sourceModel" in dir(self) and "isDirty" in dir(self.sourceModel()):
				source_index = self.mapToSource(index)
				if self.sourceModel().isDirty(source_index):
					return qv(QtGui.QColor(QtCore.Qt.red))

		return value

class CachedProxyModelMixin(object):
	def __init__(self, parentmodel):
		self._parentmodel = parentmodel

		self._cache = {}

		self.connect(self,
			QtCore.SIGNAL("dataChanged(const QModelIndex &, const QModelIndex &)"),
			self.dataChanged)
		self.connect(self,
			QtCore.SIGNAL("rowsRemoved(const QModelIndex &, int, int)"),
			self.rowsRemoved)

	def lessThan(self, left, right):
		self.clear_cache()
		return self._parentclass.lessThan(self, left, right)

	def clear_cache(self):
		self._cache = {}

	def dataChanged(self, topleft, bottomright):
#		print "dataChanged"
		self.clear_cache()

	def rowsRemoved(self, index, start, end):
#		print "rowsRemoved index=%s, start=%s, end=%s" % (index, start, end)
		self.clear_cache()

	def data(self, index, role=QtCore.Qt.DisplayRole):
		key = "%d-%d-%d" % (index.row(), index.column(), role)
		if self._cache.has_key(key):
			return self._cache[key]

		value = self._parentmodel.data(self, index, role)

		self._cache[key] = value
		return value

class ComboBoxMixin(object):
	'''
	将指定的QComboBox变成带有WOW插件风格的ComboBox。
	之所以没有做成新的ComboBox类是因为需要改装UI上即有的QCombBox的原因。
	输入：combo
	输出：给combo增加了一个信号comboActivated()
	'''
	class __LineEdit(QtGui.QLineEdit):
		def keyPressEvent(self, event):
			if event.key() != QtCore.Qt.Key_Return:
				QtGui.QLineEdit.keyPressEvent(self, event)
			else:
	#			self.emit(QtCore.SIGNAL("returnPressed()"))
				self.emit(QtCore.SIGNAL("enterPressed()"))

	def __init__(self, combo):
		self.__combo = combo
		self.__edit = self.__LineEdit()
		self.__combo.setLineEdit(self.__edit)
		self.__combo.connect(self.__combo.lineEdit(),
			QtCore.SIGNAL("enterPressed()"), self.__enterPressed)
		self.__combo.connect(self.__combo,
			QtCore.SIGNAL("editTextChanged(const QString &)"),
			self.__textChanged)
		self.__combo.connect(self.__combo,
			QtCore.SIGNAL("activated(int)"),
			self.__activated)
#		self.__combo.connect(self.__combo,
#			QtCore.SIGNAL("currentIndexChanged(int)"),
#			self.__currentIndexChanged)
#		self.__combo.view().setFixedHeight(20)

	def __enterPressed(self):
		self.__combo.emit(QtCore.SIGNAL("comboActivated()"))

	def __textChanged(self, value):
		idx = self.__combo.currentIndex()

		if self.__dict__.has_key("ComboBoxMixin_textChanged_AR") or \
			idx == 0 and self.tiprow_exists():
			return

		self.ComboBoxMixin_textChanged_AR = True
		cursor_pos = self.__combo.lineEdit().cursorPosition()

#		print GBK(value), idx

		data = value
		if idx != -1:
#			data = self.__combo.itemData(idx).toString()
#			self.__combo.setCurrentIndex(-1)
#			self.__combo.setEditText(data)
			self.__combo.emit(QtCore.SIGNAL("comboActivated()"))

		text = GBK(data)
		if text:
			self.insert_tiprow(text)
		else:
			self.remove_tiprow()

		self.__combo.lineEdit().setCursorPosition(cursor_pos)
		del self.ComboBoxMixin_textChanged_AR

	def insert_tiprow(self, text):
		if self.__combo.findData(qv(text)) != -1:
			action = "移除"
		else:
			action = "添加"

		tip = "(%s %s)" % (action, text)
		if not self.tiprow_exists():
			self.__combo.insertItem(0, tip, qv("::"+text))
			self.__combo.setCurrentIndex(-1)
			self.__combo.setEditText(text)
#			print "tip inserted"
		else:
			self.__combo.setItemText(0, tip)
			self.__combo.setItemData(0, qv("::"+text))
			self.__combo.setCurrentIndex(-1)
			self.__combo.setEditText(text)
#			print "current index = %d" % self.cbFilter.currentIndex()
#			print "tip changed"

	def remove_tiprow(self, idx = 0):
		if self.tiprow_exists():
			self.__combo.removeItem(idx)
			self.__combo.setCurrentIndex(-1)
#			print "tip removed"

	def tiprow_exists(self):
		for i in xrange(self.__combo.count()):
			text = GBK(self.__combo.itemText(i))
			data = GBK(self.__combo.itemData(i).toString())
			if data.startswith("::") and text[:5] in ["(添加", "(移除"]:
				return True
		return False

	def __activated(self, idx):
		print "activated %s" % idx	#, GBK(self.cbFilter.itemText(0))

		if idx == 0 and self.tiprow_exists():
			tip = GBK(self.__combo.itemText(0))
			data = self.__combo.itemData(0).toString()[2:]
#			print tip, GBK(data)

			if tip.startswith("(添加"):
				self.__combo.addItem(data, qv(data))
				self.__combo.setCurrentIndex(-1)
				self.__combo.setEditText(data)
			else:
				i = self.__combo.findData(qv(data))
				self.__combo.removeItem(i)
				self.__combo.setCurrentIndex(-1)
				self.__combo.setEditText(data)
			return
		else:
			self.__combo.emit(QtCore.SIGNAL("comboActivated()"))

