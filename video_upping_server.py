#!/usr/bin/python
#
# This thing is pretty simple, it just monitors a specific path for new files
# and then uploads them to amazon's s3 poo.  After a successful upload, it
# removes the file(s).

path = 'videos'  # default watched path

import os
import re
import time
import sys
from threading import Thread
from pyinotify import ProcessEvent, ThreadedNotifier, WatchManager, EventsCodes

bucket = 'bucket-name'

class UpThread(Thread):
	import boto
	from boto.s3.key import Key
	def __init__ (self, file):
		Thread.__init__(self)
		self.file = file
		self.exp = re.compile('-notify-([A-Za-z0-9]+)-(.+)')
	def run(self):
		print "runnin'", self.file
		try:
			# first determine the file name of the actual file
			res = self.exp.match(self.file)
			if not res:
				print 'returnin'
				return
			id = res.group(1)
			name = res.group(2)
			key = id + '/' + name
			file = id + '-' + name
			print key, file
#			conn = boto.connect_s3()
		except IndexError:
			print 'excepted'
			pass



class PThinger(ProcessEvent):
	exp = re.compile('-notify-.*')
	def process_IN_CREATE(self, event):
		"""
		process 'IN_CREATE' events
		"""
		if self.exp.match(event.name):
			print 'found poo:', event.name
			UpThread(event.name).start()

if __name__ == '__main__':
	import sys

	if sys.argv[1:]:
		path = sys.argv[1]

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

	# keep artificially the main thread alive forever
	while True:
		try:
			import time
			time.sleep(1)
		except KeyboardInterrupt:
			# ...until c^c signal
			print 'stop monitoring...'
			# stop monitoring
			notifier.stop()
			break
		except Exception, err:
			# otherwise keep on looping
			print err

