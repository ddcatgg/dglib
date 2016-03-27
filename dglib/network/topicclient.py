# -*- coding: gbk -*-
from twisted.internet import reactor, protocol, task

import tracer
from thread_safe import Event
from httphandler import HttpHandler
from timeout_guard import TimeoutGuardMixIn

DEBUG = False

class TopicClient(object):
	def __init__(self, host, port):
		self.host = host
		self.port = port

		self.notify_received_event = Event(self)
		self.connected_event = Event(self)
		self.disconnected_event = Event(self)
		self.active = False

		self.connector = None
		self.timeout_connect = 5

	def start(self):
		if not self.active:
			self.active = True
			factory = protocol.ReconnectingClientFactory()
			factory.initialDelay = 5
			factory.maxDelay = 5
			factory.protocol = TopicClientProtocol
			factory.owner = self
			self.connector = reactor.connectTCP(self.host, self.port, factory,
												timeout=self.timeout_connect)

	def stop(self):
		if self.active:
			self.connector.factory.stopTrying()
			self.connector.disconnect()
			self.active = False

	def send_package(self, method, path, content=""):
		package = "%s %s HTTP/1.1\r\nContent-Length:%d\r\n\r\n%s" % \
			(method, path, len(content), content)
		return self.send(package)

	def send(self, data):
		if self.connector:
			transport = getattr(self.connector, "transport", None)
			if transport:
				transport.write(data)

	def build_handler(self, prop):
		handler = HttpHandler(prop)
		return handler


class TopicClientProtocol(protocol.Protocol, TimeoutGuardMixIn):

#	def __init__(self):
#		print "TopicClientProtocol.__init__"
#
#	def __del__(self):
#		print "__del__", self

	def connectionMade(self):
		self.factory.resetDelay()

		self.handler = self.factory.owner.build_handler(self)
		self.handler.package_received_event.add_listener(self.on_package_received)

		if DEBUG:
			self.tracer = tracer.get_tracer(self.__class__.__name__)
			self.traceline = self.tracer.traceline
			self.traceline("connected")

		self.login("admin", "admin")
		self.subscribe()

		TimeoutGuardMixIn.__init__(self, timeout=60 * 1000)
		self.timeoutguard_start()

		self._timer_subscribe = task.LoopingCall(self.subscribe)	# 注意：循环引用
		self._timer_subscribe.start(20)	# 每20秒周期性地重新订阅

		self.factory.owner.connected_event.dispatch()

	def connectionLost(self, reason):
		self.timeoutguard_stop()

		self._timer_subscribe.stop()
		self._timer_subscribe = None	# 解除循环引用

		if DEBUG: self.traceline("!!! disconnected!\n")

		self.factory.owner.disconnected_event.dispatch()

	def dataReceived(self, data):
		self.handler.handle_data(data)

	def on_package_received(self, sender, package):
		self.timeoutguard_reset()

		if DEBUG: self.traceline(package)

		if package.method == "NOTIFY":
			self.process_notify(package)

	def process_notify(self, package):
		self.factory.owner.notify_received_event.dispatch(package.content)

	def on_timeoutguard_timeout(self):
		self.disconnect()

	def send(self, s):
		self.transport.write(s)

	def send_notify(self, s):
		self.send(self.handler.make_request("NOTIFY", path="/", content=s))

	def send_response(self, response_code=200, heads=[], content=""):
		self.send(self.handler.make_response(response_code, heads, content))

	def login(self, uid, pwd):
		param = (("username", uid), ("password", pwd))
		request = self.handler.make_request("GET", "/Login", param)
		self.send(request)

	def subscribe(self, topics="*"):
		request = self.handler.make_request("SUBSCRIBE", "/Subscribe?objects=%s" % topics)
		self.send(request)

	def disconnect(self):
		self.transport.loseConnection()


def test_round(client):
	client.start()
	client.stop()

def callback(client):
	param = []
	param.append("ip%d=%s" % (1, "aaaa"))
	param.append("channel%d=%d" % (2, 3))
	param.append("alarm%d=%d" % (4, 5))
	client.send_package("GET", "/Alarm?%s" % "&".join(param))

def test():
	client = TopicClient("127.0.0.1", 62001)
#	task.LoopingCall(test_round, client).start(1)
	reactor.callLater(10, callback, client)
	client.start()
	reactor.run()

if __name__ == "__main__":
	test()
