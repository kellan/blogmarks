from dotenv import load_dotenv
import os
import xmltodict, iso8601, click
import json, urllib.request, sys
from typing import Any
from . import db
import datetime

load_dotenv()

# make sure you set PINBOARD_API_TOKEN environment variable

def pinboard_api(method, **kwargs):
	"Call the pinboard API and return parsed results from the XML"
	if 'auth_token' not in kwargs:
		kwargs['auth_token'] = os.getenv("PINBOARD_API_TOKEN")

	arg_strings = [f'{k}={v}' for k, v in kwargs.items()]
	args = '?' + '&'.join(arg_strings)
	url = f'https://api.pinboard.in/v1/{method}{args}'
	print(url)
	
	fp = urllib.request.urlopen(url)
	dom = xmltodict.parse(fp)
	return dom

def iso_to_unix(ts: str):
	dt = iso8601.parse_date(ts)
	return int(dt.timestamp())

def newest_time() -> int:
	dom = pinboard_api('posts/update')
	return iso_to_unix(dom['update']['@time'])

def fetch_recent(**kwargs) -> list[dict[str, Any]]:
	"Get the recent.xml from Pinboard"

	pb_ts = newest_time()
	db_ts = db.module().latest_ts() or 0
	if pb_ts <= db_ts:
		print(f'No new links. Pinboard: {pb_ts}, DB: {db_ts}')
		return []
	
	if 'count' not in kwargs:
		kwargs['count'] = 20
	

	dom = pinboard_api('posts/recent', **kwargs)
	links = []
	for post in dom['posts']['post']:
		links.append({
			'ts': iso_to_unix(post['@time']), 'url': post['@href'], 'description': post['@description'], 'extended':
			post['@extended'], 'tags': post['@tag'], 'hash': post['@hash']
		})
	return links


def add_links(links):
	now = datetime.datetime.now().timestamp()
	for link in links:
		link = munge_link(link)

		if link['ts'] > now:
			print(f"Skipping future link: {link['url']}")
			continue

		db.insert_link(link)

def munge_link(link):
	date_tag = None
	via_tag = None

	# Initialize via field to None if not already present
	if 'via' not in link:
		link['via'] = None

	tags = link['tags'].split(' ')
	for tag in tags:
		if tag.startswith("date:"):
			date_tag = tag
		elif tag.startswith("via:"):
			via_tag = tag

	if via_tag:
		raw_via = via_tag[4:]
		link['via'] = expand_via_shorthand(raw_via)
		tags.remove(via_tag)

	if date_tag:
		link['ts'] = datetime.datetime.strptime(date_tag[5:], "%Y-%m-%d").timestamp()
		tags.remove(date_tag)
	link['tags'] = ' '.join(tags)
	
	return link

def expand_via_shorthand(via_code):
	"""
	Expand via shorthand codes to full URLs.
	Returns the original value if not a known shorthand or already a URL.
	"""
	if not via_code:
		return via_code
	
	# If it's already a URL, return as-is
	if via_code.startswith(('http://', 'https://')):
		return via_code
	
	# Via shorthand mappings
	via_mappings = {
		'tbray': 'https://www.tbray.org/ongoing/',
		'migurski': 'http://mike.teczno.com/notes/',
		'skamille': 'https://www.elidedbranches.com/',
		'nelson': 'https://www.somebits.com/weblog/',
		'kottke': 'https://kottke.org/',
		'waxy': 'https://waxy.org/',
		'kottke.org': 'https://kottke.org/',
		'sarah.milstein': 'https://www.sarahmilstein.com/',
	}
	
	return via_mappings.get(via_code, via_code)

def main():
	kwargs = {}
	if os.getenv("PINBOARD_API_COUNT"):
		kwargs['count'] = os.getenv("PINBOARD_API_COUNT")

	if os.getenv("PINBOARD_API_TAG"):
		kwargs['tag'] = os.getenv("PINBOARD_API_TAG")

	links = fetch_recent(**kwargs)
	add_links(links)

if __name__ == '__main__':
	main()