# -*- coding: gbk -*-
import time
import xml.etree.cElementTree as ET

from twisted.internet import reactor, protocol, task
from twisted.protocols.policies import TimeoutMixin

from handler.httphandler import HttpHandler
from dglib.xmlutil import xmlelem_from_text, pretty_indent
from dglib.tracer import Tracer2


class TopicServer(object):
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.listener = None
		self.protocol = TopicServerProtocol
		self.info = dict(name="TopicServer", model="TopicServer", version="1.0")
		self.option = {}
		self.option["timeout"] = 60
		self.option["log"] = False
		self.notifier_order = []
		self.notifiers = {}

	def make_introduction(self):
		elem_system = ET.Element("System")
		# <Identity>
		elem_identity = ET.SubElement(elem_system, "Identity")
		elem_name = ET.SubElement(elem_identity, "Name")
		elem_name.text = self.info.get("name", "")
		elem_model = ET.SubElement(elem_identity, "Model")
		elem_model.text = self.info.get("model", "")
		elem_version = ET.SubElement(elem_identity, "Version")
		elem_version.text = self.info.get("version", "")
		# <ObjectList>
		elem_objectlist = ET.SubElement(elem_system, "ObjectList")
		for name in self.notifier_order:
			notifier = self.notifiers[name]
			desc = notifier.__doc__
			if desc is None:
				desc = ""
			else:
				desc = desc.strip()
			elem = ET.SubElement(elem_objectlist, name)
			try:
				subelems = []
				for line in desc.split("\n"):
					subelem = xmlelem_from_text(line)
					subelems.append(subelem)
				for subelem in subelems:
					elem.append(subelem)
			except SyntaxError:
				elem.text = desc
		pretty_indent(elem_system, space=" "*8)
		xml = ET.tostring(elem_system, encoding="gbk")
		return xml

	def start(self):
		topic_factory = protocol.ServerFactory()
		topic_factory.protocol = self.protocol
		topic_factory.introduction = self.make_introduction()
		topic_factory.option = self.option
		topic_factory.notifiers = self.notifiers
		self.listener = reactor.listenTCP(self.port, topic_factory, interface=self.host)

	def realport(self):
		return self.listener.getHost().port

	def register_notifier(self, topic, notifier):
		self.notifier_order.append(topic)
		self.notifiers[topic] = notifier

	def get_notifier(self, topic, default=None):
		return self.notifiers.get(topic, default)


class TopicServerProtocol(protocol.Protocol, TimeoutMixin):

	def __repr__(self):
		return "<TopicServerProtocol %s:%d server_port=%d>" % \
			(self.host, self.port, self.serverport)

	def connectionMade(self):
		self.host = self.transport.getPeer().host
		self.port = self.transport.getPeer().port
		self.serverport = self.transport.getHost().port
		self.introduction = self.factory.introduction
		self.option = self.factory.option
		self.debug = self.option["log"] not in [None, False, 0]
		self.notifiers = self.factory.notifiers

		self.login_ok = False
		self.subscribed_topics = set()

		if self.debug:
			v = self.option["log"]
			kw = v.copy() if isinstance(v, dict) else {}
			if kw.get("name") is None:
				kw["name"] = "TopicServer%d" % self.serverport
			if kw.get("subtitle") is None:
				kw["subtitle"] = "(%s-port%d)" % (self.host, self.port)
			self.tracer = Tracer2(**kw)
			self.tracer.info("connected from %s:%d" % (self.host, self.port))

		self.handler = HttpHandler(self)
		self.handler.package_received_event.add_listener(self.on_package_received)

		self.setTimeout(self.option["timeout"])

	def connectionLost(self, reason=protocol.connectionDone):
		if self.debug: self.tracer.info("disconnected\n")

		# 解除订阅
		for topic in self.subscribed_topics:
			notifier = self.notifiers.get(topic)
			if notifier:
				notifier.remove_subscriber(self)

	def dataReceived(self, data):
		if self.debug: self.tracer.debug("recv(%d bytes): %s\n" % (len(data), data.replace("\r\n", "\n")))

		self.handler.handle_data(data)

	def on_package_received(self, sender, package):
		self.resetTimeout()

		if not self.login_ok:
			if package.method == "GET" and package.path == "/Login":
				self.process_login(package)
			else:
				self.disconnect()
		else:
			if package.method == "SUBSCRIBE":
				self.process_subscribe(package)
			elif self.subscribed_topics:
				if package.method in ("GET", "POST"):
					self.process_common_request(package)
				else:	# 无效命令
					self.disconnect()
			else:	# 尚未订阅
				self.disconnect()

	def process_login(self, package):
		username = package.param.get("username", "")
		password = package.param.get("password", "")
		if username == "admin" and password == "admin":
			self.login_ok = True
			heads = [("Content-Type", "text/xml")]
			content = self.introduction
			self.send_response(heads=heads, content=content)
		else:
			self.disconnect()

	def process_subscribe(self, package):
		'''
		/Subscribe?objects=
		'''
		topics_s = package.param.get("objects", "")
		if topics_s:
			response = self.handler.make_response(200)
			self.send(response)
			topics = topics_s.split("|")
			if "*" in topics:
				topics = self.notifiers.keys()	# 订阅所有主题
			self.subscribe(topics)
		else:
			response = self.handler.make_response(400)
			self.send(response)

	def subscribe(self, topics):
		if self.subscribed_topics != topics:
			self.unsubscribe()
			self.subscribed_topics = topics
			for topic in topics:
				notifier = self.notifiers.get(topic)
				if notifier:
					notifier.add_subscriber(self)
					data = notifier.make_notify()
					if data is not None:
						self.send_notify(data)

	def unsubscribe(self):
		for topic in self.subscribed_topics:
			self.notifiers.remove_subscribe(topic)
		self.subscribed_topics = ""

	def process_common_request(self, package):
		# "/UpdateDevicesXml" -> "hreq_updatedevicesxml"
		processor_name = "hreq" + package.path.replace("/", "_").lower()
		path_processor = getattr(self, processor_name, None)
		if path_processor:
			path_processor(package)
		else:
			if self.debug: self.tracer.error("*** error! request handler not exists: %r" % path_processor)
			self.send_response(404)

	def send(self, s):
		if self.debug: self.tracer.debug("send(%d bytes): %s\n" % (len(s), s.replace("\r\n", "\n")))
		self.transport.write(s)

	def send_notify(self, s):
		self.send(self.handler.make_request("NOTIFY", path="/", content=s))

	def send_response(self, response_code=200, heads=[], content=""):
		self.send(self.handler.make_response(response_code, heads, content))

	def disconnect(self):
		self.transport.loseConnection()

	def timeoutConnection(self):			# 重载的超时方法
		self.transport.abortConnection()	# 如果不重载默认是loseConnection()


