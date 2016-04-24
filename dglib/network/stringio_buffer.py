# -*- coding: utf-8 -*-
from cStringIO import StringIO


class Buffer(object):
	def __init__(self, data=""):
		self.buf = StringIO()
		if data:
			self.buf.write(data)

	def __str__(self):
		return self.buf.getvalue()

	def __len__(self):
		o = self.buf.tell()
		self.buf.seek(0, 2)		# 2 = os.SEEK_END
		x = self.buf.tell()
		self.buf.seek(o)
		return x

	def __getitem__(self, i):
		# not support slice-step
		c = len(self)
		if not isinstance(i, slice):
			if i >= c or i < -c:
				raise IndexError("buffer index out of range")
			if i < 0:
				i = len(self) + i
			i = slice(i, i + 1)
		start = i.start
		stop = i.stop
		if start is None:
			start = 0
			i = None
		if stop is None:
			stop = c
			i = None
		if i is None:
			i = slice(start, stop)
		o = self.buf.tell()
		self.buf.seek(i.start)
		data = self.buf.read(i.stop - i.start)
		self.buf.seek(o)
		return data

	def write(self, s):
		self.buf.write(s)

	def drop(self, n):
		# 如果将数据作为StringIO构造函数的参数传递会导致cStringIO构造成StringI，
		# 或StringIO构造后pos为0，调用write前需要seek，否则会导致覆盖已有的数据。
		buf_new = StringIO()
		buf_new.write(self.buf.getvalue()[n:])
		self.buf = buf_new

	def truncate(self, pos):
		self.buf.truncate(pos)


if __name__ == "__main__":
	pass
