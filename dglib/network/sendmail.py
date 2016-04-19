# -*- coding: utf-8 -*-
import os
import smtplib
import email
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# 设置服务器，用户名、口令以及邮箱的后缀
host = ""
user = ""
pswd = ""
debug = False


def sendmail(receiver, subject, content, **kwargs):
	'''
	receiver: 发给谁，可用分号分隔多个地址。
	subject: 主题
	content: 内容
	sendmail("receiver@163.com", "主题", "内容")
	'''
	# 先搜索用户名中包含的邮箱域名，如果没有再取smtp服务器的域名。
	if "@" in user:
		uid, domain = user.split("@")
	else:
		uid = user
		domain = ".".join(host.split(".")[-2:])
	sender = "%s<%s@%s>" % (user, uid, domain)
	msg = MIMEMultipart()
	if isinstance(subject, unicode):
		subject = subject.encode('utf8')
	msg["Subject"] = email.Header.Header(subject, "utf8")
	msg["From"] = sender
	msg["To"] = receiver
	msg["Date"] = email.utils.formatdate(localtime=True)
	cc = kwargs.get("cc")
	if cc:
		msg["CC"] = cc
	bcc = kwargs.get("bcc")
	if bcc:
		msg["BCC"] = bcc
	if isinstance(content, unicode):
		content = content.encode('utf8')
	txt = email.MIMEText.MIMEText(content, _subtype="plain", _charset="utf8")
	msg.attach(txt)
	# 添加附件
	files = kwargs.get("files")
	if files:
		for file in files:
			add_file(msg, file)
	try:
		timeout = kwargs.get("timeout")
		if timeout is None:
			smtp = smtplib.SMTP()
		else:
			smtp = smtplib.SMTP(timeout=timeout)
		code, resp = smtp.connect(host)
		if debug:
			print code, resp
		code, resp = smtp.login(user, pswd)
		if debug:
			print code, resp
		to_list = [s.strip() for s in receiver.split(";")]
		smtp.sendmail(sender, to_list, msg.as_string())
		smtp.close()
		return ""
	except Exception, e:
		print str(e)
		return str(e)


def add_file(msg, filename):
	#添加二进制附件
	if os.path.isfile(filename):
		ctype, encoding = mimetypes.guess_type(filename)
		if ctype is None or encoding is not None:
			ctype = 'application/octet-stream'
		maintype, subtype = ctype.split('/', 1)
		att1 = MIMEImage((lambda f: (f.read(), f.close()))(open(filename, 'rb'))[0], _subtype=subtype)
		att1.add_header('Content-Disposition', 'attachment', filename=filename)
		msg.attach(att1)
		return True
	else:
		return False


if __name__ == '__main__':
#	host = "smtp.21cn.com"
#	user = "autoserver2013"
#	pswd = "autoserver"
	host = "smtp.163.com"
	user = "autoserver"
	pswd = "autoserver2013"
	debug = True
	errmsg = sendmail("autoserver@163.com; 990080@qq.com", u"测试标题123", u"测试内容1234\n测试内容5678", files=("r:\\清数据.rar",))
	if not errmsg:
		print "发送成功"
	else:
		print "发送失败", errmsg
