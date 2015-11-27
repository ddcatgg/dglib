import sys
import time
import subprocess
from cStringIO import StringIO

class Popen(object):
	def __init__(self, cmdline, shell=True, verbose=False):
		self.cmdline = cmdline
		self.shell = shell
		self.verbose = verbose
		self.stdout = StringIO()
		self.stderr = StringIO()

	def open(self):
		self.stdout.truncate(0)
		self.stderr.truncate(0)
		popen = subprocess.Popen(self.cmdline, shell=self.shell, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		ec = 0
		while True:
			s = popen.stdout.read(1)
			if s:
				self.stdout.write(s)
				if self.verbose:
					sys.stdout.write(s)
			else:
				time.sleep(0.01)
			ec = popen.poll()
			if ec != None:
				s = popen.stdout.read()
				if s:
					self.stdout.write(s)
					if self.verbose:
						sys.stdout.write(s)
				s = popen.stderr.read()
				if s:
					self.stderr.write(s)
					if self.verbose:
						sys.stderr.write(s)
				self.stdout.seek(0)
				self.stderr.seek(0)
				break
		return ec
