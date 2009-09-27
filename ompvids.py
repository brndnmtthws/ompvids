#
# Copyright 2009 Brenden Matthews <brenden@diddyinc.com>
#
# Distributed under the terms of the GNU General Public License v3
#
# This is common stuff for the ompvids scripts.
#

import boto
from boto.s3.key import Key
import hashlib
import os
import re
import sys

passkey = os.environ['OMPVIDS_PASSKEY'] # will assplode if not defined in environment

bind_server_to_address = ''
server_port = 50000
socket_size = 4096
max_wait = 10 # seconds
min_wait = 1 # seconds

fn_exp = re.compile('([A-Za-z0-9]+)-(.+)')
key_exp = re.compile('([A-Za-z0-9]+)/(.+)')

def filename_to_key(filename):
	res = fn_exp.match(filename)
	if not res:
		return
	id = res.group(1)
	name = res.group(2)
	key = id + '/' + name
	return key

def key_to_filename(key):
	res = key_exp.match(key)
	if not res:
		return
	id = res.group(1)
	name = res.group(2)
	filename = id + '-' + name
	return filename

def get_bucket(bucket_name):
	conn = boto.connect_s3()
	return conn.create_bucket(bucket_name)


def get_answer(passkey, challenge):
	return hashlib.sha224('%s %li' % (passkey, challenge)).hexdigest()

def unlink(file):
	try:
		os.unlink(file)
	except OSError:
		# no care
		pass

