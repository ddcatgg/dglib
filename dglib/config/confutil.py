# -*- coding: utf-8 -*-


def update_globals_from_pyfile(filename, target=None, update_nonexists=False):
	module = load_conf_file_as_module(filename)
	return update_globals_from_module(module, target, update_nonexists)


def update_globals_from_module(module, target=None, update_nonexists=False):
	config = {}
	updated = {}
	for key in dir(module):
		if key.isupper():
			config[key] = getattr(module, key)
	if target is None:
		target = globals()
	orig = target.copy()
	for k, v in config.iteritems():
		if update_nonexists or k in orig and v != orig[k]:
			target[k] = v
			updated[k] = v
	return updated


def load_conf_file_as_module(filename):
	import imp
	module = imp.new_module('conf')
	module.__file__ = filename
	# module.__dict__['APPPATH'] = APPPATH
	try:
		with open(filename) as f:
			exec(compile(f.read(), filename, 'exec'), module.__dict__)
	except IOError:
		raise # IOError('Unable to load configuration file (%s) - %s' % (filename, e.strerror))
	return module
