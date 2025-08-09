# ABOUTME: Test file for validating via field functionality in link processing
# ABOUTME: Ensures links with via: tags get properly saved to database with via field populated
import pytest
import tempfile
import os
import sqlite3
from blogmarks.pinboard import add_links, munge_link
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

def test_via_field_saved_to_database(temp_db):
    """Test that links with via: tags get via field saved to database"""
    # Arrange
    test_links = [{
        'ts': 1234567890,
        'url': 'https://example.com',
        'description': 'Test link',
        'extended': 'Extended description',
        'tags': 'python via:tbray coding',
        'hash': 'test123'
    }]
    
    # Act
    add_links(test_links)
    
    # Assert
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT via, tags FROM links WHERE url = ?", ('https://example.com',))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    via_field, tags_field = result
    assert via_field == 'https://www.tbray.org/ongoing/'  # via: tag should be extracted and expanded
    assert 'via:tbray' not in tags_field  # via: tag should be removed from tags
    assert 'python coding' in tags_field  # other tags should remain

def test_munge_link_extracts_via_tag():
    """Test that munge_link properly extracts via: tag"""
    # Arrange
    link = {
        'ts': 1234567890,
        'url': 'https://example.com',
        'description': 'Test link',
        'extended': 'Extended description',
        'tags': 'python via:nelson coding',
        'hash': 'test456'
    }
    
    # Act
    munged_link = munge_link(link)
    
    # Assert
    assert munged_link['via'] == 'https://www.somebits.com/weblog/'
    assert 'via:nelson' not in munged_link['tags']
    assert 'python coding' in munged_link['tags']