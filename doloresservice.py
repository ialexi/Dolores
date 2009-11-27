# This is how you make dolores into a Win32 service.
import dolores
import time

# Service Utilities
import win32serviceutil
import win32service
import win32event

class WindowsService(win32serviceutil.ServiceFramework):
	_svc_name_ = "Dolores"
	_svc_display_name_ = "Dolores Server"
	
	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
	
	def SvcStop(self):
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		win32event.SetEvent(self.hWaitStop)
	
	def SvcDoRun(self):
		import servicemanager
		dolores.start()
		while True:
			retval = win32event.WaitForSingleObject(self.hWaitStop, 10)
			if not retval == win32event.WAIT_TIMEOUT:
				dolores.stop()
				break
				time.sleep(5.0)
	

if __name__=='__main__':
	win32serviceutil.HandleCommandLine(WindowsService) 