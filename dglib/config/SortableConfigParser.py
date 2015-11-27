import ConfigParser


class SortableConfigParser(ConfigParser.ConfigParser):
	def __init__(self, *args, **kwargs):
		ConfigParser.ConfigParser.__init__(self, *args, **kwargs)
		self.sortfunc_ofsection = {}
		self.sortfunc = None

	def getdef(self, section, option, default):
		if not self.has_option(section, option):
			if not self.has_section(section):
				self.add_section(section)
			self.set(section, option, str(default))
		return self.get(section, option)

	def getintdef(self, section, option, default):
		if not self.has_option(section, option):
			if not self.has_section(section):
				self.add_section(section)
			self.set(section, option, str(default))
		return self.getint(section, option)

	def getfloatdef(self, section, option, default):
		if not self.has_option(section, option):
			if not self.has_section(section):
				self.add_section(section)
			self.set(section, option, str(default))
		return self.getfloat(section, option)

	def getbooleandef(self, section, option, default):
		if not self.has_option(section, option):
			if not self.has_section(section):
				self.add_section(section)
			self.set(section, option, str(default))
		return self.getboolean(section, option)

	def items(self, section, raw=False, vars=None):
		"""Return a list of tuples with (name, value) for each option
		in the section.

		All % interpolations are expanded in the return values, based on the
		defaults passed into the constructor, unless the optional argument
		`raw' is true.  Additional substitutions may be provided using the
		`vars' argument, which must be a dictionary whose contents overrides
		any pre-existing defaults.

		The section DEFAULT is special.
		"""
		d = self._defaults.copy()
		try:
			d.update(self._sections[section])
		except KeyError:
			if section != ConfigParser.DEFAULTSECT:
				raise ConfigParser.NoSectionError(section)
		# Update with the entry specific variables
		if vars:
			for key, value in vars.items():
				d[self.optionxform(key)] = value
		options = d.keys()

		# sort if needed
		cmp_func = self.sortfunc_ofsection.get(section)
		if cmp_func:
			options.sort(cmp=cmp_func)
		elif self.sortfunc:
			options.sort(cmp=self.sortfunc)

		if "__name__" in options:
			options.remove("__name__")
		if raw:
			return [(option, d[option])
					for option in options]
		else:
			return [(option, self._interpolate(section, option, d[option], d))
					for option in options]

	def write(self, fp):
		"""Write an .ini-format representation of the configuration state."""
		if self._defaults:
			fp.write("[%s]\n" % ConfigParser.DEFAULTSECT)
			for (key, value) in self._defaults.items():
				fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
			fp.write("\n")
		for section in self._sections:
			fp.write("[%s]\n" % section)
			for (key, value) in self.items(section):	# use our modified items()
				if key != "__name__":
					fp.write("%s = %s\n" %
							 (key, str(value).replace('\n', '\n\t')))
			fp.write("\n")
