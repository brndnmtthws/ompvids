#!/usr/bin/python
#
# Copyright 2009 Brenden Matthews <brenden@diddyinc.com>
#
# Distributed under the terms of the GNU General Public License v3
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
server_hostname = os.environ['SERVER_HOSTNAME']

tmp_path = '/tmp/'

def do_out(key, bucket, suffix, type):
	out_k = Key(bucket)
	out_k.key = key + suffix
	headers = dict()
	headers["Content-Type"] =  type
	headers["Expires"] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 315360000))
	headers["Cache-Control"] = "min-fresh=31536000"
	out_k.set_contents_from_filename(tmp_path + key_to_filename(key) + suffix, headers)
	out_k.set_acl('public-read')
	size = out_k.size
	unlink(tmp_path + key_to_filename(key) + suffix)
	return size

def process_new_videor(key):
	print 'doing it omp with', key
	bucket = get_bucket(in_bucket_name)
	in_k = Key(bucket)
	in_k.key = key
	print key
	in_k.get_contents_to_filename(tmp_path + key_to_filename(key))
	if os.system(sys.path[0] + '/encode.rb "%s" "%s"' % (tmp_path + key_to_filename(key), tmp_path)):
		# error!
		unlink(tmp_path + key_to_filename(key) + '.ogg')
		unlink(tmp_path + key_to_filename(key) + '.gif')
		unlink(tmp_path + key_to_filename(key) + '-still.gif')
		unlink(tmp_path + key_to_filename(key))
		in_k.delete()
		return False
	else:
		# success!
		bucket = get_bucket(out_bucket_name)
		size = do_out(key, bucket, '.ogg', 'application/ogg')
		do_out(key, bucket, '.gif', 'image/gif')
		do_out(key, bucket, '-still.gif', 'image/gif')
		unlink(tmp_path + key_to_filename(key))
		in_k.delete()
		return size

def connect():
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.settimeout(min_wait)
	s.connect((server_hostname,server_port))
	# first do auth
	data = s.recv(socket_size)
	res = re.match('Challenge: (\d+)\n', data)
	if not res:
		return False
	word = res.group(1)
	challenge = long(word)
	answer = get_answer(passkey, challenge)
	response = 'Response: %s\n' % answer
	s.send(response)
	data = s.recv(socket_size)
	if data == 'Come inside, friand!\n':
		return s

def check_server_for_videor():
	try:
		s = connect()
		if not s:
			return
		s.send("what is\n")
		exp = re.compile('something: (.*)\n')
		data = ''
		# nothing, lettuce just wait a while
		res = exp.match(data)
		while not res:
			s.settimeout(max_wait * 2)
			data = s.recv(socket_size)
			s.settimeout(min_wait)
			res = exp.match(data)
		s.close()
		return res.group(1)
	except socket.timeout:
		pass

def report_failure(key):
	success = False
	while not success:
		try:
			# try until succeed
			s = connect()
			if not s:
				time.sleep(max_wait)
				continue
			s.send("failure with %s\n" % key)
			data = s.recv(socket_size)
			if data == "o, ty\n":
				success = True
			s.close()
		except socket.timeout:
			time.sleep(max_wait)
			pass

def report_success(key, size):
	success = False
	while not success:
		try:
			# try until succeed
			s = connect()
			if not s:
				time.sleep(max_wait)
				continue
			s.send("success with %i %s\n" % (size, key))
			data = s.recv(socket_size)
			if data == "joy, ty\n":
				success = True
			s.close()
		except socket.timeout:
			time.sleep(max_wait)
			pass


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
			time.sleep(min_wait)
			key = check_server_for_videor()
			if key:
				size = process_new_videor(key)
				if not size:
					report_failure(key)
				else:
					report_success(key, size)
		except KeyboardInterrupt:
			print 'shutting down...'
			break
		except Exception, err:
			# otherwise keep on looping
			print err

