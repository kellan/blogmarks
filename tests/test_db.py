# ABOUTME: Comprehensive test suite for db.py database operations
# ABOUTME: Tests database connection, link insertion, and SQL query functionality
import pytest
import tempfile
import os
import sqlite3
from blogmarks import db

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

class TestDbModule:
    """Test database module creation and setup"""
    
    def test_module_creates_connection(self, temp_db):
        """Test that module() creates a working database connection"""
        queries = db.module()
        
        assert queries is not None
        # Test that we can execute a simple query
        result = queries.latest_ts()
        assert result is None or isinstance(result, int)
    
    def test_module_creates_tables(self, temp_db):
        """Test that module() creates the links table"""
        db.module()  # This should create tables
        
        # Verify table exists by checking schema
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links';")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == 'links'
    
    def test_table_has_correct_schema(self, temp_db):
        """Test that links table has all required columns"""
        db.module()  # Create tables
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(links);")
        columns = cursor.fetchall()
        conn.close()
        
        column_names = [col[1] for col in columns]
        expected_columns = ['id', 'ts', 'url', 'description', 'extended', 'via', 'tags', 'hash']
        
        for expected_col in expected_columns:
            assert expected_col in column_names

class TestInsertLink:
    """Test link insertion functionality"""
    
    def test_insert_link_basic(self, temp_db):
        """Test basic link insertion"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'via': None,
            'tags': 'python coding',
            'hash': 'test123'
        }
        
        result = db.insert_link(link)
        
        # Verify link was inserted
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM links WHERE hash = ?", ('test123',))
        db_result = cursor.fetchone()
        conn.close()
        
        assert db_result is not None
        assert db_result[2] == 'https://example.com'  # url
        assert db_result[3] == 'Test link'  # description
    
    def test_insert_link_with_via(self, temp_db):
        """Test link insertion with via field"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'via': 'tbray',
            'tags': 'python coding',
            'hash': 'test123'
        }
        
        db.insert_link(link)
        
        # Verify via field was saved
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT via FROM links WHERE hash = ?", ('test123',))
        via_result = cursor.fetchone()[0]
        conn.close()
        
        assert via_result == 'tbray'
    
    def test_insert_link_upsert_behavior(self, temp_db):
        """Test that insert_link uses upsert (insert or replace)"""
        # Insert initial link
        link1 = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Original description',
            'extended': 'Original extended',
            'via': None,
            'tags': 'python',
            'hash': 'test123'
        }
        db.insert_link(link1)
        
        # Update with same hash
        link2 = {
            'ts': 1234567891,
            'url': 'https://example.com',
            'description': 'Updated description',
            'extended': 'Updated extended',
            'via': 'tbray',
            'tags': 'python updated',
            'hash': 'test123'  # Same hash as first link
        }
        db.insert_link(link2)
        
        # Verify only one record exists with updated data
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), description, via FROM links WHERE hash = ?", ('test123',))
        result = cursor.fetchone()
        conn.close()
        
        count, description, via = result
        assert count == 1
        assert description == 'Updated description'
        assert via == 'tbray'

class TestDatabaseQueries:
    """Test SQL queries work correctly"""
    
    def test_latest_ts_empty_database(self, temp_db):
        """Test latest_ts returns None for empty database"""
        queries = db.module()
        result = queries.latest_ts()
        assert result is None
    
    def test_latest_ts_with_data(self, temp_db):
        """Test latest_ts returns correct timestamp"""
        # Insert test links with different timestamps
        links = [
            {
                'ts': 1234567890,
                'url': 'https://example1.com',
                'description': 'Link 1',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'hash1'
            },
            {
                'ts': 1234567900,  # Later timestamp
                'url': 'https://example2.com',
                'description': 'Link 2',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'hash2'
            },
            {
                'ts': 1234567880,  # Earlier timestamp
                'url': 'https://example3.com',
                'description': 'Link 3',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'hash3'
            }
        ]
        
        for link in links:
            db.insert_link(link)
        
        queries = db.module()
        result = queries.latest_ts()
        
        assert result == 1234567900  # Should return the latest timestamp
    
    def test_select_recent(self, temp_db):
        """Test select_recent query"""
        # Insert test links
        links = [
            {
                'ts': 1234567890,
                'url': 'https://example1.com',
                'description': 'Link 1',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'hash1'
            },
            {
                'ts': 1234567900,
                'url': 'https://example2.com',
                'description': 'Link 2',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'hash2'
            }
        ]
        
        for link in links:
            db.insert_link(link)
        
        queries = db.module()
        results = list(queries.select_recent(count=10))
        
        assert len(results) == 2
        # Should be ordered by timestamp desc (most recent first)
        assert results[0]['ts'] == 1234567900
        assert results[1]['ts'] == 1234567890
    
    def test_distinct_year_months(self, temp_db):
        """Test distinct_year_months query"""
        # Insert links from different months
        links = [
            {
                'ts': 1704067200,  # 2024-01-01
                'url': 'https://jan.com',
                'description': 'January link',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'jan'
            },
            {
                'ts': 1706745600,  # 2024-02-01
                'url': 'https://feb.com',
                'description': 'February link',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'feb'
            },
            {
                'ts': 1704153600,  # Another January date
                'url': 'https://jan2.com',
                'description': 'Another January link',
                'extended': '',
                'via': None,
                'tags': 'test',
                'hash': 'jan2'
            }
        ]
        
        for link in links:
            db.insert_link(link)
        
        queries = db.module()
        results = list(queries.distinct_year_months())
        
        # Should return unique year-month combinations
        year_months = [r['year_month'] for r in results]
        assert '2024-01' in year_months
        assert '2024-02' in year_months
        assert len(year_months) == 2  # Should be distinct