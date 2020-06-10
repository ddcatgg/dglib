from __future__ import absolute_import

import re
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError, DEFAULTSECT

from ..basis.ordered_dict import OrderedDictCaseInsensitive
from ..utils import SYS_ENCODING


class IniFile(RawConfigParser):
	def __init__(self, filename=None, encoding=None, get_unicode=False, compact=False):
		RawConfigParser.__init__(self, dict_type=OrderedDictCaseInsensitive)
		if encoding is None:
			encoding = SYS_ENCODING
		self._encoding = encoding
		self._get_unicode = get_unicode
		self._compact = compact
		if filename:
			self.load(filename)

	def load(self, filename=None):
		if not filename:
			filename = self.filename
		else:
			self.filename = filename

		try:
			fp = open(filename)
		except IOError:
			return

		if self._encoding == 'utf-8-sig':
			# skip BOM
			fp.read(3)

		self.readfp(fp, filename)

	def save(self, filename=None):
		if not filename:
			filename = self.filename

		fp = open(filename, 'w')
		if self._encoding == 'utf-8-sig':
			# write BOM
			fp.write(b'\xef\xbb\xbf')

		self.write(fp)

	def encode(self, text):
		encoding = self._encoding
		if encoding == 'utf-8-sig':
			encoding = 'utf-8'
		return text.encode(encoding)

	def decode(self, bytes_):
		encoding = self._encoding
		if encoding == 'utf-8-sig':
			encoding = 'utf-8'
		return bytes_.decode(encoding)

	def set(self, section, option, value=None):
		if not self.has_section(section):
			self.add_section(section)
		if isinstance(value, unicode):
			value = self.encode(value)
		elif not isinstance(value, str):
			value = str(value)
		RawConfigParser.set(self, section, option, value)

	def _get(self, section, option, default=''):
		try:
			value = RawConfigParser.get(self, section, option)
		except Exception, e:
			if isinstance(e, (NoSectionError, NoOptionError)):
				return default
			raise e
		return value

	def get(self, *args, **kw):
		if self._get_unicode:
			return self.getunicode(*args, **kw)
		else:
			return self._get(*args, **kw)

	def getunicode(self, section, option, default=u''):
		value = self._get(section, option, default)
		if not isinstance(value, unicode):
			value = unicode(value, self._encoding)
		return value

	def getint(self, section, option, default=0):
		value = self.get(section, option)
		if value.isdigit():
			return int(value)
		else:
			return default

	def getfloat(self, section, option, default=0.):
		value = self.get(section, option)
		if re.match(r'\d*?\.?\d+$', value):
			return float(value)
		else:
			return default

	# overloaded (no lower)
	def optionxform(self, optionstr):
		return optionstr

	# overloaded (key = val -> key=val ?)
	def write(self, fp):
		"""Write an .ini-format representation of the configuration state."""

		# unicode -> bytes
		def toBytes(s):
			return str(s) if not isinstance(s, unicode) else self.encode(s)

		if self._defaults:
			fp.write('[%s]\n' % toBytes(DEFAULTSECT))
			for (key, value) in self._defaults.items():
				fp.write('%s = %s\n' % (toBytes(key), toBytes(value).replace('\n', '\n\t')))
			fp.write('\n')
		for section in self._sections:
			fp.write('[%s]\n' % toBytes(section))
			for (key, value) in self._sections[section].items():
				if key == '__name__':
					continue
				if (value is not None) or (self._optcre == self.OPTCRE):
					val = toBytes(value).replace('\n', '\n\t')
					if self._compact:
						line = '='.join((toBytes(key), val))
					else:
						line = ' = '.join((toBytes(key), val))
				else:
					line = key  # value is None and self._optcre == OPTCRE_NV
				fp.write('%s\n' % line)
			fp.write('\n')


def test():
	ini = IniFile('test.ini')
	name = ini.get('option', 'name', 'aaa')
	print name
	name += str(len(name))
	ini.set('option', 'name', name)
	ini.save()


if __name__ == '__main__':
	test()
