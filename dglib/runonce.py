# -*- coding: gbk -*-
import sys
import win32api
import win32con
import winerror
import win32event

g_hMutex = None	# ���mutex�����Ǿֲ������������ں�������ʱ�ᱻ�ͷţ��𲻵��������á�

def runonce(mutex_name, register_msg="", exit=False):
	'''
	ʹ�û�������ֻ֤����һ�Σ�����ǰ�ӡ�Global\��Ϊȫ�ֻ����������ڶ��û�������
	'''
	result = False
	global g_hMutex

	if register_msg:
		# ���ֱ��import qt_utils2 �������PyQt��������
		# �������import runonce�ĳ�����py2exe�����ʱ���������
		qt_utils2 = __import__("qt_utils2")
		qt_utils2.UM_SHOW = win32api.RegisterWindowMessage(register_msg)

	g_hMutex = win32event.CreateMutex(None, 0, mutex_name)
	if g_hMutex:
		err = win32api.GetLastError()
		if err == winerror.ERROR_ALREADY_EXISTS:
			if register_msg:
				win32api.PostMessage(win32con.HWND_BROADCAST, qt_utils2.UM_SHOW, 0, 0)
			if exit:
				sys.exit()
		else:
			result = True
	else:
		win32api.MessageBox(0, "����Mutexʧ�ܣ�", "��ʾ", win32con.MB_ICONERROR)
	return result


if __name__ == "__main__":
	runonce("mutex_test", "UM_SHOW_TEST")
	while 1:
		import time
		time.sleep(1)
