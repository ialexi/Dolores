# This is the load tester for Dolores.
# It isn't great, and will be replaced with something nicer.

from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet import reactor, task
from twisted.protocols.basic import LineReceiver


import os, os.path, sys
from time import sleep
import threading
import random

class CouldNotConnect:
	pass

class ThestralClient(LineReceiver):
	def __init__(self, control):
		# Incoming buffer
		self.is_connected = False
		self.handler = self.receive_connect
		self.control = control
		self.send_queue = []
	
	
	# HIGHER-LEVEL
	def got_connected(self):
		if not self.control.strip() == "":
			f = open(os.path.join(self.control, "threads/control-" + self.uid), "w")
			f.close()
			self.send_command("CONTROL")
		
	# SENDER (implemented in case we want to change it)
	def send_command(self, data):
		if not self.is_connected:
			self.send_queue.append(data)
			return
		sendthis = data.replace("%s", self.uid).encode("ascii")
		print "SEND: " + sendthis
		self.transport.write(sendthis + "\r\n")
	
	def send_update(self, path, data):
		self.send_command("UPDATE " + path + "; " + data)
	
	def send_connect(self, uid, path):
		self.send_command("CONNECT " + uid + " " + path)
	
	def send_disconnect(self, uid, path):
		self.send_command("DISCONNECT " + uid + " " + path)
	
	def send_crash(self, uid):
		self.send_command("CRASH " + uid)
		
	# LOW-LEVEL RECEIVERS
	def receive_connect(self, buffer):
		if not buffer.startswith("I, Dolores"):
			raise CouldNotConnect()
		self.handler = self.receive_uid
	
	def receive_uid(self, buffer):
		self.uid = buffer.strip()
		self.handler = self.receive_command
		self.is_connected = True
		
		self.got_connected()
		for s in self.send_queue:
			self.send_command(s)
	
	
	def receive_command(self, buffer):
		global received_count
		received_count += 1
		
	def lineReceived(self, buffer):
		self.handler(buffer)
	

class ThestralFactory(ReconnectingClientFactory):
	def __init__(self, control=None):
		self.control = control
	def startedConnecting(self, connector):
		global active_count
		self.resetDelay()
		active_count += 1
		
	def buildProtocol(self, addr):
		self.protocol = ThestralClient(control=self.control)
		return self.protocol
		
	def clientConnectionLost(self, connector, reason):
		global active_count
		active_count -= 1
		self.resetDelay() # Don't actually want a long wait
		print 'Lost connection.  Reason:', reason
		ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
	
	def clientConnectionFailed(self, connector, reason):
		global active_count
		active_count -= 1
		self.resetDelay()
		print 'Connection failed. Reason:', reason
		ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
	

class Thestral:
	def __init__(self, host="localhost", port=8007, control=None):
		self.host = host
		self.port = port
		self.control = control
		self.factory = ThestralFactory(self.control)
		
		reactor.connectTCP(self.host, self.port, self.factory)
	
	def econnect(self, uid, path):
		reactor.callFromThread(e_connect, self, uid, path)

	def edisconnect(self, uid, path):
		reactor.callFromThread(e_disconnect, self, uid, path)

	def eupdate(self, path, message):
		reactor.callFromThread(e_update, self, path, message)
	
	def connect(self, uid, path):
		self.factory.protocol.send_connect(uid, path)
	
	def disconnect(self, uid, path):
		self.factory.protocol.send_disconnect(uid, path)
	
	def update(self, path, message):
		self.factory.protocol.send_update(path, message)

def e_connect(obj, uid, path):
	obj.connect(uid, path)

def e_update(obj, path, message):
	obj.update(path, message)

def e_disconnect(obj, uid, path):
	obj.disconnect(obj, uid, path)

thestrals = []
active_count = 0
thestral_count = 100
received_count = 0
update_count = 0

def prepare_test():
	for i in range(0, thestral_count):
		t = Thestral("localhost", 8007, control="threads")
		thestrals.append(t)
		for i in range(0, 100):
			path = str(i)
			t.connect("%s", path)


def start():
	try:
		print "Starting reactor."
		reactor.run(installSignalHandlers=0)
	except:
		pass
	print "Closed."

def stop_reactor():
	reactor.stop()
def stop():
	reactor.callFromThread(stop_reactor)

def send_updates():
	global update_count, received_count
	i = 0
	for t in thestrals:
		t.update(str(i), "{update:true}")
		i += 1
	update_count += i
	sys.stdout.write(
		"Sent: " + str(update_count) + 
		"; received: " + str(received_count) +
		"; active: " + str(active_count) + "                \r"
	)
	sys.stdout.flush()
	


def threaded_start():
	thread = threading.Thread(target=start)
	thread.start()

def main_loop():
	try:
		while True:
			sleep(1)
			reactor.callFromThread(send_updates)
		
	except KeyboardInterrupt:
		print "Stopping..."
		stop()

if __name__ == "__main__":
	threaded_start()
	main_loop()