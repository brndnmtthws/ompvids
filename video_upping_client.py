#!/usr/bin/python
#
# This is the video encoding client.  This will check if there are new videos
# available, and if so, it will process it.  If not, then it sits and waits
# until there is something to do.

import socket
import sys

host = 'localhost'
port = 50000
size = 1024
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host,port))
s.settimeout(5)

while True:
	try:
		# read from keyboard
		line = sys.stdin.readline()
		if line == '\n':
			break
		s.send(line)
		data = s.recv(size)
		sys.stdout.write(data)
	except socket.timeout:
		print 'Timed out.'
		break
s.close()
