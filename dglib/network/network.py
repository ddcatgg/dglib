# -*- coding: gbk -*-
from __future__ import with_statement
import time
import threading
import select
import socket

import _libpath
from tracer import get_tracer
from thread_safe import SafeList, QueueEx
from SocketIOModal.SelectSocketIOModal import SelectSocketIOModal


class TcpClient(object):
	MAX_TRY_CONNECT = 3
	def __init__(self, host, port):
		self.host = host
		self.port = port

		self._tracer = get_tracer(str(self.__class__), "%s@%d" % (host, port))
		#self._tracer.logger.screen_handler.setLevel(50)

		self.sock = None

		self.__active = False
		self._exiting = False

		self.__lock = threading.RLock()
		self._thread_connect = None

		self.modal = SelectSocketIOModal(self)

	def free(self):
		with self.__lock:
			if self._exiting:
				return
			self._exiting = True

		if self._thread_connect:
			self._thread_connect.join()
			self._thread_connect = None

		self.modal.terminate()

	def activate(self):
		with self.__lock:
			if self._exiting or self.__active:
				return
			self.__active = True

			# 防止与 free() 中对 self._thread_connect 的操作冲突。
			self._thread_connect = threading.Thread(target=self.thread_connect,
				args=(self.host, self.port))
			self._thread_connect.setDaemon(True)
			self._thread_connect.start()

	def thread_connect(self, host, port):
		for _ in xrange(self.MAX_TRY_CONNECT):
			if self._exiting:
				return

			self.on_before_open_socket()
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			except socket.error:
				self.on_after_open_socket(False)
				continue
			self.on_after_open_socket(True)

			self.on_before_connect(host, port)
			try:
#				sock.setblocking(True)
				sock.settimeout(2.0)
				sock.connect((host, port))
			except socket.error:
				self.on_after_connect(host, port, False)
				sock.close()
				continue
			self.on_after_connect(host, port, True)

			self.sock = sock
			self.modal.start(sock)
			self.on_connected(sock)	# 必须在modal.start()后调用，否则在on_connected()中发送数据会被忽略。
			return

		with self.__lock:
			self.__active = False	# 以便在on_connect_error()中可以重新activate()

		self.on_connect_error()

	def send(self, data):
		self.modal.send(data)

	def disconnect(self):
		self.modal.disconnect()

	def on_before_open_socket(self):
		self._tracer.trace(">>>Socket opening(TCP)...")
		pass

	def on_after_open_socket(self, ok):
		self._tracer.traceline("SUCCESS" if ok else "FAILED!")
		pass

	def on_before_connect(self, host, port):
		self._tracer.trace(">>>Connecting to %s:%d ... " % (host, port))
		pass

	def on_after_connect(self, host, port, ok):
		self._tracer.traceline("SUCCESS" if ok else "FAILED!")
		pass

	def on_connected(self, sock):
		pass

	def on_disconnected(self):
		with self.__lock:
			self.__active = False
		self._tracer.traceline("connection broken.")

	def on_received(self, data):
		pass

	def on_send(self, data):
		pass

	def on_sent(self, data):
		pass

	def on_receive_overflow(self):
		pass

	def on_send_overflow(self):
		pass

	def on_connect_error(self):
		pass

	def on_receive_error(self):
		self.modal.disconnect_deferred()

	def on_send_error(self):
		self.modal.disconnect_deferred()

	def on_close_error(self):
		self._tracer.traceline("SOCKET CLOSE ERROR!!")

class TcpServer(object):
	MAX_CLIENTS_COUNT = 300
	def __init__(self, host, port):
		self.host = host
		self.port = port

		self.sock = None
		self._exiting = False

		self._lock = threading.RLock()
		self._clients = SafeList()

		self._thread_listen = None

		self._tracer = get_tracer(str(self.__class__), "%s@%d" % (host, port))

	def activate(self):
		if self._thread_listen and self._thread_listen.isAlive():
			return

		self._thread_listen = threading.Thread(target=self.thread_listen,
				args=(self.host, self.port))
		self._thread_listen.setDaemon(True)
		self._thread_listen.start()

	def deactivate(self):
		if not self._thread_listen:
			return

		self._exiting = True
		self._thread_listen.join()
		self._thread_listen = None
		self._exiting = False

	def thread_listen(self, host, port):
		while not self._exiting:
			time.sleep(1)

			self._tracer.trace(">>>Socket opening(TCP)...")
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#				sock.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
			except socket.error:
				self._tracer.traceline("FAILED!")
				continue
			self._tracer.traceline("OK")

			self._tracer.trace(">>>Socket binding(port %d)..." % port)
			try:
				sock.bind((host, port))
			except socket.error:
				self._tracer.traceline("FAILED!")
				sock.close()
				continue
			self._tracer.traceline("OK")

			self._tracer.trace(">>>Socket listening...")
			try:
				sock.listen(5)
			except socket.error:
				self._tracer.traceline("FAILED!")
				sock.close()
				continue
			self._tracer.traceline("OK")

			break

		while not self._exiting:
			try:
				sock.settimeout(2.0)
				conn, addr = sock.accept()
				conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
			except socket.error:
