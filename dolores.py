from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, task
from twisted.protocols.basic import LineReceiver

import random, string
import os, os.path, sys
import threading
import time

# This is Delores the High Inquisitor.

# Dolores is a series of tubes. To prevent clogging, there are separate tubes,
# rather than one big pipe everyone might get stuck in.

# A user can be connected to a tube. This allows the user to receive notifications
# through said tubes.

# The pipe server is not made for actual COMET, believe it or not. There is no
# persistence or anything. It is as simple as possible. Instead, we will try to
# use Orbited to make a nice connection between Dolores and the client.

# I don't know how this will hold up performance-wise, but it is simple enough
# that I think it will work for now.

# API:
# There are two kinds of connections: control and client. The api 
# Creating a connection immediately results in a response with a thread id. Thread
# ids consist of a few main parts: IPADDRESS-THREAD#-SECRET
# Where thread# is a sequential thread number, IPADDRESS is the address of the client,
# and SECRET is a random string of bytes made for the thread.

# Clients connecting should check first for a string starting with "I,", which means they
# successfully connected. They should then read another string with their thread id.

#	CONTROL
#			Attempts to make the thread a controller. This only works if a file
#			named "control-" and the thread id is in the "threads" folder (relative
#			to the Dolores.py file -- messy, I know)
#
#	CONNECT UID PATH 			(controller only)
#			Connects the thread with id UID to the specified path.
#
#	DISCONNECT UID PATH			(controller only)
#			Disconnects the thread with id UID from the specified path.
#
#	UPDATE PATH MESSAGE 		(controller only)
#			Sens a message regarding the path. Please keep the message twitter length.
#
#	CRASH UID					(controller only)
#			Aborts a thread. Could be used for testing whole (un-optimized/cometized) reload.
#


class Comet(LineReceiver):
	def __init__(self):
		self.listening = set()
		self.controls = False
	
	def connectionMade(self):
		self.transport.write("I, Dolores, High Inquisitor, Hogwarts.\r\n")
		
		secret = ""
		for i in range(32):
			secret += random.choice(string.ascii_letters + string.digits)
		
		self.id = str(self.transport.getPeer().host) + "-" + str(self.factory.nextThreadNumber()) + "-" + secret
		
		self.transport.write(self.id + "\r\n")
		self.factory.comets[self.id] = self;
		self.factory.listenerCount += 1
	
	def control(self):
		# if the file exists, do it.
		if os.path.exists(os.path.join(os.path.dirname(__file__), "threads", "control-" + self.id)):
			self.factory.controllerCount += 1
			self.controls = True
			os.remove(os.path.join(os.path.dirname(__file__), "threads", "control-" + self.id))
		else:
			self.controls = False
	
	def connectionLost(self, reason):
		self.factory.listenerCount -= 1
		if self.controls:
			self.factory.controllerCount -= 1
		del self.factory.comets[self.id]
		for listen in self.listening:
			self.factory.deregister(listen, self)
	
	def listen(self, path):
		self.factory.register(path.strip(), self)
		self.listening.add(path.strip())
	
	def ignore(self, path):
		self.factory.deregister(path.strip(), self)
		if path.strip() in self.listening:
				self.listening.remove(path.strip())
		
	def lineReceived(self, data):
		if data.startswith("CONNECT"):
			if not self.controls:
				self.transport.write("NOALLOW\r\n")
				return
			try:
				uid, path = data[7:].strip().split(" ", 1)
				uid = uid.strip()
				path = path.strip().lower()
			
				self.factory.comets[uid].listen(path)
				self.listening.add(data[6:].strip())
				self.transport.write("SUCCESS\r\n")
			except:
				print "Failed a connect attempt."
				self.transport.write("FAIL\r\n")
			
		elif data.startswith("DISCONNECT"):
			if not self.controls:
				self.transport.write("NOALLOW\r\n")
				return
			try:
				uid, path = data[10:].strip().split(" ", 1)
				uid = uid.strip()
				path = path.strip().lower()
				if uid in self.factory.comets:
					self.factory.comets[uid].ignore(path)
					self.transport.write("SUCCESS")
					return
			except:
				pass
			self.transport.write("FAIL")
			
		elif data.startswith("CRASH"):
			if not self.controls:
				self.transport.write("NOALLOW\r\n")
				return
			try:
				uid = data[5:].strip()
				if uid in self.factory.comets:
					self.factory.comets[uid].transport.loseConnection()
				self.transport.write("SUCCESS")
			except:
				self.transport.write("FAIL")
		
		elif data.startswith("EXIT"):
			self.transport.loseConnection()
			
		elif data.startswith("UPDATE"):
			if not self.controls:
				self.transport.write("NOALLOW\r\n")
				return
			try:
				pieces = data[6:].split(";",1)
				path = pieces[0].lower() # make sure the path is in lower case
				message = ""
				if len(pieces) > 1:
					message = pieces[1]
				self.factory.message(path.strip(), message.strip())
				self.transport.write("SUCCESS")
			except:
				self.transport.write("FAIL\r\n")
		
		elif data.startswith("ALL"):
			if not self.controls:
				self.transport.write("NOALLOW\r\n")
				return
			try:
				path = data[3:]
				for i in self.factory.comets:
					self.factory.comets[i].sendMessage(path)
				self.transport.write("SUCCESS")
			except:
				self.transport.write("FAIL")
		
		elif data.startswith("CONTROL"):
			self.control()
			if not self.controls:
				self.transport.write("NOALLOW\r\n")
				return
	
	def sendMessage(self, path, message):
		self.transport.write("UPDATE " + path + ";" + message + "\r\n")

