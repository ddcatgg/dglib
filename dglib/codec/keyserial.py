# -*- coding: utf-8 -*-
import wmi
import string
import hashlib
import pywintypes

SERIALCHRS = "".join([string.digits, string.ascii_uppercase])
MD5CHRS = "0123456789ABCDEF"


def md5_to_serial(md5_s):
	"""
	将md5字符串（32个字符，0-9A-F）转换为序列号字符串（16个字符串，0-9A-Z）
	"""
	chars = []
	for i in range(0, len(md5_s), 2):
		a = md5_s[i]
		b = md5_s[i + 1]
		c = 0 if a > b else 1 if b > a else 2
		j = MD5CHRS.index(a) + MD5CHRS.index(b) + c
		chars.append(SERIALCHRS[j])
		if len(chars) in [4, 9, 14]:
			chars.append("-")
	return "".join(chars)


def get_serial_by_mac():
	"""
	根据多块物理网卡MAC生成序列号
	"""
	pnpd_ids = []
	c = wmi.WMI()
	wql = "SELECT * FROM Win32_NetworkAdapter WHERE (MACAddress IS NOT NULL) AND (NOT (PNPDeviceID LIKE 'ROOT%'))"
	for entry in c.query(wql):
		try:
			prop = entry.wmi_property("PNPDeviceID")
		except pywintypes.com_error:
			prop = None
		if prop and prop.value:
			pnpd_ids.append(prop.value)

	if pnpd_ids:
		pci_ids = filter(lambda s: s.startswith("PCI"), pnpd_ids)
		mac_s = "|".join(pci_ids)
		md5_s = hashlib.md5(mac_s).hexdigest().upper()
		return md5_to_serial(md5_s)


def get_serial_by_hdd():
	"""
	根据多块物理硬盘ID生成序列号
	"""
	hdd_ids = []
	c = wmi.WMI()
	wql = "SELECT * FROM Win32_DiskDrive"
	for entry in c.query(wql):
		# 有的WD硬盘没有序列号，VirtualBox虚拟机里也没有这一项，就使用PNPDeviceID代替。
		# 另外有的刀片服务器有SerialNumber这一栏，但取得的prop.value是None而不是字符串类型。
		try:
			prop = entry.wmi_property("SerialNumber")
		except pywintypes.com_error:
			try:
				prop = entry.wmi_property("PNPDeviceID")
			except pywintypes.com_error:
				prop = None
		if prop and prop.value:
			hdd_ids.append(prop.value)

	if hdd_ids:
		hdd_s = "|".join(hdd_ids)
		md5_s = hashlib.md5(hdd_s).hexdigest().upper()
		return md5_to_serial(md5_s)


def get_serial():
	serial = get_serial_by_hdd()
	if not serial:
		serial = get_serial_by_mac()
	return serial


def get_registerkey(serial, code=""):
	"""
	根据序列号生成注册码
	@param code: 特征码
	"""
	result = ""
	# 验证序列号的合法性
	if len(serial) == 19:
		if all(map(lambda a: a in SERIALCHRS + "-", serial)):	# 验证字符的合法性
			blocks = serial.split("-")
			if len(blocks) == 4 and all(map(lambda s: len(s) == 4, blocks)):	# 验证4个字符一组一共4组
				# 生成注册码
				key = code.join(blocks)
				result = hashlib.sha224(key).hexdigest()
	return result


if __name__ == "__main__":
	serial = get_serial_by_hdd()
	print "get_serial_by_hdd", serial
	print get_registerkey(serial)
