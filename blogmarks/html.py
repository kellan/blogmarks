from jinja2 import Environment, FileSystemLoader
import db

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)


def create_index(count=100, template='page.html'):
    posts = list(db.module().select_recent(count=count))
    data = {
        'page': {'title': 'Blogmarks'},
        'links': posts
    }
    template = env.get_template(template)
    output = template.render(data)
    print(output)

def create_archives(template='archives.html'):
    # fetch all year-month combinations from links
    year_months = db.module().distinct_year_months()
    print(list(year_months))
    # check if we already have an archive for that year-month
    # if not, create one
    # render the archive

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
    create_archives()

if __name__ == '__main__':
    main()