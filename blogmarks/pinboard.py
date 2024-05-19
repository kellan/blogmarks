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
	arg_strings = [f'{k}={v}' for k, v in kwargs.items()]
	args = '?' + '&'.join(arg_strings)
	url = f'https://api.pinboard.in/v1/{method}{args}'
	fp = urllib.request.urlopen(url)
	dom = xmltodict.parse(fp)
	return dom

def iso_to_unix(ts: str):
	dt = iso8601.parse_date(ts)
	return int(dt.timestamp())

def fetch_recent() -> list[dict[str, Any]]:
	"Get the recent.xml from Pinboard"
	dom = pinboard_api('posts/recent', count=20)
	links = []
	for post in dom['posts']['post']:
		links.append({
			'ts': iso_to_unix(post['@time']), 'url': post['@href'], 'description': post['@description'], 'extended':
			post['@extended'], 'tags': post['@tag'], 'hash': post['@hash']
		})
	return links


# def add_recent():
# 	"Call the Pinboard API and add any recent links"
# 	# Compare timestamp from Pinboard API to database
# 	pb_ts = newest_time()
# 	db_ts = queries.latest_ts()
# 	if pb_ts <= db_ts:
# 		print(f'No new links. Pinboard: {pb_ts}, DB: {db_ts}')
# 		return 3
# 	recent = get_recent()
# 	queries.upsert_link(recent)  # type: ignore
# 	print(f'Added {len(recent)} links from recent')
# 	return 0

def main():
	links = fetch_recent()
	print(links)
	db.insert_link(link)


if __name__ == '__main__':
	main()
