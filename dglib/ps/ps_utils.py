# -*- coding: gbk -*-
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