#				self._tracer.traceline(">>>An \"accept\" error happened!")
#				sock.close()
				continue

			if not self.verify_connection(addr):
				conn.close()
				continue

			if not self.new_client(conn, addr):
				conn.close()
				continue

	def verify_connection(self, addr):
		return True

	def new_client(self, sock, addr):
		result = False
		self._clients.lock()
		self._tracer.traceline(">>>Connecting from %s at port %s" % addr)
		if self._clients.count() >= self.MAX_CLIENTS_COUNT:
			self._tracer.traceline("Client limit(%d) reached." %
				self.MAX_CLIENTS_COUNT)
		else:
			client = self.make_client(sock, addr)
			if client:
				self._clients.add(client)
				self._tracer.traceline("Total number of connections is %d/%d" %
						(self._clients.count(), self.MAX_CLIENTS_COUNT))
				client.activate()
				result = True
			else:
				self._tracer.traceline("make_client() failed!")
		self._clients.unlock()

		return result

	def make_client(self, sock, addr):
		return TcpConnection(self, sock, addr)

	def remove_client(self, client):
		self._clients.lock()

		self._tracer.traceline("Connection(%s:%d) broken." %
				(client.host, client.port))
		self._clients.remove(client)
		self._tracer.traceline("Total number of connections is %d/%d" %
				(self._clients.count(), self.MAX_CLIENTS_COUNT))

		self._clients.unlock()

#	def client_count(self):
#		return self._clients.count()

class TcpConnection(object):
	MAX_QUEUE_SIZE = 100 * 10000
	def __init__(self, parent, sock, addr):
		self.parent = parent
		self.sock = sock
		self.host, self.port = addr

		self._exiting = False
		self.queue_send = QueueEx(self.MAX_QUEUE_SIZE)

		self._thread_recv = None
		self._thread_send = None
		self._thread_sweeper = None

		self._lock = threading.RLock()

		self._tracer = get_tracer(str(self.__class__),
			"%s@%d" % (self.host, self.port))

	def __del__(self):
		self._tracer.traceline("__del__()")

	def activate(self):
		if self._thread_recv:
			return

		self._thread_recv = threading.Thread(target=self.thread_recv)
		self._thread_recv.setDaemon(True)
		self._thread_recv.start()

		self._thread_send = threading.Thread(target=self.thread_send)
		self._thread_send.setDaemon(True)
		self._thread_send.start()

	def thread_recv(self):
		MAX_BYTES_RECV = 64 * 1024

		while not self._exiting:
			try:
				ready = select.select([self.sock], [], [], 2)
				if not ready[0]:
					continue

				data = self.sock.recv(MAX_BYTES_RECV)
				if not data:
					self.on_receive_error()
					break
			except socket.error:
				self.on_receive_error()
				break

			self.handle_data(data)

	def thread_send(self):
		while not self._exiting:
			try:
				ready = select.select([], [self.sock], [], 2)
				if not ready[1]:
					continue

				if not self.queue_send.empty():
					data = self.queue_send.get()
	#				self._tracer.traceline("Send %d bytes data: %s" %
	#					(len(data), format_frame(data)))
					if not self._send(data):
						self._tracer.traceline("Send failed!")
						self.on_send_error()
						break
				else:
					time.sleep(0.001)

			except socket.error:
				self.on_send_error()
				break

	def send(self, data):
		return self.queue_send.put_nowait(data)

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

#	def linger_and_close(self):
#		while not self.queue_send.empty():
#			time.sleep(0.001)
#
#		self.disconnect()

	def on_receive_error(self):
		self._tracer.traceline("on_receive_error()")
		self.disconnect()

	def on_send_error(self):
		self._tracer.traceline("on_send_error()")
		self.disconnect()

	def disconnect(self):
		self.free()

	def handle_data(self, data):
		pass

	def free(self):
		with self._lock:
			if not self._thread_sweeper:
				self._thread_sweeper = threading.Thread(target=self.thread_sweeper)
				self._thread_sweeper.setDaemon(True)
				self._thread_sweeper.start()

	def thread_sweeper(self):
#		self._tracer.traceline("sweeper()")
		self._exiting = True
		self.parent.remove_client(self)

		if self._thread_recv:
			self._thread_recv.join()
			self._thread_recv = None
		if self._thread_send:
			self._thread_send.join()
			self._thread_send = None

		if self.sock:
			self.sock.close()
			self.sock = None

		self._thread_sweeper = None
#		self._tracer.traceline("sweeper() over")

def test_tcp_server():
	server = TcpServer("127.0.0.1", 1001)
	server.activate()
	while True:
		time.sleep(1)

if __name__ == "__main__":
	test_tcp_server()
