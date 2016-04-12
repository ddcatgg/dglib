import time
import socket
import logging
import eventlet

from dglib import tracer
from dglib.thread_safe import Strand


class EventletWSGIServer(object):
	def __init__(self, app, bindip, bindport, logfile=None,
				 socket_timeout=60, **kwargs):
		self.app = app
		self.bindip = bindip
		self.bindport = bindport
		self.logfile = logfile
		self.socket_timeout = socket_timeout
		self.kwargs = kwargs

		self.sock = None
		self.errno = 0
		self.strand = None

	def start(self,):
		succ = self.bind(self.bindip, self.bindport)
		if succ:
			self.serve_forever(self.logfile)
		return succ

	def bind(self, ip, port, retry=0):
		result = False
		for _ in range(1 + retry):
			try:
				self.sock = eventlet.listen((ip, port))
			except socket.error, e:
				self.errno = e.errno	# 10048: bind error
				time.sleep(1)
			else:
				self.errno = 0
				result = True
				break
		return result

	def serve_forever(self, logfile=None):
		if 'log' not in self.kwargs:
			if logfile:
				log = tracer.CompositeFile(logfile, 'w', nocache=True)
			else:
				log = logging.getLogger('wsgi')	# tracer.BlackHole()
			self.kwargs['log'] = log
		eventlet.wsgi.server(self.sock, self.app,
							socket_timeout=self.socket_timeout,
							**self.kwargs)

	def init_strand(self, daemon=True):
		self.strand = Strand()
		self.strand.start(daemon)

	def start_inthread(self, daemon=True):
		succ = self.bind_inthread(daemon)
		if succ:
			self.serve_forever_inthread()
		return succ

	def bind_inthread(self, retry=0, daemon=True):
		if not self.strand:
			self.init_strand(daemon)

		defer = self.strand.synchronize(self.bind, self.bindip, self.bindport, retry)
		return defer.wait_value()

	def serve_forever_inthread(self):
		if self.strand:
			self.strand.synchronize(self.serve_forever, self.logfile)
