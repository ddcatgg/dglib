# -*- coding: utf-8 -*-
import re
from dglib.thread_safe import Event


class HttpPackage(object):
	def __init__(self):
		self.head = {}
		self.method = ""
		self.path = ""
		self.param_raw = ""
		self.param = {}
		self.content = ""
		# 应答
		self.response_version = ""
		self.response_code = ""
		self.response_msg = ""

	def __str__(self):
		result = ["<%s object at 0x%X>" % (self.__class__.__name__, id(self))]
		if not self.response_code:
			result.append("head = %r" % (self.head))
			result.append("method = %r" % (self.method))
			result.append("path = %r" % (self.path))
			result.append("param = %r" % (self.param))
			result.append("content = %r" % (self.content))
		else:
			result.append("%s %s" % (self.response_code, self.response_msg))
			result.append("head = %r" % (self.head))
			result.append("content = %r" % (self.content))
		return "\n".join(result)


class HttpHandler(object):
	def __init__(self, parent):
		self.reset()
		self.head_limit = 8192
		self.content_limit = 50 * 1024 * 1024
		self.package = HttpPackage()

		self.response_dict = {
			200: "OK",
			400: "Bad Request",
			401: "Unauthorized",
			403: "Forbidden",
			404: "Not Found"
		}

		self.package_received_event = Event(parent)
		self.error_report_event = Event(parent)

	def reset(self):
		self.buf = ""
		self.content_length = 0
		self.content_recv_size = 0
		self.content_l = []		# 接收content的缓存
		self.is_chunked = False
		self.chunksize = -1
		self.chunkdata_l = []

	def handle_data(self, s):
		self.buf = "".join([self.buf, s])

		p = 0
		while True:
			if self.is_chunked:
				p = self.handle_chunked()
				if p == -1:
					break

			if not self.content_length:
				p = self.handle_head()
				if p == -1:
					break

			if self.content_length:
				p = self.handle_content()
				if p == -1:
					break

	def handle_head(self):
#		print "- handle_head()"
		p = self.buf.find("\r\n\r\n")
		if p != -1:
#			print "headlen:", p + 4
			head_s = self.buf[:p]
			self.buf = self.buf[p + 4:]

			if len(head_s) > self.head_limit:
				self.error_report_event.dispatch("HTTP_HEAD_TOO_LONG (%d/%d)" %
					(len(head_s), self.head_limit))

			self.package = self.parse_http_head(head_s)
			self.is_chunked = self.package.head.get("Transfer-Encoding", "") == "chunked"
			if not self.is_chunked:
				# 处理常规（含有Content-Length的）包
				try:
					self.content_length = int(self.package.head.get("Content-Length", 0))
				except:
					self.content_length = 0
#				print "content-length:", self.content_length
				if not self.content_length:
					self.package_received_event.dispatch(self.package)
					self.package = HttpPackage()
				else:
					if self.content_length > self.content_limit:
						self.error_report_event.dispatch("HTTP_CONTENT_TOO_LONG (%d/%d)" %
							(self.content_length, self.content_limit))
		else:
			if len(self.buf) > self.head_limit:
				self.error_report_event.dispatch("HTTP_HEAD_TOO_LONG (%d/%d)" %
					(len(self.buf), self.head_limit))

		return p

	def handle_content(self):
#		print "- handle_content()"
		p = -1
		# 为避免大数据拷贝，使用一个数组作为缓存存放每次收到的数据。
		if self.buf:
			self.content_recv_size += len(self.buf)
			self.content_l.append(self.buf)
			self.buf = ""
		if self.content_recv_size >= self.content_length:
			# HTTP内容已收全
			p = 0
			# 从缓存中还原数据
			self.buf = "".join(self.content_l)
			self.content_l = []
			self.content_recv_size = 0

			self.package.content = self.buf[:self.content_length]
			self.buf = self.buf[self.content_length:]
			self.content_length = 0
