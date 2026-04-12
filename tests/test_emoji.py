# ABOUTME: Tests that emoji in link fields survive the full pipeline
# ABOUTME: Covers database storage, HTML rendering, Atom feed, and JSON output
import pytest
import tempfile
import os
import sqlite3
import json
from blogmarks import db
from blogmarks.pinboard import munge_link
from blogmarks.render import prepare_posts, render, create_recent_json


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)

    original_module_func = db.module
    def temp_module():
        queries = original_module_func()
        queries.connect(f'sqlite:///{temp_path}')
        queries.create_links_tables()
        return queries

    db.module = temp_module

    yield temp_path

    db.module = original_module_func
    os.unlink(temp_path)


def make_emoji_link():
    return {
        'ts': 1712700000,
        'url': 'https://example.com/rocket',
        'description': 'Launching rockets 🚀 into space',
        'extended': 'This is 🔥 and also 💯 percent cool',
        'via': None,
        'tags': 'space 🏷️emoji fun',
        'hash': 'emoji123'
    }


class TestEmojiDatabase:
    """Test emoji round-trips through the database"""

    def test_emoji_in_description_survives_db(self, temp_db):
        link = make_emoji_link()
        db.insert_link(link)

        queries = db.module()
        results = list(queries.select_recent(count=1))
        assert results[0]['description'] == 'Launching rockets 🚀 into space'

    def test_emoji_in_extended_survives_db(self, temp_db):
        link = make_emoji_link()
        db.insert_link(link)

        queries = db.module()
        results = list(queries.select_recent(count=1))
        assert results[0]['extended'] == 'This is 🔥 and also 💯 percent cool'

    def test_emoji_in_tags_survives_db(self, temp_db):
        link = make_emoji_link()
        db.insert_link(link)

        queries = db.module()
        results = list(queries.select_recent(count=1))
        assert results[0]['tags'] == 'space 🏷️emoji fun'


class TestEmojiMunge:
    """Test emoji survives the munge_link processing"""

    def test_emoji_in_description_after_munge(self):
        link = make_emoji_link()
        result = munge_link(link)
        assert '🚀' in result['description']

    def test_emoji_in_tags_after_munge(self):
        link = make_emoji_link()
        result = munge_link(link)
        assert '🏷️emoji' in result['tags']

    def test_emoji_tag_with_via(self):
        link = make_emoji_link()
        link['tags'] = 'space 🏷️emoji via:kottke fun'
        result = munge_link(link)
        assert '🏷️emoji' in result['tags']
        assert result['via'] == 'https://kottke.org/'


class TestEmojiRendering:
    """Test emoji renders correctly in HTML and Atom output"""

    def test_emoji_in_html_output(self):
        links = [make_emoji_link()]
        posts = prepare_posts(links)
        data = {'page': {}, 'links': posts}
        html = render('links.html', data)
        assert '🚀' in html
        assert '🔥' in html

    def test_emoji_in_atom_output(self):
        links = [make_emoji_link()]
        posts = prepare_posts(links)
        data = {'links': posts}
        atom = render('atom.xml', data)
        assert '🚀' in atom
        assert '🔥' in atom

    def test_emoji_in_tags_rendered(self):
        links = [make_emoji_link()]
        posts = prepare_posts(links)
        assert '🏷️emoji' in posts[0]['clean_tags']


class TestEmojiJson:
    """Test emoji in JSON output"""

    def test_emoji_preserved_in_json_roundtrip(self):
        """Verify emoji survives JSON serialization and deserialization"""
        link = make_emoji_link()
        json_str = json.dumps(link, ensure_ascii=False)
        roundtripped = json.loads(json_str)
        assert roundtripped['description'] == link['description']
        assert '🚀' in roundtripped['description']

    def test_emoji_escaped_with_ensure_ascii(self):
        """The current code uses ensure_ascii=True (default), emoji gets escaped"""
        link = make_emoji_link()
        json_str = json.dumps({'description': link['description']})
        # With ensure_ascii=True, emoji becomes \uXXXX escape sequences
        # But it should still round-trip correctly
        roundtripped = json.loads(json_str)
        assert '🚀' in roundtripped['description']

    def test_json_output_has_no_surrogate_escapes(self, temp_db):
        """JSON must not contain surrogate pair escapes (\\uD800-\\uDFFF).

        Jekyll loads _data/recent_links.json via safe_yaml/Psych which
        rejects surrogate pair escapes as invalid Unicode. Writing literal
        UTF-8 emoji avoids this."""
        link = make_emoji_link()
        db.insert_link(link)
        create_recent_json(count=1)
        with open('_site/recent_links.json', 'r') as f:
            json_str = f.read()
        import re
        surrogates = re.findall(r'\\ud[89a-f][0-9a-f]{2}', json_str, re.IGNORECASE)
        assert surrogates == [], f"Found surrogate escapes: {surrogates}"
