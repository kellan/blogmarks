from jinja2 import Environment, FileSystemLoader
from . import db
import datetime
import json
import os
import collections

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)

def format_ts(ts, format="%Y-%m-%d"):
    return datetime.datetime.fromtimestamp(ts).strftime(format)

def format_ts_rfc3339(ts):
    """Format a timestamp as a date suitable for inclusion in Atom feeds."""
    date = datetime.datetime.fromtimestamp(ts)
    return date.isoformat() + ("Z" if date.utcoffset() is None else "")

def link_tags(tags, joiner=' '):
    base_url = 'https://pinboard.in/u:kellan/t:'
    tag_urls = [f'<a href="{base_url}{tag}">{tag}</a>' for tag in tags]
    return joiner.join(tag_urls)

def is_url_filter(value):
    """
    Jinja filter to detect if a value is a valid URL.
    Returns True if the value starts with http:// or https://
    """
    if not value or not isinstance(value, str):
        return False
    
    value = value.strip()
    if not value:
        return False
    
    return value.startswith(('http://', 'https://')) and len(value) > 8

env.filters["format_ts"] = format_ts
env.filters["link_tags"] = link_tags
env.filters["format_ts_rfc3339"] = format_ts_rfc3339
env.filters["is_url"] = is_url_filter

def create_index(count=100, template='links.html'):
    posts = list(db.module().select_recent(count=count))
    posts = prepare_posts(posts)
    data = {
        'page' : {},
        'links': posts
    }

    os.makedirs('_site', exist_ok=True)

    with open(f'_site/index.html', 'w') as fp:
        fp.write(render(template, data)) 
    

def create_archives():
    # fetch all year-month combinations from links
    year_months = db.module().distinct_year_months()

    archives = collections.defaultdict(list)

    for year_month in year_months:
        (year, month) = year_month["year_month"].split('-')
        archives[year].append(month)

        posts = list(db.module().select_by_year_month(**year_month))
        posts = prepare_posts(posts)
        
        data = {
            'page': {'title': f'Archive: {year_month["year_month"]}'},
            'links': posts
        }

        os.makedirs('_site', exist_ok=True)
        with open(f'_site/{year_month["year_month"]}.html', 'w') as fp:
            fp.write(render('links.html', data)) 


    data = {
        'page': {'title': 'Archive'},
        'year_months' : archives
    }

    with open(f"_site/archive.html", 'w') as fp:
        fp.write(render('archive.html', data))

def create_recent_json(count=15):
    posts = list(db.module().select_recent(count=count))
    posts = prepare_posts(posts)
    recent = []
    for post in posts:
        recent.append({
            'url': post['url'],
            'description': post['description'],
            'extended': post['extended'],
            'ts': format_ts(post['ts'], "%Y-%m-%d"),
            'quotable': post.get('quotable', False),
        })

    os.makedirs('_site', exist_ok=True)

    with open('_site/recent_links.json', 'w') as fp:
        json.dump(recent, fp, indent=2)


def create_feed(count=100):
    posts = list(db.module().select_recent(count=count))
    posts = prepare_posts(posts)
    data = {
        'links': posts
    }

    os.makedirs('_site', exist_ok=True)

    template = 'atom.xml'

    with open(f'_site/index.atom', 'w') as fp:
        fp.write(render(template, data)) 
    

def prepare_posts(links):
    munged_links = []
    for link in links:
        clean_tags = link['tags'].split(' ')
        clean_tags = list(filter(lambda t: t not in ('+', '-'), clean_tags))
        link['clean_tags'] = sorted(clean_tags)
        if 'quotable' in clean_tags:
            link['quotable'] = True

        #markdown = mistune.create_markdown()
        #link['extended'] = markdown(link['extended'])

        munged_links.append(link)
    
    return munged_links


def render(template, data):
    template = env.get_template(template)
    return template.render(data)

def test():
    template = env.get_template('page.html')
    # Define the data to pass to the template
    data = {
        'page' : {'title': 'My Page Title'},
        'links': [
            {'description': 'Post 1', 'extended': 'This is the body of post 1', 'ts': 1234567890, 'url': 'http://example.com'},
            {'description': 'Post 2', 'extended': 'This is the body of post 2', 'ts': 1234567890, 'url': 'http://example.com/2'},
    ]}

    # Render the template with data
    output = template.render(data)
    print(output)

def main():
    create_index()
    create_archives()
    create_feed()
    create_recent_json()

if __name__ == '__main__':
    main()