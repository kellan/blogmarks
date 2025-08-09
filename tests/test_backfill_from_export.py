# ABOUTME: Test suite for backfilling via fields from Pinboard export data
# ABOUTME: Tests parsing export JSON, filtering mlp+via links, and updating database
import pytest
import tempfile
import os
import sqlite3
import json
from blogmarks import db

@pytest.fixture
def temp_db_with_existing_links():
    """Create a temporary database with some existing links (without via fields populated)"""
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
    db.module()  # Initialize tables
    
    # Insert test links that exist in database but have NULL via field
    conn = sqlite3.connect(temp_path)
    cursor = conn.cursor()
    
    test_links = [
        (1625097038, 'https://example.com/glp1', 'GLP-1 article', 'Extended description', None, 'health glp1 insurance mlp', 'c50fd66774283e2d0a11077fbc7021f3'),
        (1625097039, 'https://example.com/protest', 'Protest article', 'Extended description', None, 'politics us protest mlp', 'hash2'),
        (1625097040, 'https://example.com/ai', 'AI article', 'Extended description', None, 'ai policy llm mlp', 'hash3'),
        (1625097041, 'https://example.com/normal', 'Normal article', 'Extended description', None, 'tech coding', 'hash4'),
    ]
    
    cursor.executemany(
        "INSERT INTO links (ts, url, description, extended, via, tags, hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        test_links
    )
    conn.commit()
    conn.close()
    
    yield temp_path
    
    # Cleanup
    db.module = original_module_func
    os.unlink(temp_path)

@pytest.fixture
def sample_pinboard_export():
    """Sample Pinboard export data matching the format"""
    return [
        {
            "href": "https://example.com/glp1",
            "description": "GLP-1 article", 
            "extended": "Extended description",
            "meta": "5797228aba72ee87517a93188ebdf57f",
            "hash": "c50fd66774283e2d0a11077fbc7021f3",
            "time": "2025-08-09T12:10:38Z",
            "shared": "yes",
            "toread": "no",
            "tags": "health data glp1 insurance mlp via:tbray"
        },
        {
            "href": "https://example.com/protest",
            "description": "Protest article",
            "extended": "Extended description", 
            "meta": "meta2",
            "hash": "hash2",
            "time": "2025-08-08T10:30:00Z",
            "shared": "yes",
            "toread": "no",
            "tags": "mlp politics us protest via:sarah.milstein"
        },
        {
            "href": "https://example.com/ai",
            "description": "AI article",
            "extended": "Extended description",
            "meta": "meta3", 
            "hash": "hash3",
            "time": "2025-08-07T15:20:00Z",
            "shared": "yes",
            "toread": "no",
            "tags": "ai mlp policy llm silicon.valley rodney.brooks via:skamille"
        },
        {
            "href": "https://example.com/no-mlp",
            "description": "No MLP article",
            "extended": "Extended description",
            "meta": "meta4",
            "hash": "hash4", 
            "time": "2025-08-06T09:15:00Z",
            "shared": "yes",
            "toread": "no",
            "tags": "tech coding via:someone"
        },
        {
            "href": "https://example.com/mlp-no-via",
            "description": "MLP but no via",
            "extended": "Extended description",
            "meta": "meta5",
            "hash": "hash5",
            "time": "2025-08-05T14:45:00Z",
            "shared": "yes", 
            "toread": "no",
            "tags": "mlp politics economics"
        }
    ]

class TestPinboardExportParsing:
    """Test parsing of Pinboard export data"""
    
    def test_load_pinboard_export(self, sample_pinboard_export):
        """Test that we can parse Pinboard export format"""
        from blogmarks.backfill_from_export import load_pinboard_export
        
        # Create temp JSON file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(sample_pinboard_export, f)
        
        try:
            links = load_pinboard_export(temp_path)
            assert len(links) == 5
            assert links[0]['href'] == 'https://example.com/glp1'
            assert links[0]['tags'] == 'health data glp1 insurance mlp via:tbray'
        finally:
            os.unlink(temp_path)
    
    def test_filter_mlp_with_via_tags(self, sample_pinboard_export):
        """Test filtering for links that have both 'mlp' and 'via:' tags"""
        from blogmarks.backfill_from_export import filter_mlp_with_via
        
        filtered_links = filter_mlp_with_via(sample_pinboard_export)
        
        assert len(filtered_links) == 3  # First 3 have both mlp and via:
        
        urls = [link['href'] for link in filtered_links]
        assert 'https://example.com/glp1' in urls
        assert 'https://example.com/protest' in urls 
        assert 'https://example.com/ai' in urls
        assert 'https://example.com/no-mlp' not in urls  # no mlp tag
        assert 'https://example.com/mlp-no-via' not in urls  # no via tag
    
    def test_extract_via_from_export_link(self, sample_pinboard_export):
        """Test extracting via value from export link tags"""
        from blogmarks.backfill_from_export import extract_via_from_tags
        
        # Test various via tag formats
        assert extract_via_from_tags("health data glp1 insurance mlp via:tbray") == "tbray"
        assert extract_via_from_tags("mlp politics us protest via:sarah.milstein") == "sarah.milstein"
        assert extract_via_from_tags("ai mlp policy llm via:skamille") == "skamille"
        assert extract_via_from_tags("mlp politics economics") is None  # no via tag

