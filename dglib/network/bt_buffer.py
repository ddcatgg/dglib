# The contents of this file are subject to the Python Software Foundation
# License Version 2.3 (the License).  You may not copy or use this file, in
# either source code or executable form, except in compliance with the License.
# You may obtain a copy of the License at http://www.python.org/license.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

ctypes = None
try:
	import ctypes
except ImportError:
	pass


from cStringIO import StringIO

class cStringIO_Buffer(object):

	def __init__(self, s=""):
		self.buffer = StringIO()
		if s:
			self.buffer.write(s)
		for attr in dir(self.buffer):
			self.__dict__[attr] = getattr(self.buffer, attr)

	def __getattr__(self, attr):
		return getattr(self.buffer, attr)

	def _slice_to_a_b(self, i):
		if not isinstance(i, slice):
			if i >= len(self):
				raise IndexError("buffer index out of range")
			i = slice(i, i + 1)
		o = self.tell()
		if i.start is None:
			a = 0
		else:
			a = i.start
		if i.stop is None:
			b = o
		else:
			b = i.stop
		if b < 0:
			b = o + b
		b = max(a, b - a)
		return o, a, b

	def __setitem__(self, i, d):
		o, a, b = self._slice_to_a_b(i)
		self.seek(a)
		self.write(d)
		self.seek(o)

	def __getitem__(self, i):
		o, a, b = self._slice_to_a_b(i)
		self.seek(a)
		d = self.read(b)
		self.seek(o)
		return d

	def drop(self, size):
		if size > 0:
			v = self.getvalue()
			self.truncate(0)
			self.write(buffer(v, size))

	def __len__(self):
		o = self.tell()
		self.seek(0, 2)
		x = self.tell()
		self.seek(o)
		return x

	def __str__(self):
		return self.getvalue()

Buffer = cStringIO_Buffer

# slow, has dependencies
if False: # ctypes:

	class ctypes_Buffer(object):

		def __init__(self):
			self.length = 32
			self.data = ctypes.create_string_buffer(self.length)
			self.written = 0
			self.offset = 0

		def __setitem__(self, i, y):
			if isinstance(i, slice):
				return self.data.__setslice__(i.start, i.stop, y)
			else:
				return self.data.__setitem__(i, y)

		# TODO: call PyBuffer_FromMemory!
		def __getitem__(self, i):
			if isinstance(i, slice):
				if i.stop < 0:
					i = slice(i.start, self.written + i.stop)
				return self.data.__getslice__(i.start or 0, i.stop or self.written)
			else:
				return self.data.__getitem__(i)

		def __getattr__(self, attr):
			return getattr(self.data, attr)

		def __str__(self):
			return self.data[:self.written]

		def __len__(self):
			return self.written

		def _oversize(self, l):
			o = self.length
			while l > self.length:
				self.length *= 2
			if self.length > o:
				d = self.data
				self.data = ctypes.create_string_buffer(self.length)
				# which is faster?
				#self.data[0:self.written] = d[:self.written]
				self.data[0:o] = d

		def write(self, s):
			l = len(s)
			self._oversize(self.offset + l)
			self.data[self.offset:self.offset + l] = s
			self.offset += l
			self.written = max(self.written, self.offset)
			return l

		def seek(self, offset):
			self.offset = min(self.written - 1, max(0, offset))

		def truncate(self, size=None):
			if size is None:
				size = self.offset
			self.written = size
			self.offset = min(size, self.offset)

		def drop(self, size):
			if size < 0:
				raise ValueError("cannot discard negative bytes")
			size = min(size, self.written)
			new_written = self.written - size
			# ow
			try:
				self.data[:new_written] = self.data[size:self.written]
			except ValueError:
				print new_written, size, self.written
			self.written = new_written
			self.offset = min(self.written, self.offset)

	Buffer = ctypes_Buffer


def func1(s):
	b = Buffer(s)
	for i in xrange(100000):
		b.write("hello" * 10)
	result = b.getvalue()	# 500M well lead to a MemoryError
	return result

def func2(s):
	b = [s]
	for i in xrange(100000):
		b.append("hello" * 10)
	result = "".join(b)
	return result

def func3(s):
	b = bytearray(s)
	for i in xrange(100000):
		b.extend("hello" * 10)
	result = str(b)		# 500M well lead to a MemoryError
	return result

def func4(s):
	for i in xrange(100000):
		s += "hello" * 10
	return s

def func5(s):
	from array import array
	char_array = array('c')
	for i in xrange(100000):
		char_array.fromstring("hello" * 10)
	return char_array.tostring()


def test_performance():
	import timeit
	x = timeit.Timer(stmt="'a' + 'b'")
	print x.timeit()

	x = timeit.Timer(stmt="''.join(['a', 'b'])")
	print x.timeit()
	print

	stmt = """\
b.write("hello" * 10)
"""
	t = timeit.timeit(stmt=stmt, setup="from __main__ import Buffer; b = Buffer('hello' * 1000)", number=100000)
	print "%.2f usec/pass" % (1000000 * t / 100000)

	stmt = """\
b.append("hello" * 10)
"""
	t = timeit.timeit(stmt=stmt, setup="b = ['hello' * 1000]", number=100000)
	print "%.2f usec/pass" % (1000000 * t / 100000)

	stmt = """\
b.extend("hello" * 10)
"""
	t = timeit.timeit(stmt=stmt, setup="b = bytearray('hello' * 1000)", number=100000)
	print "%.2f usec/pass" % (1000000 * t / 100000)

	stmt = """\
s += "hello" * 10
"""
	t = timeit.timeit(stmt=stmt, setup="s = 'hello' * 1000", number=100000)
	print "%.2f usec/pass" % (1000000 * t / 100000)

	stmt = """\
char_array.fromstring("hello" * 10)
"""
	t = timeit.timeit(stmt=stmt, setup="from array import array; char_array = array('c')", number=100000)
	print "%.2f usec/pass" % (1000000 * t / 100000)


def test_functional():
	b = Buffer()
	b.write("abcde12")
	b.seek(0)
	b.write(buffer("hello"))
	assert(str(b) == "hello12")
	b.drop(1)
	assert(str(b) == "ello12")
	b[2:3] = 'q'	# known issue: nothing happen if assign an empty string.
	assert str(b) == "elqo12"
	assert b[0] == "e"
	#print repr(b[:-1])
	assert b[:-1] == "elqo1"
	#assert len(b) <= b.length
	assert len(b) == len(str(b))
	b.drop(1)
	b.seek(0)
	b.write('foo')
	assert b[0] == 'f'
	try:
		b[100]
	except IndexError:
		pass
	else:
		assert False


def test():
	test_functional()
	test_performance()

if __name__ == "__main__":
	test()
