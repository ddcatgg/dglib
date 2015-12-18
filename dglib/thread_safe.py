# -*- coding: utf-8 -*-
from __future__ import with_statement
import time
import ctypes
import Queue
import threading
import traceback
import inspect
import weakref
from basis import weakmethod	# 取自 PyPubSub v3.2 的 pubsub.core.weakmethod


class SafeList(object):
	def __init__(self, init_list=None, lock=None):
		if init_list is None:
			init_list = []
		self._list = init_list

		if lock:
			self.lock = lock
		else:
			self.lock = threading.RLock()

	def __repr__(self):
		with self:
			result = "%r" % self._list
		return result

	def __str__(self):
		return self.__repr__()

	def __len__(self):
		return len(self._list)

	def __setitem__(self, idx, val):
		with self:
			self._list[idx] = val

	def __getitem__(self, idx):
		with self:
			val = self._list[idx]
		return val

	def __enter__(self):
		self.lock.acquire()

	def __exit__(self, exc_type, exc_value, traceback):
		self.lock.release()

	def append(self, val):
		with self:
			self._list.append(val)

	def remove(self, val):
		with self:
			self._list.remove(val)

	def index(self, val):
		with self:
			idx = self._list.index(val)
		return idx

	def clear(self):
		self[:] = []	# will call self.__setitem__(<type 'slice'>, [])

	def count(self):
		with self:
			result = len(self._list)
		return result

	def lock(self):
		self._lock.acquire()

	def unlock(self):
		self._lock.release()


class QueueEx(Queue.Queue):
	def __init__(self, maxsize=0):
		self.maxsize = maxsize
		# Queue.Queue不是继承自object，无法使用super()。
		Queue.Queue.__init__(self, maxsize)

	def get_nowait(self):
		try:
			item = Queue.Queue.get_nowait(self)
			return (True, item)
		except:
			return (False, None)

	def put_nowait(self, item):
		try:
			Queue.Queue.put_nowait(self, item)
			return True
		except:
			return False

	def clear(self):
		while self.get_nowait()[0]:
			pass

	def getall(self, limit=0):
		# 需小心，如果放得比拿得还快会死循环。
		result = []
		while True:
			ret, val = self.get_nowait()
			if ret:
				result.append(val)
				if limit and len(result) >= limit:
					break
			else:
				break
		return result


class SafeArray(list):
	def __init__(self, count, lock=None):
		list.__init__(self, [0] * count)

		if lock:
			self.lock = lock
		else:
			self.lock = threading.RLock()

	def __setitem__(self, idx, value):
		self.lock.acquire()
		list.__setitem__(self, idx, value)
		self.lock.release()

	def __getitem__(self, idx):
		self.lock.acquire()
		value = list.__getitem__(self, idx)
		self.lock.release()
		return value


class SafeBoolArray(SafeArray):
	def __setitem__(self, idx, value):
		self.lock.acquire()
		if value:
			SafeArray.__setitem__(self, idx, 1)
		else:
			SafeArray.__setitem__(self, idx, 0)
		self.lock.release()


