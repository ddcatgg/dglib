# -*- coding: utf-8 -*-
from base64 import b64decode
from flask import current_app, request, make_response, jsonify


__all__ = ['succ_response', 'fail_response', 'do_basic_auth', 'make_auth_required_response', 'make_cors_response']


def succ_response(msg=None, value=None):
	return jsonify(code=0, msg=msg, value=value)


def fail_response(code, msg=None):
	return jsonify(code=code, msg=msg)


def do_basic_auth():
	server_user_pwd = current_app.config.get('AUTH_INFO')
	if not server_user_pwd:
		return True

	auth = request.headers.get('Authorization', '')
	if auth.startswith('Basic '):
		b64 = auth[6:]
		try:
			user_pwd = b64decode(b64)
		except TypeError:
			pass
		else:
			if user_pwd == server_user_pwd:
				return True
	return False


def make_auth_required_response():
	rep = make_response('Unauthorized Access', 401)
	rep.headers['WWW-Authenticate'] = 'Basic realm="Authentication Required"'
	return rep


def make_cors_response(*args):
	"""
	创建一个允许跨域请求的应答
	CORS（Cross-Origin Resource Sharing）跨域资源共享
	:param args:
	:return:
	"""
	rep = make_response(*args)
	rep.headers['Access-Control-Allow-Origin'] = '*'
	rep.headers['Access-Control-Allow-Methods'] = 'PUT,GET,POST,DELETE'
	allow_headers = "Referer,Accept,Origin,User-Agent"
	rep.headers['Access-Control-Allow-Headers'] = allow_headers
	return rep
