#!/usr/bin/python
import urllib2
import json
import gzip, zlib
import os, sys
from base64 import b64encode as base64_encode
from datetime import datetime
from StringIO import StringIO

API_URL = 'https://api.github.com/users/LineageOS/repos?per_page=200&page=%d'
OUTPUT = "default.xml"

MIN_API_CALLS = 1500

API_AUTH = None
if os.path.exists("github-auth.txt"):
	API_AUTH = open("github-auth.txt", "r").read()

def get_url (url):
	request = urllib2.Request(url)
	request.add_header('Accept-Encoding', 'gzip')
	if API_AUTH is not None:
		request.add_header('Authorization', 'Basic %s' % base64_encode(API_AUTH))

	response = urllib2.urlopen(request)
	encoding = str(response.info().get('Content-Encoding')).lower()
	data = response.read()

	if encoding == 'gzip':
		buf = StringIO(data)
		data = gzip.GzipFile(fileobj=buf).read()
	elif encoding =='deflate':
		data = zlib.decompress(data)
	return data


if __name__ == '__main__':
	if API_AUTH is None:
		print "No GitHub auth configured. This is required."
		print "Enter your username and password in github-auth.txt with the format username:password"
		sys.exit()


	if os.path.exists("repos.txt") and os.stat("repos.txt").st_size is not 0:
		REFRESH = False
		REPLY = raw_input("Do you want to download new repo data? [N/y] ").strip().lower()
		if REPLY == "y":
			REFRESH = True
		else:
			print "Not refreshing repo data."
	else:
		REFRESH = True

	if REFRESH:
		res = json.loads(get_url("https://api.github.com/rate_limit"))
		core = res['resources']['core']
		if core['remaining'] < MIN_API_CALLS:
			print "Not enough API calls remaining (%d required)." % MIN_API_CALLS
			print "Available: %d. Reset time: %s" % (core['remaining'], datetime.utcfromtimestamp(core['reset']).strftime("%H:%M:%S"))
			sys.exit()

	print "Output: %s" % OUTPUT

	if os.path.exists(OUTPUT):
		if os.stat(OUTPUT).st_size is not 0:
			REPLY = raw_input("%s already exists. Do you want to overwrite? [Y/n] " % OUTPUT).strip().lower()
			if not REPLY or REPLY[0] == "y":
				print
				pass
			else:
				print "Not overwriting %s. Exiting..." % OUTPUT
				sys.exit()
		

	if REFRESH:
		repos = []
		page = 1
		while True:
			print "Fetching page %d of repo list.." % page
			data = get_url(API_URL % page)

			res = json.loads(data)
			if (len(res) == 0):
				break


			for repo in res:
				repos.append(repo['full_name'])

			page += 1
	else:
		repos = [line.split(" ")[0] for line in open("repos.txt", "r").readlines()]
	
	count = len(repos)
	print "Total repos found: %d." % count

	repos.sort()

	manifest = open(OUTPUT, "w")
	tmp_manifest = ""

	if REFRESH:
		list = open("repos.txt", "w")

	pos = 0
	for repo in repos:
		pos += 1
		print "Processing repo %d of %d" % (pos, count)
		tmp_manifest += '\t<project name="%s" />\n' % repo

		if REFRESH:
			try:
				data = json.loads(get_url("https://api.github.com/repos/%s/branches" % repo))
			except urllib2.HTTPError, e:
				print "[ %s ] HTTP Error: %d (%s)" % (repo, e.getcode(), e.msg)
				continue
			branches = []
			for branch in data:
				branches.append(branch['name'])
			list.write("%s %s\n" % (repo, " ".join(branches)))



	head = open("%s.head" % OUTPUT, "r").read()
	tail = open("%s.tail" % OUTPUT, "r").read()
	aosp = "\n".join(['\t<project name="%s" remote="aosp" />' % line.strip() for line in open("aosp.txt", "r").readlines()])

	manifest.writelines([head, tmp_manifest, "\n\n", aosp, "\n", tail])
	manifest.close()

	if REFRESH:
		list.close()

	print "Manifest %s written." % OUTPUT
