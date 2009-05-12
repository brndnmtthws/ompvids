#!/usr/bin/python
#
# This thing is pretty simple, it monitors a specific path for new files and
# then uploads them to amazon's s3 poo.  After a successful upload, it removes
# the file(s) and notifies the remote encoders that we have something for them.

path = ''

import os
import re
import time
import sys
import select
import socket
import random
import sha
from Queue import Queue
from threading import Thread
from pyinotify import ProcessEvent, ThreadedNotifier, WatchManager, EventsCodes

bucket_name = os.environ['AWS_BUCKET'] # will assplode if not defined in environment
passkey = os.environ['OMPVIDS_PASSKEY'] # will assplode if not defined in environment
video_queue = Queue()

class Server:
	def __init__(self):
		self.host = ''
		self.port = 50001
		self.backlog = 5
		self.size = 4096
		self.server = None
		self.threads = []
		self.open_socket()

	def had_clients(self):
		if len(self.threads) > 0:
			return True
		return False

	def clients(self):
		return len(self.threads)

	def open_socket(self):
		try:
			self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.server.bind((self.host,self.port))
			self.server.listen(5)
		except socket.error, (value,message):
			if self.server:
				self.server.close()
			print "Could not open socket: " + message
			sys.exit(1)

	def run(self):
		input = [self.server,sys.stdin]
		inputready,outputready,exceptready = select.select(input,[],[])

		for s in inputready:
			if s == self.server:
				# handle the server socket
				c = Client(self.server.accept())
				c.start()
				self.threads.append(c)

			elif s == sys.stdin:
				# handle standard input
				junk = sys.stdin.readline()

	def __del__(self):
		# close all threads
		self.server.close()
		for c in self.threads:
			c.join()

class Client(Thread):
	def __init__(self,(client,address)):
		Thread.__init__(self)
		self.client = client
		self.client.settimeout(5) # really don't need to waste time here, get in and get out asap
		self.address = address
		self.size = 4096

	def run(self):
		try:
			# first do auth
			challenge = random.getrandbits(64)
			self.client.send('Challenge: %li\n' % challenge)
			# calculate the correct answer
			answer = sha.new('%s %li' % (passkey, challenge)).hexdigest()
			response = 'Response: %s\n' % answer
			data = self.client.recv(self.size)
			if response != data:
				response = 'Bad key :(\n'
				self.client.send(response)
				print response,
			else:
				response = 'Come inside, friand!\n'
				self.client.send(response)
				print response,
				while True:
					data = self.client.recv(self.size)
					if data:
						self.client.send(data)
						print data,
					else:
						break
		except socket.timeout:
			pass
		self.client.close()


class UpThread(Thread):
	def __init__ (self, file):
		Thread.__init__(self)
		self.file = file
		self.exp = re.compile('-notify-([A-Za-z0-9]+)-(.+)')
	def run(self):
		try:
			import boto
			from boto.s3.key import Key
			# first determine the file name of the actual file
			res = self.exp.match(self.file)
			if not res:
				return
			id = res.group(1)
			name = res.group(2)
			key = id + '/' + name
			file = id + '-' + name
			print "Uploading '%s' as key '%s'" % (file, key)
			conn = boto.connect_s3()
			bucket = conn.create_bucket(bucket_name)
			k = Key(bucket)
			k.key = key
			k.set_contents_from_filename(path + file)
			# if we reach here, everything succeeded and we need to queue this omp
			print "Done uploading '%s', queueing up" % key
			video_queue.put(key)
		except IndexError:
			pass

class PThinger(ProcessEvent):
	exp = re.compile('-notify-.*')
	def process_IN_CREATE(self, event):
		"""
		process 'IN_CREATE' events
		"""
		if self.exp.match(event.name):
			UpThread(event.name).start()

if __name__ == '__main__':
	if sys.argv[1:]:
		path = sys.argv[1]
		if path[len(path) - 1] != '/':
			path = path + '/'
		if not os.path.exists(path):
			print "Path '%s' does not exist" % path
	else:
		print "Please supply the path to videos dir as the first argument"
		sys.exit()

	mask = EventsCodes.IN_CREATE

	# watch manager instance
	wm = WatchManager()
	# notifier instance and init, give an instance of Pthinger as
	# processing function.
	notifier = ThreadedNotifier(wm, PThinger())
	# start notifier's thread
	notifier.start()

	# watch path for events handled by mask.
	wm.add_watch(path, mask)

	print 'start monitoring %s with mask 0x%08x' % (path, mask)

	print 'starting server'

	server = Server()

	# keep artificially the main thread alive forever
	while True:
		try:
			import time
			server.run()
		except KeyboardInterrupt:
			# ...until c^c signal
			print 'shutting down...'
			if server.had_clients():
				print '%i clients were connected' % server.clients()
			# stop monitoring
			notifier.stop()
			break
		except Exception, err:
			# otherwise keep on looping
			print err

