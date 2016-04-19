# -*- coding: utf-8 -*-


def attr_gbk(elem, name):
	return elem.attrib.get(name).encode("GBK")


def attr_int(elem, name):
	return int(elem.attrib.get(name))


def attr_bool(elem, name):
	return bool(elem.attrib.get(name))


def attr(elem, *args):
	if len(args) > 1:
		result = []
		for name in args:
			result.append(attr(elem, name))
		return result

	[name] = args
	value = elem.attrib.get(name)
	if not value:
		return value
	elif isinstance(value, unicode):
		return value.encode("utf-8")
	elif value.isdigit():
		return int(value)
	elif value.lower() in ["true", "false"]:
		return value.lower() == "true"
	else:
		return value


def fix_attribs(elem):
	dict_ = {}
	if elem is not None:
		for key in elem.attrib:
			dict_.update({key: attr(elem, key)})
	return dict_


def build_dict(elem):
	'''
	适合处理数据保存在元素的属性中的XML
	<root>
		<sysmon enabled="0" host="0.0.0.0" port="6000" />
	</root>
	'''
	if elem is not None:
		dict_ = {}
		for subelem in elem:
			if subelem.tag in dict_:
				if not isinstance(dict_[subelem.tag], list):
					dict_[subelem.tag] = [dict_[subelem.tag]]
				dict_[subelem.tag].append(build_dict(subelem))
			else:
				dict_.update({subelem.tag: build_dict(subelem)})
			if subelem.text and subelem.text.strip():
				dict_.update({subelem.tag: {"_text": subelem.text}})
		dict_.update(fix_attribs(elem))
		return dict_
	else:
		return fix_attribs(elem)


def build_dict2(elem, encoding=None, isroot=True):
	'''
	适合处理数据作为标签文本保存的XML
	<DeviceType><ID>id1<ID><Name>xxx</Name></DeviceType>
	'''
	d = {}
	if elem is not None:
		if list(elem):
			for subelem in elem:
				if subelem.tag in d:
					if not isinstance(d[subelem.tag], list):
						d[subelem.tag] = [d[subelem.tag]]
					d[subelem.tag].append(build_dict2(subelem, encoding, isroot=False))
				else:
					if list(subelem):
						d.update({subelem.tag: build_dict2(subelem, encoding, isroot=False)})
					else:
						d.update(build_dict2(subelem, encoding, isroot=False))
		else:
			text = elem.text
			if text is not None:
				text = text.strip()
			else:
				text = ""
			if encoding:
				if isinstance(text, unicode):
					text = text.encode(encoding)
			d.update({elem.tag: text})
		if isroot:
			return {elem.tag: d}
	return d