# Factory
class Manager(Factory):
	def __init__(self):
		self.protocol = Comet
		self.comets = {}
		self.lookup = {}
		self.listenerCount = 0
		self.controllerCount = 0
		self.pathCount = 0
		self.observerCount = 0
		self.messageCount = 0
		self.dispatchedCount = 0
		self.listenerID = 0
		
	def startFactory(self):
		pass
	
	def stopFactory(self):
		pass
	
	def register(self, path, comet):
		if path not in self.lookup:
			self.pathCount += 1
			self.lookup[path] = set()
		
		if comet in self.lookup[path]:
			return
		self.lookup[path].add(comet)
		self.observerCount += 1
	
	def deregister(self, path, comet):
		if path not in self.lookup:
			return
		
		if comet not in self.lookup[path]:
			return
		
		self.lookup[path].remove(comet)
		self.observerCount -= 1
		
		if len(self.lookup[path]) == 0:
			self.pathCount -= 1
			del self.lookup[path]
	
	def message(self, path, message):
		if path not in self.lookup:
			return
		
		self.messageCount += 1
		dispatch = 0
		for i in self.lookup[path]:
			dispatch += 1
			i.sendMessage(path, message)
		self.dispatchedCount += dispatch
	
	def nextThreadNumber(self):
		self.listenerID = self.listenerID + 1
		return self.listenerID


def update_status(f):
	sys.stdout.write(
		str(f.listenerCount).ljust(15) +
		str(f.controllerCount).ljust(15) +
		str(f.pathCount).ljust(15) +
		str(f.observerCount).ljust(15) +
		str(f.messageCount).ljust(15) +
		str(f.dispatchedCount) + "\r"
	)
	sys.stdout.flush()
	
def thread_start():
	global dolores_reactor
	factory = Manager()
	
	status_updater = task.LoopingCall(update_status, factory)
	status_updater.start(1.0)
	reactor.listenTCP(8007, factory)
	
	reactor.run(installSignalHandlers=0)
	print "Dolores has been taken by the Centaurs. Clip clop."
	

dolores_thread = None
def start():
	print "Starting Dolores..."
	global dolores_thread
	dolores_thread = threading.Thread(target=thread_start)
	dolores_thread.start()
	print "Dolores has  now been appointed High Inquisitor."
	print("Connections".ljust(15) + "Controllers".ljust(15) + "Paths".ljust(15) + "Observers".ljust(15) + "Messages".ljust(15) + "Dispatched")

def stop_reactor():
	reactor.stop()

def stop():
	reactor.callFromThread(stop_reactor)

if __name__ == "__main__":
    start()
    run = True
    while run:
    	try:
    		time.sleep(5)
    	except KeyboardInterrupt:
    		stop()
    		run = False
    		
