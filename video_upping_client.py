#!/usr/bin/python
#
# This is the video encoding client.  This will check if there are new videos
# available, and if so, it will process it.  If not, then it sits and waits
# until there is something to do.

import socket
from ompvids import *
import time

passkey = ''
in_bucket_name = os.environ['AWS_IN_BUCKET'] # will assplode if not defined in environment
out_bucket_name = os.environ['AWS_OUT_BUCKET']

tmp_path = '/tmp/'

def process_new_videor(key):
	print 'doing it omp with', key
	bucket = get_bucket(in_bucket_name)
	in_k = Key(bucket)
	in_k.key = key
	print key
	in_k.get_contents_to_filename(tmp_path + key_to_filename(key))
	if os.system('./encode.rb "%s"' % (tmp_path + key_to_filename(key))):
		# error!
		print 'ono, error!'
	else:
		# success!
		bucket = get_bucket(out_bucket_name)
		out_k = Key(bucket)
		out_k.key = key + '.ogg'
		out_k.set_contents_from_filename(tmp_path + key_to_filename(key) + '.ogg')
		out_k.set_acl('public-read')
		in_k.delete()

def check_server_for_videor():
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((server_hostname,port))
		s.settimeout(min_wait)
		# first do auth
		data = s.recv(size)
		challenge = long(re.match('Challenge: (\d+)\n', data).group(1))
		answer = get_answer(passkey, challenge)
		response = 'Response: %s\n' % answer
		s.send(response)
		data = s.recv(size)
		print data,
		if data == 'Come inside, friand!\n':
			s.send("what is\n")
			exp = re.compile('something: (.*)\n')
			# nothing, lettuce just wait a while
			res = exp.match(data)
			while not res:
				s.settimeout(max_wait)
				data = s.recv(size)
				s.settimeout(min_wait)
				res = exp.match(data)
			return res.group(1)
	except socket.timeout:
		pass
	s.close()


if __name__ == '__main__':
	if sys.argv[1:]:
		passkey = sys.argv[1]
	else:
		print "Please supply the passkey as the first argument"
		sys.exit()
	if sys.argv[2:]:
		tmp_path = sys.argv[2]
		if tmp_path[len(tmp_path) - 1] != '/':
			tmp_path = tmp_path + '/'
		if not os.path.exists(tmp_path):
			print "Path '%s' does not exist" % tmp_path
	while True:
		try:
			time.sleep(5)
			key = check_server_for_videor()
			if key:
				process_new_videor(key)
		except KeyboardInterrupt:
			print 'shutting down...'
			break
		except Exception, err:
			# otherwise keep on looping
			print err