class Notifier(object):
	def __init__(self):
		self.subscribers = set()

	def add_subscriber(self, subscriber):
		self.subscribers.add(subscriber)

	def remove_subscriber(self, subscriber):
		if subscriber in self.subscribers:
			self.subscribers.remove(subscriber)

	def notify(self, data=None):
		'''
		向所有订阅者发送通知
		'''
		if data is None:
			data = self.make_notify()
		if data is not None:
			for subscriber in self.subscribers:
				subscriber.send_notify(data)

	def make_notify(self):
		return ""


class StatusNotifier(Notifier):
	'''
	<Status>服务器基本状态信息，如运行时间、当前数据流量等</Status>
	'''
	def __init__(self):
		Notifier.__init__(self)
		self.ordered_keys = "RunTime|Time|CpuGlobalPercent|CpuPercent|MemPercent|MemTotal|MemUsed|"\
			"MemAvailable|NetRecv|NetSent|NetTotal".split("|")
		self.data = {}
		self.time_start = time.clock()

	def make_notify(self):
		return self.make_notify_status()

	def make_notify_status(self):
		self.update_data()
		elem_notify = ET.Element("Notify")
		elem_status = ET.SubElement(elem_notify, "Status")
		for key in self.ordered_keys:
			val = self.data.get(key)
			if not isinstance(val, basestring):
				val = str(val)
			elem = ET.SubElement(elem_status, key)
			elem.text = val
		xml = ET.tostring(elem_notify, encoding="gbk")
		return xml

	def update_data(self):
		import psutil
		# Time
		self.data["RunTime"] = int(time.clock() - self.time_start)
		self.data["Time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
		# Cpu
		self.data["CpuGlobalPercent"] = int(psutil.cpu_percent())
		curr_process = psutil.Process()
		self.data["CpuPercent"] = int(curr_process.cpu_percent())
		# Mem
		meminfo = psutil.virtual_memory()
		self.data["MemPercent"] = int(meminfo.percent)
		self.data["MemTotal"] = int(meminfo.total)
		self.data["MemUsed"] = int(meminfo.used)
		self.data["MemAvailable"] = int(meminfo.free)
		# Net
		netinfo = psutil.net_io_counters()
		bytes_recv = netinfo.bytes_recv
		bytes_sent = netinfo.bytes_sent
		self.data["NetRecv"] = bytes_recv
		self.data["NetSent"] = bytes_sent
		self.data["NetTotal"] = bytes_recv + bytes_sent


def update_status():
	notifier_status.notify()


if __name__ == "__main__":
	notifier_status = StatusNotifier()

	server = TopicServer("0.0.0.0", 1000)
	server.register_notifier("Status", notifier_status)
	server.option["log"] = True
	server.start()

	timer = task.LoopingCall(update_status)
	timer.start(1)

	reactor.run()

