# -*- coding: utf-8 -*-
from functools import wraps

from flask import current_app, request

from .util import do_basic_auth, make_cors_response, make_auth_required_response


__all__ = ['allow_cross_origin', 'support_jsonp', 'auth_required', 'auth_required_configurable']


def allow_cross_origin(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		return make_cors_response(func(*args, **kwargs))

	return wrapper


def support_jsonp(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		callback = request.args.get('callback')
		rep = func(*args, **kwargs)
		if callback:
			content = b'%s(%s)' % (str(callback), str(rep.data))
			return current_app.response_class(content, mimetype='application/javascript')
		else:
			return rep

	return wrapper


def auth_required(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		if not do_basic_auth():
			return make_auth_required_response()
		else:
			return func(*args, **kwargs)

	return wrapper


def auth_required_configurable(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		req_method = request.method
		key = 'AUTH_REQUIRED_' + func.__name__.upper()
		key_m = '_'.join([key, req_method])
		key_c = 'AUTH_REQUIRED'
		auth_needed = current_app.config.get(key) \
					  or current_app.config.get(key_m) \
					  or current_app.config.get(key_c)
		if auth_needed and not do_basic_auth():
			return make_auth_required_response()
		else:
			return func(*args, **kwargs)

	return wrapper
