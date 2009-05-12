#!/usr/bin/python
#
# This is the video encoding client.  This will check if there are new videos
# available, and if so, it will process it.  If not, then it sits and waits
# until there is something to do.

import socket
import sys
import re
import sha

passkey = ''
if sys.argv[1:]:
	passkey = sys.argv[1]
else:
	print "Please supply the passkey as the first argument"
	sys.exit()

host = 'localhost'
port = 50001
size = 4096
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host,port))
s.settimeout(5)

try:
	# first do auth
	data = s.recv(size)
	challenge = long(re.match('Challenge: (\d+)\n', data).group(1))
	answer = sha.new('%s %li' % (passkey, challenge)).hexdigest()
	response = 'Response: %s\n' % answer
	s.send(response)
	data = s.recv(size)
	print data,
	if data == 'Come inside, friand!\n':
		while True:
			# read from keyboard
			line = sys.stdin.readline()
			if line == '\n':
				break
			s.send(line)
			data = s.recv(size)
			sys.stdout.write(data)
except socket.timeout:
	print 'Timed out.'
s.close()
