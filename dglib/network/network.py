# -*- coding: utf-8 -*-
from __future__ import with_statement
import time
import threading
import select
import socket

from dglib.thread_safe import SafeList, QueueEx


class TcpClient(object):
	def __init__(self, host, port):
		self.host = host
		self.port = port

		self.sock = None

	def activate(self):
		pass

	def send(self, data):
		pass

	def disconnect(self):
		pass

	def on_connected(self, sock):
		pass

	def on_disconnected(self):
		pass

	def on_recv(self, data):
		pass

	def on_send(self, data):
		pass

	def on_sent(self, data):
		pass

	def on_connect_error(self):
		pass

	def on_recv_error(self):
		pass

	def on_send_error(self):
		pass


class TcpServer(object):
	MAX_CLIENTS_COUNT = 300

	def __init__(self, host, port):
		self.host = host
		self.port = port

		self.sock = None

		self._clients = SafeList()

		self._thread_listen = None

	def activate(self):
		pass

	def deactivate(self):
		pass

	def verify_connection(self, addr):
		return True

	def new_client(self, sock, addr):
		result = False
		return result

	def make_client(self, sock, addr):
		return TcpConnection(self, sock, addr)

	def remove_client(self, client):
		pass


class TcpConnection(object):
	def __init__(self, parent, sock, addr):
		self.parent = parent
		self.sock = sock
		self.host, self.port = addr

	def activate(self):
		pass

	def send(self, data):
		pass

	def _send(self, data):
		try:
			total_sent = 0
			while total_sent < len(data):
				sent = self.sock.send(data[total_sent:])
				if sent:
					total_sent += sent
				else:
					total_sent = 0
					break
		except socket.error:
			total_sent = 0
		return total_sent

	def on_recv_error(self):
		pass

	def on_send_error(self):
		self.disconnect()

	def disconnect(self):
		pass

	def handle_data(self, data):
		pass


def test_tcp_server():
	server = TcpServer("127.0.0.1", 1001)
	server.activate()
	while True:
		time.sleep(1)


if __name__ == "__main__":
	test_tcp_server()
