# -*- coding: gbk -*-
import os
import smtplib
import email
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# ���÷��������û����������Լ�����ĺ�׺
host = ""
user = ""
pswd = ""
debug = False

def sendmail(receiver, subject, content, **kwargs):
	'''
	receiver: ����˭�����÷ֺŷָ������ַ��
	subject: ����
	content: ����
	sendmail("receiver@163.com", "����", "����")
	'''
	# �������û����а������������������û����ȡsmtp��������������
	if "@" in user:
		uid, domain = user.split("@")
	else:
		uid = user
		domain = ".".join(host.split(".")[-2:])
	sender = "%s<%s@%s>" % (user, uid, domain)
	msg = MIMEMultipart()
	msg["Subject"] = email.Header.Header(uni(subject).encode("utf8"), "utf8")
	msg["From"] = sender
	msg["To"] = receiver
	msg["Date"] = email.utils.formatdate(localtime=True)
	cc = kwargs.get("cc")
	if cc:
		msg["CC"] = cc
	bcc = kwargs.get("bcc")
	if bcc:
		msg["BCC"] = bcc
	txt = email.MIMEText.MIMEText(uni(content).encode("utf8"), _subtype="plain", _charset="utf8")
	msg.attach(txt)
	# ��Ӹ���
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
	#��Ӷ����Ƹ���
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

def uni(s, encoding="gbk"):
	if isinstance(s, str):
		return unicode(s, encoding)
	else:
		return unicode(s)

if __name__ == '__main__':
#	host = "smtp.21cn.com"
#	user = "autoserver2013"
#	pswd = "autoserver"
	host = "smtp.163.com"
	user = "autoserver"
	pswd = "autoserver2013"
	debug = True
	errmsg = sendmail("autoserver@163.com; 990080@qq.com", "���Ա���123", "��������1234\n��������5678", files=("r:\\������.rar",))
	if not errmsg:
		print "���ͳɹ�"
	else:
		print "����ʧ��", errmsg
