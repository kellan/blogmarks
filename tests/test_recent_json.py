# ABOUTME: Tests for create_recent_json() which exports recent links as JSON
# ABOUTME: Verifies JSON file creation, structure, and field contents
import pytest
import tempfile
import os
import json
from blogmarks.render import create_recent_json
from blogmarks import db


BLOGMARKS_ROOT = os.path.join(os.path.dirname(__file__), '..')


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)

    # Override the db module to use temp database
    original_module_func = db.module
    sql_dir = os.path.join(BLOGMARKS_ROOT, 'sql/')

    def temp_module():
        import pugsql
        queries = pugsql.module(sql_dir)
        queries.connect(f'sqlite:///{temp_path}')
        queries.create_links_tables()
        return queries

    db.module = temp_module

    yield temp_path

    # Cleanup
    db.module = original_module_func
    os.unlink(temp_path)


@pytest.fixture
def populated_db(temp_db):
    """Create a temp database with some test links"""
    queries = db.module()
    for i in range(5):
        queries.upsert_link(
            ts=1700000000 + i * 86400,
            url=f'https://example.com/{i}',
            description=f'Test Link {i}',
            extended=f'Extended description for link {i}',
            via='',
            tags='python coding' if i % 2 == 0 else 'python quotable',
            hash=f'hash{i}',
        )
    return temp_db


class TestCreateRecentJson:
    def test_creates_json_file(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        assert os.path.exists(tmp_path / '_site' / 'recent_links.json')

    def test_output_is_valid_json(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        assert isinstance(data, list)

    def test_contains_expected_fields(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        assert len(data) == 5
        for item in data:
            assert 'url' in item
            assert 'description' in item
            assert 'extended' in item
            assert 'ts' in item
            assert 'quotable' in item

    def test_ts_formatted_as_date(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        for item in data:
            # Should be YYYY-MM-DD format
            parts = item['ts'].split('-')
            assert len(parts) == 3
            assert len(parts[0]) == 4

    def test_quotable_flag(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        quotable_values = [item['quotable'] for item in data]
        assert True in quotable_values
        assert False in quotable_values

    def test_ordered_most_recent_first(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        # Most recent link (hash4) should be first
        assert data[0]['url'] == 'https://example.com/4'
        assert data[-1]['url'] == 'https://example.com/0'

    def test_empty_db_produces_empty_list(self, temp_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json()
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        assert data == []

    def test_respects_count_parameter(self, populated_db, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        create_recent_json(count=3)
        with open(tmp_path / '_site' / 'recent_links.json') as fp:
            data = json.load(fp)
        assert len(data) == 3
