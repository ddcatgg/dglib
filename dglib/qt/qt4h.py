# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QVariant', 2)
sip.setapi('QString', 2)

if getattr(sip, "setdestroyonexit", None):
	sip.setdestroyonexit(False)

from PyQt4 import QtGui, QtCore
