# -*- coding: gbk -*-
import re
import xml.etree.cElementTree as ET

class XmlStr(str):
	def __new__(cls, init_str, encoding="gbk"):
		data = '<?xml version="1.0" encoding="%s"?>%s' % (encoding, init_str)
		return unicode(data, "gbk").encode(encoding)


class XmlElem(object):
	def __init__(self, text="", encoding="gbk", elem=None, int_elems=[]):
		if elem is None:
			self._rootelem = xmlelem_from_text(text, encoding)
		else:
			self._rootelem = elem
		self._int_elems = int_elems

	def __getattr__(self, name):
		if name.startswith("_"):
			return self.__dict__[name]
		elif name in self.__dict__:
			return self.__dict__[name]
		else:
			return self.get(name)

	def __contains__(self, name):
		elem = self._rootelem.find(name)
		return elem != None

	def get(self, name, val=None):
		elem = self._rootelem.find(name)
		if elem != None:
			if elem.text:
				val = elem.text.encode("gbk")
				if callable(self._int_elems):
					be_int = self._int_elems(val)
				else:
					be_int = name in self._int_elems
				if be_int:
					val = int(val)
				else:
					val = droptags(val)
			else:
				val = ""
		return val

	def tostring(self, encoding="gbk"):
		return ET.tostring(self._rootelem, encoding)


def get_xmlhead(text):
	head = ""
	if text.startswith("<?xml"):
		m = re.match("<\?xml (.*?)\?>", text)
		if m:
			head = m.group()
	return head

def get_xmlencoding(text, default):
	'''
	�Զ�ʶ��xml�ı��ı��룬���ʶ�𲻳��ͷ���defaultָ���ı��롣
	'''
	encoding = default
	head = get_xmlhead(text)
	if head:
		m1 = re.search(r"encoding=([\"'])([^\"']+)\1", head)
		if m1:
			encoding = m1.group(2)
	return encoding.lower()

def drop_xmlidentifier(text):
	if text.startswith("<?xml"):
		m = re.match("<\?xml (.*?)\?>", text)
		if m:
			text = m.string[m.end(0):]
	return text

def xmlelem_from_text(text, encoding="gbk"):
	'''
	��xml�ı�����xml����
	�����Զ�ʶ��xml�е�encoding�����Ҳ��ܰ�������<?xml ...?>ͷ������ȷ����
	��xml�в�����encodingʱ��Ĭ��Ϊgbk��
	'''
	head = get_xmlhead(text)
	encoding = get_xmlencoding(head, default=encoding)
	if encoding not in ["utf8", "utf-8"]:
		if encoding == "gb2312":	# �е�xml�ļ���Ȼ��ע��gb2312����
			encoding = "gb18030"	# ��ȴ�����޷�������ַ���Ҫgbk����gb18030����
		text = text[len(head):]
		text = unicode(text, encoding).encode("utf-8")
		head = ""
	if not head:
		head = "<?xml version='1.0' encoding='utf-8'?>"
		xml = "".join((head, text))
	else:
		xml = text
	# ET.XML() �൱��ET.fromstring()��ֻ�ܽ���UTF-8������ı���
	# ע��ET.XML���������'<?xml version="1.0" encoding="gbk" ?><ChannelName>&#x04;</ChannelName>'
	# �ᱨ��SyntaxError: reference to invalid character number: line 1, column 51
	return ET.XML(xml)

def clone(elem):
	'''
	�ο���http://www.velocityreviews.com/forums/t668383-elementtree-and-clone-element-toot.html
	'''
	new_elem = elem.makeelement(elem.tag, elem.attrib)
	new_elem.text = elem.text
	for child in elem:
		new_elem.append(clone(child))
	return new_elem

def get_parent_elem(rootelem, elem):
	"""
	 ���Ԫ�صĸ�Ԫ��
	 �μ�http://stackoverflow.com/questions/2170610/access-elementtree-node-parent-node
	"""
	parent_map = dict((c, p) for p in rootelem.getiterator() for c in p)
	parent_elem = parent_map.get(elem)
	return parent_elem

def droptags(text):
	text = text.replace("&lt;", "<")
	text = text.replace("&gt;", ">")
	text = re.sub("<br\s*?/?>", "\n", text)
	text = re.sub("<.*?>", "", text)
	return text

def pretty_indent(elem, space="\t", level=0):
	'''
	�����������
	ժ��http://effbot.org/zone/element-lib.htm#prettyprint
	'''
	i = "\n" + level * space
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + space
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for child in elem:
			pretty_indent(child, space=space, level=level + 1)
		if not child.tail or not child.tail.strip():
			child.tail = i
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i
