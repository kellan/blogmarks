from jinja2 import Environment, FileSystemLoader
import db
import datetime 
import os

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)

def format_ts(ts, format="%Y-%m-%d"):
    return datetime.datetime.fromtimestamp(ts).strftime(format)


def link_tags(tags, joiner=' '):
    base_url = 'https://pinboard.in/u:kellan/t:'
    tag_urls = [f'<a href="{base_url}{tag}">{tag}</a>' for tag in tags]
    return joiner.join(tag_urls)

env.filters["format_ts"] = format_ts
env.filters["link_tags"] = link_tags

def create_index(count=100, template='page.html'):
    posts = list(db.module().select_recent(count=count))
    posts = prepare_posts(posts)
    data = {
        'page': {'title': 'Blogmarks'},
        'links': posts
    }

    os.makedirs('_site', exist_ok=True)

    with open(f'_site/index.html', 'w') as fp:
        fp.write(render(template, data)) 
    

def create_archives(template='page.html'):
    # fetch all year-month combinations from links
    year_months = db.module().distinct_year_months()

    for year_month in year_months:
        posts = list(db.module().select_by_year_month(**year_month))
        data = {
            'page': {'title': year_month['year_month']},
            'links': posts
        }

        os.makedirs('_site', exist_ok=True)
        with open(f'_site/{year_month["year_month"]}.html', 'w') as fp:
            fp.write(render(template, data)) 


def prepare_posts(links):
    munged_links = []
    for link in links:
        clean_tags = link['tags'].split(' ')
        clean_tags = list(filter(lambda t: t not in ('+', '-'), clean_tags))
        link['clean_tags'] = sorted(clean_tags)
        if 'quotable' in clean_tags:
            link['quotable'] = True

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

if __name__ == '__main__':
    main()