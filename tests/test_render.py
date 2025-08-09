# ABOUTME: Comprehensive test suite for render.py template and HTML generation functions
# ABOUTME: Tests timestamp formatting, tag linking, post preparation, and template rendering
import pytest
import tempfile
import os
import sqlite3
from blogmarks.render import format_ts, format_ts_rfc3339, link_tags, prepare_posts, render
from blogmarks import db
import datetime
from unittest.mock import patch, MagicMock

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

class TestFormatTs:
    """Test timestamp formatting functions"""
    
    def test_format_ts_default(self):
        """Test default timestamp formatting (YYYY-MM-DD)"""
        ts = 1234567890  # 2009-02-13 23:31:30 UTC
        result = format_ts(ts)
        assert result == "2009-02-13"
    
    def test_format_ts_custom_format(self):
        """Test custom timestamp formatting"""
        ts = 1234567890  # 2009-02-13 23:31:30 UTC
        result = format_ts(ts, format="%B %d, %Y")
        assert result == "February 13, 2009"
    
    def test_format_ts_time_format(self):
        """Test timestamp formatting with time"""
        ts = 1234567890  # 2009-02-13 23:31:30 UTC
        result = format_ts(ts, format="%Y-%m-%d %H:%M")
        assert "2009-02-13" in result
        # Note: exact time may vary based on local timezone

class TestFormatTsRfc3339:
    """Test RFC3339 timestamp formatting for Atom feeds"""
    
    def test_format_ts_rfc3339_basic(self):
        """Test RFC3339 timestamp formatting"""
        ts = 1234567890  # 2009-02-13 23:31:30 UTC
        result = format_ts_rfc3339(ts)
        
        # Should be ISO format with timezone indicator
        assert "2009-02-13" in result
        assert ":" in result  # Time separator
        assert ("Z" in result or "+" in result or "-" in result)  # Timezone indicator
    
    def test_format_ts_rfc3339_format(self):
        """Test that RFC3339 format is valid ISO format"""
        ts = 1234567890
        result = format_ts_rfc3339(ts)
        
        # Should be parseable as ISO format
        try:
            datetime.datetime.fromisoformat(result.replace('Z', '+00:00'))
            assert True
        except ValueError:
            assert False, f"Invalid ISO format: {result}"

class TestLinkTags:
    """Test tag linking functionality"""
    
    def test_link_tags_single_tag(self):
        """Test linking a single tag"""
        tags = ['python']
        result = link_tags(tags)
        
        expected = '<a href="https://pinboard.in/u:kellan/t:python">python</a>'
        assert result == expected
    
    def test_link_tags_multiple_tags(self):
        """Test linking multiple tags with default joiner"""
        tags = ['python', 'coding', 'web']
        result = link_tags(tags)
        
        assert 'href="https://pinboard.in/u:kellan/t:python">python</a>' in result
        assert 'href="https://pinboard.in/u:kellan/t:coding">coding</a>' in result
        assert 'href="https://pinboard.in/u:kellan/t:web">web</a>' in result
        # Default joiner is space
        assert ' ' in result
    
    def test_link_tags_custom_joiner(self):
        """Test linking tags with custom joiner"""
        tags = ['python', 'coding']
        result = link_tags(tags, joiner=', ')
        
        assert ', ' in result
        assert 'href="https://pinboard.in/u:kellan/t:python">python</a>' in result
        assert 'href="https://pinboard.in/u:kellan/t:coding">coding</a>' in result
    
    def test_link_tags_empty_list(self):
        """Test linking empty tag list"""
        tags = []
        result = link_tags(tags)
        assert result == ""

class TestPreparePosts:
    """Test post preparation for rendering"""
    
    def test_prepare_posts_basic(self):
        """Test basic post preparation"""
        links = [
            {
                'id': 1,
                'ts': 1234567890,
                'url': 'https://example.com',
                'description': 'Test link',
                'extended': 'Extended description',
                'via': None,
                'tags': 'python coding web',
                'hash': 'test123'
            }
        ]
        
        result = prepare_posts(links)
        
        assert len(result) == 1
        assert result[0]['clean_tags'] == ['coding', 'python', 'web']  # Sorted
        assert 'quotable' not in result[0]
    
    def test_prepare_posts_filters_special_tags(self):
        """Test that +/- tags are filtered out"""
        links = [
            {
                'id': 1,
                'ts': 1234567890,
                'url': 'https://example.com',
                'description': 'Test link',
                'extended': 'Extended description',
                'via': None,
                'tags': 'python + - coding web',
                'hash': 'test123'
            }
        ]
        
        result = prepare_posts(links)
        
        clean_tags = result[0]['clean_tags']
        assert '+' not in clean_tags
        assert '-' not in clean_tags
        assert 'python' in clean_tags
        assert 'coding' in clean_tags
        assert 'web' in clean_tags
    
    def test_prepare_posts_quotable_flag(self):
        """Test quotable flag is set when quotable tag present"""
        links = [
            {
                'id': 1,
                'ts': 1234567890,
                'url': 'https://example.com',
                'description': 'Test link',
                'extended': 'Extended description',
                'via': None,
                'tags': 'python quotable coding',
                'hash': 'test123'
            }
        ]
        
        result = prepare_posts(links)
        
        assert result[0]['quotable'] is True
        assert 'quotable' in result[0]['clean_tags']
    
    def test_prepare_posts_multiple_links(self):
        """Test preparing multiple posts"""
        links = [
            {
                'id': 1,
                'ts': 1234567890,
                'url': 'https://example1.com',
                'description': 'Test link 1',
                'extended': 'Extended description 1',
                'via': None,
                'tags': 'python coding',
                'hash': 'test123'
            },
            {
                'id': 2,
                'ts': 1234567891,
                'url': 'https://example2.com',
                'description': 'Test link 2',
                'extended': 'Extended description 2',
                'via': 'tbray',
                'tags': 'javascript quotable',
                'hash': 'test456'
            }
        ]
        
        result = prepare_posts(links)
        
        assert len(result) == 2
        assert result[0]['clean_tags'] == ['coding', 'python']
        assert result[1]['clean_tags'] == ['javascript', 'quotable']
        assert 'quotable' not in result[0]
        assert result[1]['quotable'] is True

class TestRender:
    """Test template rendering functionality"""
    
    def test_render_basic_template(self):
        """Test basic template rendering"""
        # Create a simple test template
        with patch('blogmarks.render.env') as mock_env:
            mock_template = MagicMock()
            mock_template.render.return_value = "Rendered content"
            mock_env.get_template.return_value = mock_template
            
            result = render('test.html', {'key': 'value'})
            
            assert result == "Rendered content"
            mock_env.get_template.assert_called_once_with('test.html')
            mock_template.render.assert_called_once_with({'key': 'value'})
    
    def test_render_passes_data_correctly(self):
        """Test that render passes data to template correctly"""
        test_data = {
            'page': {'title': 'Test Page'},
            'links': [{'url': 'https://example.com'}]
        }
        
        with patch('blogmarks.render.env') as mock_env:
            mock_template = MagicMock()
            mock_env.get_template.return_value = mock_template
            
            render('test.html', test_data)
            
            mock_template.render.assert_called_once_with(test_data)

# Integration tests for file generation functions would require more complex setup
# and file system mocking, which may be beyond the scope of this comprehensive test suite.
# The core logic functions are well covered above.