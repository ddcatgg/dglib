import time
import threading

import zmq
from thread_safe import Event


class BaseServer(object):
	def __init__(self, url):
		self.url = url	# "tcp://*:5555"
		self.mode = zmq.REP
		self.ctx = zmq.Context.instance()
		self.debug = False

		self.recv_event = Event(self)
		self.reply = ""

		self._thread_work = None
		self.exiting = False

	def activate(self):
		'''
		bind may cause zmq.error.ZMQError
		e.strerror : "Permission denied" or "Address in use"
		'''
		if self._thread_work:
			return False

		result = True
		try:
			self.sock = self.ctx.socket(self.mode)
			self.sock.bind(self.url)
		except zmq.error.ZMQError:
			result = False

		self._thread_work = threading.Thread(target=self.thread_work)
		self._thread_work.setDaemon(True)
		self._thread_work.start()
		return result

	def thread_work(self):
		pass

	def deactivate(self):
		if self._thread_work:
			self.exiting = True
			self._thread_work.join()

			self.sock.setsockopt(zmq.LINGER, 0)
			self.sock.close()

	def send(self, msg):
		if isinstance(msg, unicode):
			msg = msg.encode("utf-8")
		self.sock.send(msg)


class RepServer(BaseServer):
	def __init__(self, url):
		BaseServer.__init__(self, url)
		self.mode = zmq.REP

	def thread_work(self):
		while not self.exiting:
			msg = self.sock.recv()
			if self.debug:
				self.traceline("<< recv(%d): %s" % (len(msg), msg))
			self.recv_event.dispatch(msg)
			reply = self.reply
			if self.debug:
				self.traceline(">> send(%d): %s" % (len(reply), reply))
			self.sock.send(reply)

class PullServer(BaseServer):
	def __init__(self, url):
		BaseServer.__init__(self, url)
		self.mode = zmq.PULL

	def thread_work(self):
		while not self.exiting:
			msg = self.sock.recv()
			if self.debug:
				self.traceline("<< recv(%d): %s" % (len(msg), msg))
			self.recv_event.dispatch(msg)


if __name__ == "__main__":
	server = RepServer(60000)
	server.activate()
	while True:
		time.sleep(1)
