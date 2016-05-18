import socket


def getaddrinfo_ipv4(host, port, family=0, socktype=0, proto=0, flags=0):
	family = socket.AF_INET
	return socket._origin_getaddrinfo(host, port, family, socktype, proto, flags)


def patch_getaddrinfo():
	if not getattr(socket, '_origin_getaddrinfo', None):
		socket._origin_getaddrinfo = socket.getaddrinfo
		socket.getaddrinfo = getaddrinfo_ipv4

