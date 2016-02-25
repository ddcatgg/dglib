# -*- coding: utf-8 -*-
import inspect


class NoSuccMethodError(ValueError):
	pass


class ParamsNotEnoughError(ValueError):
	pass


class MethodRouter(object):
	def __init__(self, obj, prefix=''):
		self.obj = obj
		self.prefix = prefix			# eg: 'handle_'
		self.action_alias = {}			# eg: {'start': 'launch'}
		self.key_translation_table = {}	# eg: {'from': 'from_', 'type': 'type_'}

	def route(self, action, params):
		meth = getattr(self.obj, self.prefix + self.action_alias.get(action, action), None)
		if meth is None or not inspect.ismethod(meth):
			raise NoSuccMethodError('no such method!')

		d = params.copy()
		# 转换参数中与关键字冲突的键
		for k in d:
			nk = self.key_translation_table.get(k)
			if nk:
				d[nk] = d[k]
				del d[k]

		# 检验参数个数及名称是否正确
		args, _, _, defaults = inspect.getargspec(meth)
		if args and args[0] == 'self':
			args.pop(0)	# 忽略self参数
		c = len(args)
		dc = len(defaults) if defaults else 0
		default_kw = {args[-i]: defaults[-i] for i in range(1, dc + 1)}
		kw = {}
		# 填充必填参数
		for i in range(c - dc):
			k = args[i]
			v = d.get(k)	# 如果有必填参数未传递，则键值为None，后面会检测。
			kw[k] = v

		# 检测是否有必填参数未传递
		if filter(lambda x: x is None, kw.values()):
			raise ParamsNotEnoughError('method params not enough!')

		# 补填可选参数
		for k, v in default_kw.items():
			if k not in kw:
				kw[k] = d.get(k, v)

		return meth, kw
