import sys
import traceback


def tracelog(logfile, traceback_=None):
	import time
	timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
	errlog = open(logfile, "a+")
	errlog.write(timestamp + "\n")
	if traceback_:
		tp, val, tb = traceback_
		traceback.print_exception(tp, val, tb, file=sys.stderr)
		traceback.print_exception(tp, val, tb, file=errlog)
	else:
		traceback.print_exc(file=sys.stderr)
		traceback.print_exc(file=errlog)
#	errlog.write(repr(sys.exc_info()[-1].tb_frame.f_locals))
	errlog.write("\n")
	errlog.close()


def excepthook(tp, val, tb):
	if tb:
		pyfile = tb.tb_frame.f_code.co_filename
		p = pyfile.rfind(".")
		if p:
			logfile = pyfile[:p] + ".log"
		else:
			logfile = pyfile + ".log"
		tracelog(logfile, (tp, val, tb))
	else:
		traceback.print_exception(tp, val, tb)

sys.excepthook = excepthook
