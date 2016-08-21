# http://blog.csdn.net/ghostfromheaven/article/details/7671853
import threading


class Singleton(object):
	"""
	usage:
		class MyClass(Singleton):
			pass
	"""
	def __new__(cls, *args, **kw):
		if not hasattr(cls, '_instance'):
			orig = super(Singleton, cls)
			cls._instance = orig.__new__(cls, *args, **kw)
		return cls._instance


class Singleton2(type):
	"""
	usage:
		class MyClass(object):
			__metaclass__ = Singleton2
	"""
	def __init__(cls, name, bases, _dict):
		super(Singleton2, cls).__init__(name, bases, _dict)
		cls._instance = None

	@classmethod
	def __call__(cls, *args, **kw):
		if cls._instance is None:
			cls._instance = super(Singleton2, cls).__call__(*args, **kw)
		return cls._instance


class SingletonMixin(object):
	__instance = None
	__lock = threading.RLock()

	@classmethod
	def get_instance(cls, *args, **kw):
		with cls.__lock:
			if cls.__instance is None:
				cls.__instance = cls(*args, **kw)
			return cls.__instance


'''
def singleton(cls):
	"""
	usage:
		@singleton
		class MyClass(object):
			pass
	"""
	instances = {}
	_lock = threading.RLock()
	def _singleton(*args, **kw):
		with _lock:
			if cls not in instances:
				instances[cls] = cls(*args, **kw)
			return instances[cls]
	return _singleton
'''


def singleton(cls):
	"""
	usage:
		@singleton
		class MyClass(object):
			pass
	"""
	@classmethod
	def get_instance(cls, *args, **kw):
		with cls.__lock:
			if not cls.__instance:
				cls.__instance = cls(*args, **kw)
			return cls.__instance

	def _singleton(*args, **kw):
		return cls(*args, **kw)

	cls.__lock = threading.RLock()
	cls.__instance = None
	cls.get_instance = get_instance
	return cls


def test():
	@singleton
	class MyClass(object):
		def __init__(self, a, b, c=0):
			print "myclass", a, b, c

	my1 = MyClass(1, 2)
	my2 = MyClass(3, 4, 5)
	assert(my1 != my2)
	assert(MyClass.get_instance(11, 22) == MyClass.get_instance())


if __name__ == '__main__':
	test()
