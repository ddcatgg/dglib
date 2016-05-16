# -*- coding: utf-8 -*-
import win32api
import win32con
import win32event
import ctypes

ProcessBasicInformation = 0
STATUS_SUCCESS = 0


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
		_fields_ = [
			("Reserved1", ctypes.c_void_p),
			("PebBaseAddress", ctypes.c_void_p),
			("Reserved2", ctypes.c_void_p * 2),
			("UniqueProcessId", ctypes.c_void_p), 	# ULONG_PTR
			("Reserved3", ctypes.c_void_p)
		]


def get_ppid():
	# NtQueryInformationProcess的用法参考自：
	# http://stackoverflow.com/questions/6587036/alternative-to-psutil-processpid-name
	ntdll = ctypes.windll.LoadLibrary('ntdll.dll')
	if not ntdll:
		return 0

	try:
		pid = win32api.GetCurrentProcessId()
		if not pid:
			return 0

		hproc = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
		if not hproc:
			return 0

		buflen = ctypes.sizeof(PROCESS_BASIC_INFORMATION)
		buf = ctypes.c_char_p('\0' * buflen)
		ret = ntdll.NtQueryInformationProcess(int(hproc), ProcessBasicInformation, buf, buflen, None)
		if ret != STATUS_SUCCESS:
			return 0

		pbuf = ctypes.cast(buf, ctypes.POINTER(PROCESS_BASIC_INFORMATION))
		ppid = pbuf[0].Reserved3
		return ppid

	finally:
		win32api.FreeLibrary(ntdll._handle)


def die_with_parent():
	ppid = get_ppid()
	if not ppid:
		return

	try:
		hpproc = win32api.OpenProcess(win32con.SYNCHRONIZE, False, ppid)
		if not hpproc:
			return

		# waiting parent process
		win32event.WaitForSingleObject(hpproc, win32event.INFINITE)
		# kill myself
		win32api.TerminateProcess(win32api.GetCurrentProcess(), 0)

	finally:
		if hpproc:
			win32api.CloseHandle(hpproc)


def die_with_parent_unreliable():
	'''
	这种方法经测试不可靠，父进程已经退出了有时还在等。
	'''
	import time
	import psutil
	curr_process = psutil.Process()
	parent_process = curr_process.parent()
	if parent_process:
		while True:
			if not parent_process.is_running():
				curr_process.terminate()
				break
			time.sleep(1)


def start_die_with_parent_thread(daemon=True, func=die_with_parent):
	import threading
	_thread_check_parent_alive = threading.Thread(target=func)
	_thread_check_parent_alive.setDaemon(daemon)
	_thread_check_parent_alive.start()
	return _thread_check_parent_alive


def set_subprocess_create_new_console(is_set=True):
	def _my_create_process(*args):
		'''
		通过BrowserDebugStream重定向了spynner的日志输出，但是
		QNetworkReplyImplPrivate::error: Internal problem, this method must only be called once.
		是PyQt直接输出到stderr的，无法消除。
		解决方法是通过multiprocessing模块建立一个独立进程来执行spynner的代码，不幸的是multiprocessing创建
		的进程默认是继承父进程的标准输入输出句柄的，而且是写死的没法改。
		因此需要用这个MyCreateProcess替换掉_subprocess.CreateProcess，	在MyCreateProcess内部设置了
		subprocess.CREATE_NEW_CONSOLE参数。
		'''
		import subprocess
		args = list(args)
		# new console
		args[5] = subprocess.CREATE_NEW_CONSOLE
		# hidden
		import win32process
		import win32con
		startupinfo = subprocess.STARTUPINFO()
		startupinfo.dwFlags |= win32process.STARTF_USESHOWWINDOW
		startupinfo.wShowWindow = win32con.SW_HIDE
		args[-1] = startupinfo
		return _origin_CreateProcess(*args)

	import _subprocess
	if is_set:	# set
		# 防止无限递归
		if getattr(_subprocess, '_origin_CreateProcess', None) is None:
			setattr(_subprocess, '_origin_CreateProcess', _subprocess.CreateProcess)
			_origin_CreateProcess = _subprocess.CreateProcess
			_subprocess.CreateProcess = _my_create_process
	else:		# restore
		_origin_CreateProcess = getattr(_subprocess, '_origin_CreateProcess', None)
		if _origin_CreateProcess is not None:
			_subprocess.CreateProcess = _origin_CreateProcess
			delattr(_subprocess, '_origin_CreateProcess')


def test_create_process_create_new_console():
	import subprocess
	import win32process
	import win32con
	startupinfo = subprocess.STARTUPINFO()
	startupinfo.dwFlags |= win32process.STARTF_USESHOWWINDOW
	startupinfo.wShowWindow = win32con.SW_HIDE
	p = subprocess.Popen("taobao_change_amount.exe /getinfo",
						 creationflags=subprocess.CREATE_NEW_CONSOLE,
						 startupinfo=startupinfo)
	p.wait()
