# -*- coding: gbk -*-
import os
import codecs
import __builtin__
from bs4 import UnicodeDammit


def get_fileencoding(filename, default=None, detail=None):
	encoding = default
	skip_bytes = 0
	if os.path.isfile(filename):
		f = __builtin__.open(filename, "rb")
		try:
			s = f.read(2)
			"""
			ANSI：				无格式定义；
			Unicode：			前两个字节为FFFE；
			Unicode big endian：	前两字节为FEFF；
			UTF-8 with BOM：		前三字节为EFBBBF；
			"""
			if s == chr(0xff) + chr(0xfe):
				encoding = "utf_16_le"
				skip_bytes = 2
			elif s == chr(0xfe) + chr(0xff):
				encoding = "utf_16_be"
				skip_bytes = 2
			elif s == chr(0xef) + chr(0xbb):
				encoding = "utf-8-sig"
				skip_bytes = 3
		except:
			pass
		if not encoding:
			# 使用BeautifulSoup的编码识别功能
			f.seek(0)
			line = f.readline()
			dammit = UnicodeDammit(line)
			# 注意，这种方法有时获取到的编码是'windows-1252'（拉丁字符集的一种），因而不可靠。
			encoding = dammit.original_encoding
		f.close()
	if isinstance(detail, dict):
		detail["encoding"] = encoding
		detail["skip_bytes"] = skip_bytes
	return encoding


def open(filename, mode="r", encoding=None, skip_bytes=0):
	detail = {}
	if encoding is None:
		encoding = get_fileencoding(filename, detail=detail)
	if encoding is None:
		encoding = "gb18030"
	if not skip_bytes:
		skip_bytes = detail.get("skip_bytes", skip_bytes)

	# 注意：codecs.open 不管是否指定了mode，总是以二进制模式打开。
	# 因此需要自行处理文本文件中的\r\n -> \n
	f = codecs.open(filename, mode=mode, encoding=encoding)
	f.seek(skip_bytes)	# 跳过指示头
	# 注意：f.read()返回的是unicode
	return f


def readfile(filename, encoding="gbk"):
	with open(filename) as f:
		content = f.read()
		content = content.replace(u"\r\n", u"\n")
		if encoding:
			content = content.encode(encoding)
	return content


if __name__ == "__main__":
	print readfile("1.txt")