#			print "package ready, reset of buf:", len(self.buf)
			self.package_received_event.dispatch(self.package)
			self.package = HttpPackage()
		return p

	def handle_chunked(self):
		p = 0
		while p != -1:
			if self.chunksize == -1:
				p = self.handle_chunked_size()
			else:
				p = self.handle_chunked_content()
		return p

	def handle_chunked_size(self):
		p = self.buf.find("\r\n")
		if p != -1:
			try:
				self.chunksize = int(self.buf[:p], 16)
			except:
				self.chunksize = -1
				p = -1	# 错误的chunksize，终止chunk接收。
			print "chunked size:", self.chunksize
			if self.chunksize >= 0:
				self.buf = self.buf[p + 2:]
		return p

	def handle_chunked_content(self):
		p = -1
		if len(self.buf) >= self.chunksize + 2:
			p = 0
			# CHUNK内容已收全
			self.chunkdata_l.append(self.buf[:self.chunksize])
			self.buf = self.buf[self.chunksize + 2:]
			if self.chunksize == 0:
				# HTTP内容已收全
				self.package.content = "".join(self.chunkdata_l)
				print
				self.chunkdata_l = []
				self.package_received_event.dispatch(self.package)
				self.package = HttpPackage()
				p = self.buf.find("\r\n\r\n")
			self.chunksize = -1
		return p

	def parse_http_head(self, head_s):
		package = HttpPackage()
		request_line = ""
		lines = head_s.split("\r\n")
		for i, line in enumerate(lines):
			if i == 0:
				request_line = line
			else:
				p = line.find(":")
				if p != -1:
					name = line[:p]
					value = line[p + 1:].strip()
					package.head[name] = value

		if request_line:
			# 检查是否请求头
			m = re.search("(GET|POST|SUBSCRIBE|NOTIFY) +?([^ ]+)", request_line, re.I | re.M)
			if m:
				package.method, path = m.groups()
				if "?" in path:
					# aaa?xxx=yyy
					axy = path.split("?")[:2]
					package.path, package.param_raw = axy
					# aaa?xxx=yyy&mmm=nnn
					xy = package.param_raw
					xymn = xy.split("&")
					for entry in xymn:
						if "=" in entry:
							name, value = entry.split("=")[:2]
							package.param[name] = value
				else:
					package.path = path
			else:
				# 检查是否应答头
				m = re.search("HTTP/(\\d+\\.\\d+)\\s+(\\d+)\\s+?(\\w+)?", request_line, re.I | re.M)
				if m:
					package.response_version, package.response_code, package.response_msg = m.groups()
		return package

	def make_request(self, method, path, param=[], heads=[], content=""):
		request = ""
		if param:
			request = "?"
			for name, value in param:
				request = "".join([request, name, "=", value, "&"])
			else:
				request = request[:-1]

		package_s = "%s %s%s HTTP/1.1\r\n" % (method, path, request)

		head_lines = []
		content_type = ""
		for name, value in heads:
			head_lines.append("".join([name, ": ", value]))
			if name.lower() == "content-type":
				content_type = value
		if not content_type:
			head_lines.append("Content-Type: text/plain")
		head_lines.append("Content-Length: %d\r\n\r\n" % len(content))

		package_s += "\r\n".join(head_lines)
		if content:
			package_s += content

		return package_s

	def make_response(self, response_code, heads=[], content=""):
		response_msg = self.response_dict.get(response_code, "Unknown")
		package_s = "HTTP/1.1 %d %s\r\n" % (response_code, response_msg)

		head_lines = []
		content_type = ""
		for name, value in heads:
			head_lines.append("".join([name, ": ", value]))
			if name.lower() == "content-type":
				content_type = value
		if not content_type:
			head_lines.append("Content-Type: text/plain")
		head_lines.append("Content-Length: %d\r\n\r\n" % len(content))

		package_s += "\r\n".join(head_lines)
		if content:
			package_s += content

		return package_s