class TestBackfillFromExport:
    """Test backfilling via fields from export data"""
    
    def test_backfill_updates_matching_links(self, temp_db_with_existing_links, sample_pinboard_export):
        """Test that backfill updates links that match by hash"""
        from blogmarks.backfill_from_export import backfill_via_from_export
        
        # Create temp export file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(sample_pinboard_export, f)
        
        try:
            updates_count = backfill_via_from_export(temp_path)
            
            # Should have updated 3 links (the ones with mlp + via: tags)
            assert updates_count == 3
            
            # Check that via fields were updated with expanded URLs
            conn = sqlite3.connect(temp_db_with_existing_links)
            cursor = conn.cursor()
            
            # Check first link - tbray should be expanded
            cursor.execute("SELECT via FROM links WHERE hash = ?", ('c50fd66774283e2d0a11077fbc7021f3',))
            result = cursor.fetchone()
            assert result[0] == 'https://www.tbray.org/ongoing/'
            
            # Check second link - sarah.milstein should be expanded
            cursor.execute("SELECT via FROM links WHERE hash = ?", ('hash2',))
            result = cursor.fetchone()
            assert result[0] == 'https://www.sarahmilstein.com/'
            
            # Check third link - skamille should be expanded
            cursor.execute("SELECT via FROM links WHERE hash = ?", ('hash3',))
            result = cursor.fetchone()
            assert result[0] == 'https://www.elidedbranches.com/'
            
            # Check that non-matching link wasn't touched
            cursor.execute("SELECT via FROM links WHERE hash = ?", ('hash4',))
            result = cursor.fetchone()
            assert result[0] is None
            
            conn.close()
        finally:
            os.unlink(temp_path)
    
    def test_backfill_preserves_other_fields(self, temp_db_with_existing_links, sample_pinboard_export):
        """Test that backfill only changes via field"""
        from blogmarks.backfill_from_export import backfill_via_from_export
        
        # Get original data
        conn = sqlite3.connect(temp_db_with_existing_links)
        cursor = conn.cursor()
        cursor.execute("SELECT ts, url, description, extended, tags FROM links WHERE hash = ?", ('hash2',))
        original_data = cursor.fetchone()
        conn.close()
        
        # Create temp export file and run backfill
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(sample_pinboard_export, f)
        
        try:
            backfill_via_from_export(temp_path)
            
            # Check that other fields are unchanged
            conn = sqlite3.connect(temp_db_with_existing_links)
            cursor = conn.cursor()
            cursor.execute("SELECT ts, url, description, extended, tags FROM links WHERE hash = ?", ('hash2',))
            updated_data = cursor.fetchone()
            conn.close()
            
            assert original_data == updated_data
        finally:
            os.unlink(temp_path)
    
    def test_preview_shows_planned_updates(self, temp_db_with_existing_links, sample_pinboard_export):
        """Test preview function shows what would be updated"""
        from blogmarks.backfill_from_export import preview_backfill_from_export
        
        # Create temp export file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(sample_pinboard_export, f)
        
        try:
            candidates = preview_backfill_from_export(temp_path)
            
            assert len(candidates) == 3
            
            # Check details for one candidate
            glp1_candidate = next(c for c in candidates if c['hash'] == 'c50fd66774283e2d0a11077fbc7021f3')
            assert glp1_candidate['current_via'] is None
            assert glp1_candidate['extracted_via'] == 'https://www.tbray.org/ongoing/'
            assert glp1_candidate['url'] == 'https://example.com/glp1'
        finally:
            os.unlink(temp_path)