class Property(object):
	def __init__(self, name_value_pair, locks=None):
		self.__dict__["_%s__keys" % self.__class__.__name__] = \
			[name for name, value in name_value_pair]
		self._props = []
		for i, [name, value] in enumerate(name_value_pair):
			self._props.append(name)
			self.__dict__["_%s_lock" % name] = locks[i] if locks \
				else threading.RLock()
			self.__dict__["_%s" % name] = value
			self.__dict__["%s_changed" % name] = None
		self.changed = None

	def __getattr__(self, name):
		if name in self.__keys:
			self.__dict__["_%s_lock" % name].acquire()
			value = self.__dict__["_%s" % name]
			self.__dict__["_%s_lock" % name].release()
			return value
		elif name in self.__dict__:
			return self.__dict__[name]

		raise AttributeError("'%s' object has no attribute '%s'" %
			(self.__class__.__name__, name))

	def __setattr__(self, name, value):
		if name in self.__keys:
			old_value = self.__dict__["_%s" % name]
			if old_value != value:
				self.__dict__["_%s_lock" % name].acquire()
				self.__dict__["_%s" % name] = value
				notify_event = self.__dict__["%s_changed" % name]
				if notify_event:
					notify_event(self, old_value, value)
				if self.changed:
					self.changed(self, name, old_value, value)
				# 当属性作为列表中的一个元素时，宿主程序可能会在事件处理中读取这个列表中的
				# 其他项，而与此同时其他项可能正在或已经被其他线程更改，造成在事件处理时这
				# 个列表的整体数据无法处于稳定状态。解决办法是，对这个列表的所有Property
				# 对象指定同一个锁，这样在一个元素被更改并进入事件时，其他线程对其他元素的
				# 操作就被挂起，因此能够正确地读取整个列表的元素。
				self.__dict__["_%s_lock" % name].release()
		else:
			self.__dict__[name] = value

	def prop_index(self, name):
		return self._props.index(name)


class Event(object):
	def __init__(self, parent=None, name=""):
		# 使用了weakref和WeakMethod防止循环引用
		self.ref_parent = None if parent is None else weakref.ref(parent)
		self.name = name
		self.ref_listeners = []

	def add_listener(self, listener):
		if inspect.ismethod(listener):
			ref_listener = weakmethod.WeakMethod(listener)
		else:
			ref_listener = weakref.ref(listener)
		if ref_listener not in self.ref_listeners:
			self.ref_listeners.append(ref_listener)

	def remove_listener(self, listener):
		ref_listener = weakmethod.WeakMethod(listener)
		if ref_listener in self.ref_listeners:
			self.ref_listeners.remove(ref_listener)

	def remove_all_listener(self):
		self.ref_listeners = []

	def dispatch(self, *args, **kwargs):
		should_remove = []
		for ref_listener in self.ref_listeners:
			listener = ref_listener()
			if listener:
				try:
					if self.ref_parent:
						parent = self.ref_parent()
						if parent is None:
							continue
					else:
						parent = None
					listener(parent, *args, **kwargs)
				except:	# Exception, e:
					traceback.print_exc()
			else:
				should_remove.append(ref_listener)

		# clean
		for ref_listener in should_remove:
			self.ref_listeners.remove(ref_listener)


class Property2(object):
	def __init__(self, parent, name_value_pair, locks=None):
		self.__dict__["parent"] = parent
		self.__dict__["_%s__keys" % self.__class__.__name__] = \
			[name for name, value in name_value_pair]
		self._props = []
		for i, [name, value] in enumerate(name_value_pair):
			self._props.append(name)
			self.__dict__["_%s_lock" % name] = locks[i] if locks \
				else threading.RLock()
			self.__dict__["_%s" % name] = value
			self.__dict__["%s_changed" % name] = Event(parent)
		self.changed = Event(parent)

	def __getattr__(self, name):
		if name in self.__keys:
			with self.__dict__["_%s_lock" % name]:
				value = self.__dict__["_%s" % name]
			return value
		elif name in self.__dict__:
			return self.__dict__[name]

		raise AttributeError("'%s' object has no attribute '%s'" %
			(self.__class__.__name__, name))

	def __setattr__(self, name, value):
		if name in self.__keys:
			old_value = self.__dict__["_%s" % name]
			if old_value != value:
				with self.__dict__["_%s_lock" % name]:
					self.__dict__["_%s" % name] = value
					evt_notifier = self.__dict__["%s_changed" % name]
					evt_notifier.dispatch(old_value, value)
					self.changed.dispatch(name, old_value, value)
					# 当属性作为列表中的一个元素时，宿主程序可能会在事件处理中读取这个列表中的
					# 其他项，而与此同时其他项可能正在或已经被其他线程更改，造成在事件处理时这
					# 个列表的整体数据无法处于稳定状态。解决办法是，对这个列表的所有Property
					# 对象指定同一个锁，这样在一个元素被更改并进入事件时，其他线程对其他元素的
					# 操作就被挂起，因此能够正确地读取整个列表的元素。
		else:
			self.__dict__[name] = value

	def prop_index(self, name):
		return self._props.index(name)


