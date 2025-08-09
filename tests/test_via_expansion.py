# ABOUTME: Test suite for via shorthand expansion functionality
# ABOUTME: Tests expanding via shorthand codes to full URLs in munge_link processing
import pytest
from blogmarks.pinboard import expand_via_shorthand, munge_link

class TestViaExpansion:
    """Test via shorthand expansion"""
    
    def test_expand_known_via_shorthands(self):
        """Test expanding known via shorthand codes to full URLs"""
        # Test known mappings
        assert expand_via_shorthand('tbray') == 'https://www.tbray.org/ongoing/'
        assert expand_via_shorthand('migurski') == 'http://mike.teczno.com/notes/'
        assert expand_via_shorthand('skamille') == 'https://www.elidedbranches.com/'
        assert expand_via_shorthand('nelson') == 'https://www.somebits.com/weblog/'
        assert expand_via_shorthand('kottke') == 'https://kottke.org/'
        assert expand_via_shorthand('waxy') == 'https://waxy.org/'
        assert expand_via_shorthand('kottke.org') == 'https://kottke.org/'
        assert expand_via_shorthand('sarah.milstein') == 'https://www.sarahmilstein.com/'
    
    def test_expand_unknown_via_shorthand_returns_original(self):
        """Test that unknown shorthand codes return the original value"""
        assert expand_via_shorthand('unknown') == 'unknown'
        assert expand_via_shorthand('someone.else') == 'someone.else'
        assert expand_via_shorthand('new.person') == 'new.person'
    
    def test_expand_already_expanded_urls(self):
        """Test that already expanded URLs are returned unchanged"""
        assert expand_via_shorthand('https://example.com/') == 'https://example.com/'
        assert expand_via_shorthand('http://test.com/path') == 'http://test.com/path'
        assert expand_via_shorthand('https://simonwillison.net/') == 'https://simonwillison.net/'
    
    def test_expand_handles_none_and_empty(self):
        """Test that None and empty strings are handled gracefully"""
        assert expand_via_shorthand(None) is None
        assert expand_via_shorthand('') == ''

class TestMungeLinkWithViaExpansion:
    """Test munge_link integration with via expansion"""
    
    def test_munge_link_expands_known_via_shorthand(self):
        """Test that munge_link expands known via shorthand to full URL"""
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
    
    def test_munge_link_expands_multiple_known_shorthands(self):
        """Test expansion of various known shorthand codes"""
        test_cases = [
            ('via:migurski', 'http://mike.teczno.com/notes/'),
            ('via:skamille', 'https://www.elidedbranches.com/'),
            ('via:nelson', 'https://www.somebits.com/weblog/'),
            ('via:kottke', 'https://kottke.org/'),
            ('via:waxy', 'https://waxy.org/'),
            ('via:sarah.milstein', 'https://www.sarahmilstein.com/'),
        ]
        
        for via_tag, expected_url in test_cases:
            link = {
                'ts': 1234567890,
                'url': 'https://example.com',
                'description': 'Test link',
                'extended': 'Extended description',
                'tags': f'python {via_tag} coding',
                'hash': 'test123'
            }
            
            result = munge_link(link)
            assert result['via'] == expected_url, f"Failed for {via_tag}"
    
    def test_munge_link_preserves_unknown_via_codes(self):
        """Test that unknown via codes are preserved as-is"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python via:unknown.person coding',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        assert result['via'] == 'unknown.person'
        assert 'via:unknown.person' not in result['tags']
        assert 'python coding' in result['tags']
    
    def test_munge_link_preserves_full_urls_in_via(self):
        """Test that full URLs in via tags are preserved"""
        link = {
            'ts': 1234567890,
            'url': 'https://example.com',
            'description': 'Test link',
            'extended': 'Extended description',
            'tags': 'python via:https://simonwillison.net/ coding',
            'hash': 'test123'
        }
        
        result = munge_link(link)
        
        assert result['via'] == 'https://simonwillison.net/'
        assert 'via:https://simonwillison.net/' not in result['tags']
        assert 'python coding' in result['tags']