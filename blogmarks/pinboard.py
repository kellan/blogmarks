from dotenv import load_dotenv
import os
import xmltodict, iso8601, click
import json, urllib.request, sys
from typing import Any
import db

load_dotenv()

# make sure you set PINBOARD_API_TOKEN environment variable

def pinboard_api(method, **kwargs):
	"Call the pinboard API and return parsed results from the XML"
	if 'auth_token' not in kwargs:
		kwargs['auth_token'] = os.getenv("PINBOARD_API_TOKEN")
	print("API TOKEN:", kwargs['auth_token'])

	print("Call some other URL")
	fp = urllib.request.urlopen("https://kellanem.com")
	print("Call pinboard URL")
	fp = urllib.request.urlopen("https://pinboard.in/u:kellan")

	arg_strings = [f'{k}={v}' for k, v in kwargs.items()]
	args = '?' + '&'.join(arg_strings)
	url = f'https://api.pinboard.in/v1/{method}{args}'
	print(url)
	try:
		fp = urllib.request.urlopen(url)
		dom = xmltodict.parse(fp)
		return dom
	except urllib.error.HTTPError as e:
		print(f"HTTPError: {e.code}")
		print(f"Reason: {e.reason}")
		print(f"Headers: {e.headers}")
		print(f"URL: {url}")
		return None
	except Exception as e:
		print(f"An error occurred: {e}")
		return None

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
	for link in links:
		db.insert_link(link)

def main():
	kwargs = {}
	if os.getenv("PINBOARD_API_COUNT"):
		kwargs['count'] = os.getenv("PINBOARD_API_COUNT")

	if os.getenv("PINBOARD_API_TAG"):
		kwargs['tag'] = os.getenv("PINBOARD_API_TAG")

	# if os.getenv("PINBOARD_API_TOKEN") == '***':
	# 	print("Token is '***'")
	# else:
	# 	print("Token is not '***'")

	links = fetch_recent(**kwargs)
	add_links(links)

if __name__ == '__main__':
	main()