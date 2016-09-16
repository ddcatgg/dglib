import time
import win32process
import threading
from twisted.web.http import stringToDatetime


class ExpiredChecker(object):
	def __init__(self, time_expired, interval=20 * 60):
		self.time_expired = time_expired
		self.interval = interval

		self._thread_check = threading.Thread(target=self.thread_check)
		self._thread_check.setDaemon(True)
		self._thread_check.start()

	def thread_check(self):
		sec = time.clock()
		while True:
			time.sleep(1)
			if time.clock() - sec > self.interval:
				if time.time() > self.time_expired:
					self.on_expired()
					break

	def on_expired(self):
		win32process.ExitProcess(0)


def get_http_date(url):
	try:
		rep = requests.get(url)
	except:
		pass
	else:
		# get server date
		server_date = rep.headers.get('date')
		if server_date:
			# 1477189234 = time.mktime((2016,10,23,10,20,34,0,0,0))
			t = stringToDatetime(server_date)
			return t


def test():
	checker = ExpiredChecker(time_expired=time.time(), interval=1)
	while True:
		time.sleep(1)


if __name__ == "__main__":
	test()
