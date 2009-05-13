#
# This is common stuff for the ompvids scripts.
#

import boto
from boto.s3.key import Key
import sha
import os
import re
import sys

passkey = os.environ['OMPVIDS_PASSKEY'] # will assplode if not defined in environment

bind_server_to_address = ''
server_hostname = 'localhost'
port = 50000
size = 4096
max_wait = 600 # seconds
min_wait = 5 # seconds

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
	return sha.new('%s %li' % (passkey, challenge)).hexdigest()
