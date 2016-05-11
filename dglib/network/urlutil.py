# -*- coding: gbk -*-
import time
import urllib
import urllib2
import cookielib
import Cookie
import gzip
from cStringIO import StringIO


class Fetcher(object):
	def __init__(self, retry=0, retry_delay=5, validator=None):
		self.retry = retry
		self.retry_delay = retry_delay
		self.validator = validator
		self.iterator = map

	def _fetch(self, opener):
		result = OpenerResult(opener)
		opener.html = None
		opener.err = None
		try:
			result.html = opener.open()
#		except urllib2.HTTPError, e:
#			print "HttpError:", e.code
#		except urllib2.URLError, e:
#			print e
#		except socket.timeout, e:
#			print e
		except Exception, e:
			import traceback
			e.traceback = traceback.format_exc()
			result.err = e
		return result

	def on_retry(self, retry, openers):
		validate_error_operers = filter(lambda x: hasattr(x, 'validate_error') and x.validate_error, openers)
		print "正在重试 (%d/%d) ... (%d个页面/%d个检验失败)" % (retry, self.retry, len(openers), len(validate_error_operers))
		should_break = len(openers) == len(validate_error_operers)
		return not should_break

	def fetch(self, openers):
		results = [OpenerResult(opener) for opener in openers]
		retry = 0
		_openers = openers[:]
		while _openers and retry <= self.retry:
			if retry:
				time.sleep(self.retry_delay)
				if not self.on_retry(retry, _openers):
					break
			for result in self.iterator(self._fetch, _openers):
				if result.err is None:
					ok = self.validator(result) if self.validator else True
					if ok:
						_openers.remove(result.opener)
					else:
						# 检验失败时设置一个标志，这个标志是设置在临时局部opener对象上的，不影响传入的openers。
						result.opener.validate_error = True
						result.err = ValueError('validate error')
				results[openers.index(result.opener)] = result

			retry += 1
		return results


class EventletFetcher(Fetcher):
	def __init__(self, retry=0, retry_delay=5, validator=None):
		Fetcher.__init__(self, retry, retry_delay, validator)
		import eventlet
		pool = eventlet.GreenPool(100)
		self.iterator = pool.imap


class OpenerResult(object):
	def __init__(self, opener, html=None, err=None):
		self.opener = opener
		self.html = html
		self.err = err

	def get_tuple(self):
		return self.opener, self.html, self.err


class BaseOpener(object):
	def __init__(self, url, timeout):
		self.url = url
		self.timeout = timeout

	def open(self):
		rep = urllib2.urlopen(self.url, timeout=self.timeout)
		return self.read(rep)

	def read(self, rep):
		if rep.info().get("Content-Encoding") == "gzip":
			buf = StringIO(rep.read())
			f = gzip.GzipFile(fileobj=buf)
			html = f.read()
		else:
			html = rep.read()
		return html


class Opener(BaseOpener):
	default_timeout = 20

	def __init__(self, url, addheaders=None, postdata=None, timeout=None,
		headers=None, cookie_jar=None):
		BaseOpener.__init__(self, url, timeout)
		if cookie_jar is not None:
			self.cookie_jar = cookie_jar
		else:
			self.cookie_jar = cookielib.CookieJar()
		self.opener = self._build_opener()
		if not addheaders:
			addheaders = []
		if "User-Agent" not in dict(addheaders):
			addheaders.append(("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36"))
		self.opener.addheaders = addheaders
		if headers:
			for k, v in headers.iteritems():
				self.set_header(k, v)
		self.postdata = postdata
		self.timeout = timeout if timeout else self.default_timeout

	def _build_opener(self):
		return urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))

	def open(self):
		postdata = self.postdata
		if postdata:
			if isinstance(postdata, dict):
				postdata = urllib.urlencode(postdata.items())
		else:
			postdata = None
		rep = self.opener.open(self.url, data=postdata, timeout=self.timeout)
		return self.read(rep)

	@classmethod
	def create(cls, request_raw, cookie=None, postdata=None, timeout=None,
		url=None, user_agent=None, referer=None, cookie_jar=None, header_keys=None):
		'''
		@param cookie: 字符串或字典
		'''
		d = parse_request_raw(request_raw)
		if url:
			d["url"] = url
		if user_agent:
			d["User-Agent"] = user_agent
		if referer:
			d["Referer"] = referer

		if "Cookie" in d:
			del d["Cookie"]

		# header_keys = "Referer User-Agent".split()
		addheaders = make_addheaders(d, header_keys)
		result = cls(d["url"], addheaders, postdata, timeout, cookie_jar=cookie_jar)
		if cookie is not None:
			cookies = build_cookie(cookie, domain=d.get("Host", ""))
			result.set_cookie(cookies)
		return result

	def get_cookie(self):
		return list(self.cookie_jar)

	def set_cookie(self, cookie, domain=""):
		'''
		@param cookie: 接受字符串、字典、cookielib.Cookie对象及其列表。
		'''
		if isinstance(cookie, cookielib.Cookie):
			cookies = [cookie]
		if isinstance(cookie, list):
			cookies = cookie
		else:	# str, dict
			cookies = build_cookie(cookie, domain)
		for cookie_obj in cookies:
			self.cookie_jar.set_cookie(cookie_obj)

	def clear_cookie(self):
		self.cookie_jar.clear()

	def extract_cookie(self):
		'''
		将cookie导出成为带域名的字典，由于会丢失Cookie对象的一些其他信息，不建议再使用此函数。
		'''
		result = {}
		for cookie_obj in self.cookie_jar:
			d = result.setdefault(cookie_obj.domain, {})
			d[cookie_obj.name] = cookie_obj.value
		return result

	def set_header(self, key, val):
		set_addheaders(self.opener.addheaders, key, val)


