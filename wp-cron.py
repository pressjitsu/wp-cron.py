#!/usr/bin/python
# Runs wp-cron.php for every website on the account.

# Configuration
WP_DIR = '/home/username/public_html'
WP_CLI_PATH = '/usr/local/bin/wp'
PHP_PATH = '/usr/bin/php'

import json
import subprocess
import sys, fcntl
import os, pwd
from urlparse import urlparse

# Don't run more than once simultaneously.
fp = open('/tmp/wp-cron.pid', 'w')
try:
	fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
	print 'Another instance of wp-cron.py is already running'
	exit()

# Don't run as root.
username = pwd.getpwuid(os.getuid()).pw_name
if username == 'root':
	print 'Do not run as root'
	exit()

# Things that could be used in wp-config.php
env = {
	'HTTP_HOST': '',
	'REQUEST_URI': '',
}

# Get a list of available sites on the account.
s = subprocess.check_output([WP_CLI_PATH, '--path=%s' % WP_DIR, '--skip-themes', '--skip-plugins', 'eval', '''
	$urls = array();

	if ( ! is_multisite() ) {
		$urls[] = home_url();
	} else {
		foreach ( wp_get_sites() as $blog ) {
			$urls[] = get_home_url( $blog['blog_id'] );
		}
	}

	echo json_encode( $urls );
	exit;
'''], env=env)

urls = json.loads(s)
for url in urls:
	url = urlparse(url)
	if url.scheme not in ['http', 'https']:
		continue

	# Set up env variables for php-cli.
	env = {
		'QUERY_STRING': '',
		'REQUEST_METHOD': 'POST',
		'CONTENT_TYPE': '',
		'CONTENT_LENGTH': '',
		'REQUEST_URI': '/wp-cron.php',
		'REQUEST_SCHEME': 'http',
		'REMOTE_ADDR': '127.0.0.1',
		'SERVER_NAME': url.hostname,
		'HTTP_HOST': url.hostname,
		'HTTP_USER_AGENT': 'wp-cron.py',
		'SERVER_PROTOCOL': 'HTTP/1.1',
	}

	if url.scheme == 'https':
		env['REQUEST_SCHEME'] = 'https'
		env['HTTPS'] = 'on'
		env['SERVER_PORT'] = '443'

	try:
		# Run wp-cron.php via php-cli.
		s = subprocess.check_output([PHP_PATH, '%s/wp-cron.php' % WP_DIR], env=env)
		print 'Running wp-cron.php for %s' % url.hostname
	except subprocess.CalledProcessError:
		print 'Error running wp-cron.php for %s' % url.hostname
		continue
