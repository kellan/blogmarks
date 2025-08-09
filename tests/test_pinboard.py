# ABOUTME: Comprehensive test suite for pinboard.py functions
# ABOUTME: Tests link fetching, processing, date/via tag handling, and database operations
import pytest
import tempfile
import os
import sqlite3
from unittest.mock import patch, MagicMock
from blogmarks.pinboard import iso_to_unix, munge_link, add_links
from blogmarks import db
import datetime

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)
    
    # Override the db module to use temp database
    original_module_func = db.module
    def temp_module():
        queries = original_module_func()
        queries.connect(f'sqlite:///{temp_path}')
        queries.create_links_tables()
        return queries
    
    db.module = temp_module
    
    yield temp_path
    
    # Cleanup
    db.module = original_module_func
    os.unlink(temp_path)

class TestIsoToUnix:
    """Test ISO timestamp conversion to Unix timestamp"""
    
    def test_iso_to_unix_basic(self):
        """Test basic ISO to Unix conversion"""
        iso_string = "2024-01-15T10:30:00Z"
        result = iso_to_unix(iso_string)
        assert isinstance(result, int)
        assert result > 0
    
    def test_iso_to_unix_with_timezone(self):
        """Test ISO to Unix conversion with timezone"""
        iso_string = "2024-01-15T10:30:00-05:00"
        result = iso_to_unix(iso_string)
        assert isinstance(result, int)
        assert result > 0

class TestMungeLink:
    """Test link processing and tag handling"""
    
    def test_munge_link_basic(self):
        """Test basic link processing without special tags"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python coding web',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        assert result['tags'] == 'python coding web'
        assert 'via' not in result or result['via'] is None
        assert result['ts'] == 1234567890
    
    def test_munge_link_with_via_tag(self):
        """Test via tag extraction and removal"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python via:tbray coding',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        assert result['via'] == 'https://www.tbray.org/ongoing/'
        assert 'via:tbray' not in result['tags']
        assert 'python coding' in result['tags']
    
    def test_munge_link_with_date_tag(self):
        """Test date tag extraction and timestamp replacement"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python date:2024-01-15 coding',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        expected_ts = datetime.datetime.strptime("2024-01-15", "%Y-%m-%d").timestamp()
        assert result['ts'] == expected_ts
        assert 'date:2024-01-15' not in result['tags']
        assert 'python coding' in result['tags']
    
    def test_munge_link_with_both_via_and_date(self):
        """Test handling both via and date tags"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python via:nelson date:2024-01-15 coding',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        expected_ts = datetime.datetime.strptime("2024-01-15", "%Y-%m-%d").timestamp()
        assert result['via'] == 'https://www.somebits.com/weblog/'
        assert result['ts'] == expected_ts
        assert 'via:nelson' not in result['tags']
        assert 'date:2024-01-15' not in result['tags']
        assert 'python coding' in result['tags']
    
    def test_munge_link_preserves_other_fields(self):
        """Test that other fields are preserved unchanged"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python coding',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        assert result['url'] == link['url']
        assert result['description'] == link['description']
        assert result['extended'] == link['extended']
        assert result['hash'] == link['hash']

class TestAddLinks:
    """Test adding links to database"""
    
    def test_add_links_basic(self, temp_db):
        """Test adding basic links to database"""
        test_links = [{
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python coding',
            'hash': 'test123'
        }]
        
        add_links(test_links)
        
        # Verify link was saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM links WHERE url = ?", ('https://example.com',))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[2] == 'https://example.com'  # url column
        assert result[3] == 'Test link'  # description column
    
    def test_add_links_skips_future_dates(self, temp_db):
        """Test that links with future timestamps are skipped"""
        future_ts = int(datetime.datetime.now().timestamp()) + 86400  # tomorrow
        
        test_links = [{
            'ts': future_ts,
            'url': 'https://future.com',
            'description': 'Future link',
            'extended': 'Extended description',
            'tags': 'future',
            'hash': 'future123'
        }]
        
        # Ensure database is initialized
        db.module()
        
        add_links(test_links)
        
        # Verify link was NOT saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM links WHERE url = ?", ('https://future.com',))
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 0
    
    def test_add_links_processes_multiple_links(self, temp_db):
        """Test adding multiple links at once"""
        test_links = [
            {
                'ts': 1234567890,
                'url': 'https://example1.com',
                'description': 'Test link 1',
                'extended': 'Extended description 1',
                'tags': 'python',
                'hash': 'test123'
            },
            {
                'ts': 1234567891,
                'url': 'https://example2.com',
                'description': 'Test link 2',
                'extended': 'Extended description 2',
                'tags': 'javascript via:tbray',
                'hash': 'test456'
            }
        ]
        
        add_links(test_links)
        
        # Verify both links were saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]
        
        # Check via field was populated for second link
        cursor.execute("SELECT via FROM links WHERE url = ?", ('https://example2.com',))
        via_result = cursor.fetchone()[0]
        conn.close()
        
        assert count == 2
        assert via_result == 'https://www.tbray.org/ongoing/'