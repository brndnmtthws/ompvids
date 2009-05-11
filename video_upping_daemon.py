#!/usr/bin/python
#
# This thing is pretty simple, it just monitors a specific path for new files
# and then uploads them to amazon's s3 poo.  After a successful upload, it
# removes the file.

path = 'videos'  # default watched path

from pyinotify import ProcessEvent, ThreadedNotifier, WatchManager, EventsCodes

class PExample(ProcessEvent):
	def process_default(self, event):
		"""
		override default processing method
		"""
		print 'PExample::process_default'
		# call base method
		super(PExample, self).process_default(event)

	# The followings events are individually handled and processed

	def process_IN_MODIFY(self, event):
		"""
		process 'IN_MODIFY' events
		"""
		print 'PExample::process_IN_MODIFY'
		super(PExample, self).process_default(event)

	def process_IN_OPEN(self, event):
		"""
		process 'IN_OPEN' events
		"""
		print 'PExample::process_IN_OPEN'
		super(PExample, self).process_default(event)



if __name__ == '__main__':
	import sys

	if sys.argv[1:]:
		path = sys.argv[1]

	# only watch those events
	mask = EventsCodes.IN_MODIFY | EventsCodes.IN_DELETE | \
			EventsCodes.IN_OPEN | EventsCodes.IN_ATTRIB | \
			EventsCodes.IN_CREATE

	# watch manager instance
	wm = WatchManager()
	# notifier instance and init, give an instance of PExample as
	# processing function.
	notifier = ThreadedNotifier(wm, PExample())
	# start notifier's thread
	notifier.start()

	# watch path for events handled by mask.
	wm.add_watch(path, mask)

	print 'start monitoring %s with mask 0x%08x' % (path, mask)

	# keep artificially the main thread alive forever
	while True:
		try:
			import time
			time.sleep(5)
		except KeyboardInterrupt:
			# ...until c^c signal
			print 'stop monitoring...'
			# stop monitoring
			notifier.stop()
			break
		except Exception, err:
			# otherwise keep on looping
			print err

