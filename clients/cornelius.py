# Cornelius: The Django Thestral protocol implementation.
# That is, the Django client for Dolores.

from django.conf import settings
import socket
import time
import os, os.path

cornelius_connection = None
class CorneliusFault(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)


def _connect(reconnect = False):
	global cornelius_connection
	global settings
	if cornelius_connection and reconnect:
		try:
			cornelius_connection.shutdown()
		except:
			pass
		cornelius_connection = None
	
	if not cornelius_connection:
		cornelius_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		cornelius_connection.connect(settings.DOLORES_SERVER)
		cornelius_connection.settimeout(1) # wait one second for response if needed. Hopefully won't be that long.
		
		buffer = read()
		if len(buffer) < 2:
			raise CorneliusFault("He's Not Back!")
		
		verify_dolores = buffer[0].strip()
		if verify_dolores.strip() != "I, Dolores, High Inquisitor, Hogwarts.":
			raise CorneliusFault("Lord Thingy! Lord Thingy! Dolores, why have you turned into Lord Thingy?")
		
		cornelius_thread_id = buffer[1].strip()
		f = open(os.path.join(settings.DOLORES_PATH, "threads/control-" + cornelius_thread_id), "w")
		f.write("you big dummy.")
		f.close()
		send("CONTROL\n\n", True)
		read()

def read():
	try:
		buffer = cornelius_connection.recv(4096)
		return buffer.split("\n")
	except:
		pass

def send(what, noconnect = False):
	if not noconnect:
		_connect()
	global cornelius_connection
	try:
		cornelius_connection.sendall(what + "\r\n")
	except:
		if not noconnect:
			_connect(True)
		cornelius_connection.sendall(what + "\r\n")
	
	try:
		read() # don't do anythin' with output yet. Just get rid of it... so it doesn't sit in some buffer
	except:
		pass

def update(path, message = ""):
	send("UPDATE " + path + "; " + message)


def connect(uid, path):
	send("CONNECT " + uid + " " + path)
	
def disconnect(uid, path):
	send("DISCONNECT " + uid + " " + path)


def crash(uid):
	send("CRASH " + uid)
	
def log():
	global cornelius_connection
	cornelius_connection.read_very_eager()
# """