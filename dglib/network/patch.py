import socket
import ssl


def getaddrinfo_ipv4(host, port, family=0, socktype=0, proto=0, flags=0):
	family = socket.AF_INET
	return socket._origin_getaddrinfo(host, port, family, socktype, proto, flags)


def patch_getaddrinfo():
	if not getattr(socket, '_origin_getaddrinfo', None):
		socket._origin_getaddrinfo = socket.getaddrinfo
		socket.getaddrinfo = getaddrinfo_ipv4


def patch_ssl():
	"""
	patch for Python version greater than 2.7.9
	https://www.python.org/dev/peps/pep-0476/
	"""
	try:
		_create_unverified_https_context = ssl._create_unverified_context
	except AttributeError:
		# Legacy Python that doesn't verify HTTPS certificates by default
		pass
	else:
		# Handle target environment that doesn't support HTTPS verification
		ssl._create_default_https_context = _create_unverified_https_context
		# eventlet.green.ssl do use create_default_content
		ssl.create_default_context = _create_unverified_https_context