class Strand(object):
	def __init__(self):
		self._thread_work = None
		self._queue_work = Queue.Queue()
		self._lock = threading.RLock()

	def start(self, daemon=True):
		with self._lock:
			if not (self._thread_work and self._thread_work.isAlive()):
				self._thread_work = threading.Thread(target=self.thread_work)
				self._thread_work.setDaemon(daemon)
				self._thread_work.start()

	def stop(self):
		with self._lock:
			if self._thread_work and self._thread_work.isAlive():
				self.synchronize(None)
				self._thread_work.join()
				while not self._queue_work.empty():
					self._queue_work.get()

	def join(self, timeout=None):
		self._thread_work.join(timeout)

	def thread_work(self):
		while True:
			if not self.dispatch():
				break

	def dispatch(self):
		item = self._queue_work.get()
		method, result, args, kwargs = item
		if method is not None:
			result.value = method(*args, **kwargs)
			result.event.set()
			return True
		else:
			return False

	def synchronize(self, method, *args, **kwargs):
		class StandResult(object):
			def __init__(self):
				self.event = threading.Event()
				self.value = None

			def wait(self, timeout=None):
				self.event.wait(timeout)
				return self.event.is_set()

			def wait_value(self):
				self.event.wait()
				return self.value

		result = StandResult()
		self._queue_work.put((method, result, args, kwargs))
		return result


class DeferCall(object):
	def __init__(self):
		self.works = []
		self.lock = threading.RLock()

		val = ctypes.c_int64()
		ctypes.windll.Kernel32.QueryPerformanceFrequency(ctypes.byref(val))
		self.freq = val.value

		self.terminated = False
		self._thread_defer = threading.Thread(target=self.thread_work)
		self._thread_defer.setDaemon(True)
		self._thread_defer.start()

	def tick(self):
		val = ctypes.c_int64()
		ctypes.windll.Kernel32.QueryPerformanceCounter(ctypes.byref(val))
		return val.value

	def thread_work(self):
		while not self.terminated:
			func = None
			with self.lock:
				tick = self.tick()
				if self.works:
					self.works.sort()
					item = self.works[0]
					t, func, args, kwargs = item
					if tick >= t:
						self.works.pop(0)
					else:
						func = None
			if func:
				func(*args, **kwargs)
			time.sleep(0.01)

	def call_later(self, secs, func, *args, **kwargs):
		t = self.tick() + secs * self.freq
		with self.lock:
			self.works.append((t, func, args, kwargs))


def defercall_func(results, *args, **kwargs):
	t = int(time.time())
	results.append([t, args, kwargs])


def test_defercall():
	t = int(time.time())
	results = []
	defer = DeferCall()
	defer.call_later(2, defercall_func, results, 4, 5, foo=6)
	defer.call_later(1, defercall_func, results)

	time.sleep(3)
	assert len(results) == 2
	t1, args1, kwargs1 = results[0]
	t2, args2, kwargs2 = results[1]
	assert t1 - t == 1
	assert args1 == ()
	assert kwargs1 == {}
	assert t2 - t == 2
	assert args2 == (4, 5)
	assert kwargs2 == {"foo": 6}


def test_strand():
	strand = Strand()
	result = strand.synchronize(time.sleep, 1)
	strand.start()
	assert result.wait(2) == True
	assert result.value is None


def test():
	import unittest
	suite = unittest.TestSuite(map(unittest.FunctionTestCase, (test_strand, test_defercall)))
	runner = unittest.TextTestRunner()
	runner.run(suite)


if __name__ == "__main__":
	test()
