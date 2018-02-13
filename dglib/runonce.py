# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import win32api
import win32con
import winerror
import win32event

g_hMutex = None		# 这个mutex不可是局部变量，否则在函数返回时会被释放，起不到互斥作用。


def runonce(mutex_name, register_msg="", exit=False):
	'''
	使用互斥量保证只运行一次，名称前加“Global\”为全局互斥量可用于多用户环境。
	'''
	result = False
	global g_hMutex

	if register_msg:
		# 如果直接import qt_utils2 会引入对PyQt的依赖，
		# 造成其他import runonce的程序在py2exe打包的时候体积增大
		qt_utils2 = __import__('dglib.qt.qt_utils2')
		qt_utils2.UM_SHOW = win32api.RegisterWindowMessage(register_msg)
		runonce.UM_SHOW = qt_utils2.UM_SHOW

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
		win32api.MessageBox(0, '创建Mutex失败！', '提示', win32con.MB_ICONERROR)
	return result


if __name__ == '__main__':
	runonce('mutex_test', 'UM_SHOW_TEST')
	while 1:
		import time
		time.sleep(1)
