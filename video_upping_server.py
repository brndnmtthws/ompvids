#!/usr/bin/python
#
# Copyright 2009 Brenden Matthews <brenden@diddyinc.com>
#
# Distributed under the terms of the GNU General Public License v3
#
# This thing is pretty simple, it monitors a specific path for new files and
# then uploads them to amazon's s3 poo.  After a successful upload, it removes
# the file(s) and notifies the remote encoders that we have something for them.

path = ''

import select
import socket
import random
import rfc822
import time
from Queue import Queue, Empty
from threading import Thread, Condition
from pyinotify import ProcessEvent, ThreadedNotifier, WatchManager, EventsCodes
from ompvids import *

in_bucket_name = os.environ['AWS_IN_BUCKET'] # will assplode if not defined in environment
omploader_videor_script = os.environ['PATH_TO_VIDEOR_SCRIPT'] # will assplode if not defined in environment

video_queue = Queue()
age_limit = 60*60*48 # 48 hours, in seconds

def qsort(keys):
	if len(keys) <= 1: return keys
	return qsort( [ lt for lt in keys[1:] if lt.last_modified < keys[0].last_modified ] ) + [ keys[0] ]  +  qsort( [ ge for ge in keys[1:] if ge.last_modified >= keys[0].last_modified ] )

def check_queue():
	bucket = get_bucket(in_bucket_name)
	keys = bucket.get_all_keys()
	keys = qsort(keys)
	for key in keys:
		lm = time.mktime(time.strptime(key.last_modified, '%Y-%m-%dT%H:%M:%S.000Z'))
		# add anything older than 48 hours back in to the queue
		if lm - time.timezone < time.time() - age_limit:
			video_queue.put(key.key)


class Server:
	def __init__(self):
		self.host = bind_server_to_address
		self.port = server_port
		self.backlog = 5
		self.size = socket_size
		self.server = None
		self.threads = []
		self.open_socket()
		self.last_queue_check = 0

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
		queue_wait = 3600
		input = [self.server,sys.stdin]
		inputready,outputready,exceptready = select.select(input,[],[], queue_wait)

		for s in inputready:
			if s == self.server:
				# handle the server socket
				c = Client(self.server.accept())
				c.start()
				self.threads.append(c)

			elif s == sys.stdin:
				# handle standard input
				junk = sys.stdin.readline()
		if self.last_queue_check < time.time() - queue_wait:
			check_queue()
			check_notify_path()
			self.last_queue_check = time.time()

	def __del__(self):
		# close all threads
		self.server.close()
		for c in self.threads:
			c.join()

def report_success(id, size):
	os.system("%s -c %i %s" % (omploader_videor_script, size, id))

def report_failure(id):
	os.system("%s -d %s" % (omploader_videor_script, id))

class Client(Thread):
	class Fail(Exception):
		def __init__(self, value):
			self.value = value
		def __str__(self):
			return repr(self.value)

	def __init__(self,(client,address)):
		Thread.__init__(self)
		self.client = client
		self.client.settimeout(min_wait) # really don't need to waste time here, get in and get out asap
		self.address = address
		self.size = socket_size

	def check_response(self, data):
		if data == "what is\n":
			run = True
			while run:
				try:
					run = False
					key = video_queue.get(True, max_wait)
					if not key or len(key) < 1:
						raise Client.Fail('failed 2 get')
					self.client.send("something: %s\n" % key)
				except (Client.Fail, Empty):
					self.client.send("nothing :(\n")
					run = True
				except socket.error:
					if key:
						video_queue.put(key)
		elif len(data) > 0:
			res1 = re.match('failure with ([A-Za-z0-9]+)/.+\n', data)
			res2 = re.match('success with (\d+) ([A-Za-z0-9]+)/.+\n', data)
			if res1:
				# fail :(
				id = res1.group(1)
				report_failure(id)
				self.client.send("o, ty\n")
			elif res2:
				# have succeed!
				size = int(res2.group(1))
				id = res2.group(2)
				report_success(id, size)
				self.client.send("joy, ty\n")

	def run(self):
		try:
			# first do auth
			challenge = random.getrandbits(64)
			self.client.send('Challenge: %li\n' % challenge)
			# calculate the correct answer
			answer = get_answer(passkey, challenge)
			response = 'Response: %s\n' % answer
			data = self.client.recv(self.size)
			if response != data:
				response = 'Bad key :(\n'
				self.client.send(response)
				print response,
			else:
				response = 'Come inside, friand!\n'
				self.client.send(response)
				data = self.client.recv(self.size)
				resp = self.check_response(data)
		except socket.timeout:
			pass
		print 'bye'
		self.client.close()


class UpThread(Thread):
	def __init__ (self, file):
		Thread.__init__(self)
		self.file = file
		self.exp = re.compile('-notify-([A-Za-z0-9]+-.+)')
	def run(self):
		try:
			# first determine the file name of the actual file
			res = self.exp.match(self.file)
			if not res:
				return
			filename = res.group(1)
			key = filename_to_key(filename)
			print "Uploading '%s' as key '%s'" % (filename, key)
			bucket = get_bucket(in_bucket_name)
			k = Key(bucket)
			k.key = key
			k.set_contents_from_filename(path + filename)
			# if we reach here, everything succeeded and we need to queue this omp
			print "Done uploading '%s', queueing up" % key
			video_queue.put(key)
			unlink(path + self.file)
			unlink(path + filename)
		except IndexError:
			pass

notify_exp = re.compile('-notify-.*')

def check_notify_path():
	files = os.listdir(path)
	for file in files:
		if notify_exp.match(file):
			if os.stat(path + file).st_mtime < time.time() - age_limit:
				UpThread(file).start()

class PThinger(ProcessEvent):
	def process_IN_CREATE(self, event):
		"""
		process 'IN_CREATE' events
		"""
		if notify_exp.match(event.name):
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
		sys.exit(1)

	print 'checking for files to be uploaded...'
	check_notify_path()
	print 'initializing queue from S3'

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

