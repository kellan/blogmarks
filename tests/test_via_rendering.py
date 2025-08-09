# ABOUTME: Test suite for via field rendering functionality in templates
# ABOUTME: Tests URL detection filter for via field rendering logic
import pytest
from blogmarks.render import is_url_filter

class TestViaUrlDetection:
    """Test URL detection filter for template use"""
    
    def test_is_url_filter_detects_valid_urls(self):
        """Test that is_url filter correctly identifies URLs"""
        # Valid URLs
        assert is_url_filter('http://example.com') is True
        assert is_url_filter('https://www.tbray.org/ongoing/') is True
        assert is_url_filter('https://mastodon.social/@user/123456789') is True
        assert is_url_filter('http://mike.teczno.com/notes/') is True
        
    def test_is_url_filter_rejects_non_urls(self):
        """Test that is_url filter correctly rejects non-URLs"""
        # Non-URLs
        assert is_url_filter('chris.dary') is False
        assert is_url_filter('user.name') is False
        assert is_url_filter('example.com') is False  # No protocol
        assert is_url_filter('just text') is False
        assert is_url_filter('user@domain') is False
        
    def test_is_url_filter_handles_edge_cases(self):
        """Test that is_url filter handles None and empty strings"""
        assert is_url_filter(None) is False
        assert is_url_filter('') is False
        assert is_url_filter('   ') is False  # whitespace only
        assert is_url_filter('http://') is False  # incomplete URL