class EventletOpener(Opener):
	def _build_opener(self):
		from eventlet.green import urllib2
		return urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))	# @UndefinedVariable


class Request(object):
	def __init__(self):
		self.url = ""
		self.headers = {}
		self.data = ""
		self.cookie_s = ""

	@classmethod
	def parse(cls, request_raw):
		result = None
		req = Request()
		d = parse_request_raw(request_raw)
		url = d.get("url")
		if url:
			req.cookie_s = d.get("Cookie", "")
			headers = d.copy()
			del headers["url"]
			del headers["Cookie"]
			del headers["Content-Length"]
			postdata = request_raw.split("\n\n")[-1].strip()
			req.url = url
			req.data = postdata
			result = req
		return result


def parse_request_raw(request_raw):
	result = {}
	lines = request_raw.split("\n")
	i = 0
	for line in lines:
		line = line.strip()
		if i == 0:
			if not line:
				continue
			else:
				import re
				m = re.match(r"(?:GET|POST) ([^ ]+) HTTP/\d+.\d+", line)
				if m:
					url = m.group(1)
					if not url.startswith("http"):
						url = "http://%s%s" % (result.get("Host", ""), url)
					result["url"] = url
					continue
		if not line.strip():
			break
		items = line.split(":", 1)
		if len(items) == 2:
			key, val = items
			result[key] = val.strip()
		i += 1

	return result


def parse_postdata_table(s):
	if isinstance(s, unicode):
		s = s.encode("utf8")
	result = {}
	lines = filter(None, s.strip().split("\n"))
	for line in lines:
		items = line.split("\t")
		if len(items) == 2:
			key, val = items
			result[key] = val
	return result


def make_addheaders(d, keys=None):
	lower_keys = map(lambda x: x.lower(), keys) if keys else None
	return [(k, v) for k, v in d.iteritems() if not lower_keys or k.lower() in lower_keys]


def set_addheaders(addheaders, key, val):
	i = 0
	for header in addheaders:
		i += 1
		k, v = header
		if k == key:
			addheaders.remove(header)
			break
	addheaders.insert(i, (key, val))


def build_cookie(cookie, domain=""):
	if isinstance(cookie, basestring):
		cookie_s = cookie
	else:
		cookie_s = "; ".join(["%s=%s" % (k, v) for k, v in cookie.iteritems()])

	ck = Cookie.SimpleCookie(cookie_s)
	result = []
	for k in ck:
		v = ck[k]	# v is a Morsel Object
		cookie_obj = cookielib.Cookie(name=v.key,
									  value=v.value,
									  version=0,
									  port=None,
									  port_specified=False,
									  domain=domain,
									  domain_specified=True,
									  domain_initial_dot=True,
									  path="/",
									  path_specified=True,
									  secure=False,
									  expires=None,
									  discard=False,
									  comment=None,
									  comment_url=None,
									  rest={"HttpOnly": None},
									  rfc2109=False,
									)
		result.append(cookie_obj)
	return result


def decode_netscape_cookies(s):
	result = {}
	for line in s.split("\n"):
		if "\t" in line:
			items = line.split("\t")
			if items:
				domain = items[0]
				k, v = items[-2:]
				d = result.get(domain, {})
				d[k] = v
				result[domain] = d
	return result


def urlopen(url, cookie, postdata=None, referer=None, user_agent=None, timeout=None, eventlet=False):
	if eventlet:
		_Opener = EventletOpener
		_Fetcher = EventletFetcher
	else:
		_Opener = Opener
		_Fetcher = Fetcher
	if not user_agent:
		user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36"
	if isinstance(url, basestring):
		urls = [url]
	else:
		urls = url
	openers = []
	for _url in urls:
		opener = _Opener.create("", url=_url, postdata=postdata, cookie=cookie,
			referer=referer, user_agent=user_agent, timeout=timeout)
		openers.append(opener)
	fetcher = _Fetcher()
	results = fetcher.fetch(openers)
	if isinstance(url, basestring):	# 如果不是打开一批网址，则返回值也不是列表。
		results = results[0]
	return results
