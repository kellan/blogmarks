# ABOUTME: Backfill via fields from Pinboard export JSON data
# ABOUTME: Parse export, find mlp+via links, update database via field by matching hash
import json
from . import db
from .pinboard import expand_via_shorthand

def load_pinboard_export(file_path):
    """
    Load and parse Pinboard export JSON file.
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def filter_mlp_with_via(export_links):
    """
    Filter links that have both 'mlp' and 'via:' tags.
    """
    filtered = []
    for link in export_links:
        tags = link.get('tags', '')
        if 'mlp' in tags.split() and 'via:' in tags:
            filtered.append(link)
    return filtered

def extract_via_from_tags(tags_string):
    """
    Extract via value from tags string.
    Returns the value after 'via:' or None if no via tag found.
    """
    if not tags_string:
        return None
    
    tags = tags_string.split()
    for tag in tags:
        if tag.startswith('via:'):
            return tag[4:]  # Remove 'via:' prefix
    
    return None

def backfill_via_from_export(export_file_path):
    """
    Backfill via fields from Pinboard export data.
    Matches links by hash and updates via field only.
    """
    print(f"Loading Pinboard export from {export_file_path}...")
    export_links = load_pinboard_export(export_file_path)
    
    print(f"Filtering for mlp links with via tags...")
    mlp_via_links = filter_mlp_with_via(export_links)
    print(f"Found {len(mlp_via_links)} mlp links with via tags")
    
    updates_made = 0
    queries = db.module()
    
    for export_link in mlp_via_links:
        hash_value = export_link.get('hash')
        if not hash_value:
            continue
            
        via_value = extract_via_from_tags(export_link.get('tags', ''))
        if not via_value:
            continue
        
        # Expand via shorthand to full URL
        expanded_via = expand_via_shorthand(via_value)
        
        # Find matching link in database by hash
        db_links = list(queries.select_recent(count=10000))  # Get all links
        matching_link = None
        for db_link in db_links:
            if db_link.get('hash') == hash_value:
                matching_link = db_link
                break
        
        if matching_link:
            print(f"Updating via field for {matching_link['url']} (hash: {hash_value}) -> via: {expanded_via}")
            update_via_field_by_hash(hash_value, expanded_via)
            updates_made += 1
        else:
            print(f"No matching link found for hash: {hash_value}")
    
    print(f"Backfill complete. Updated {updates_made} links with via fields.")
    return updates_made

def update_via_field_by_hash(hash_value, via_value):
    """
    Update via field for link with specific hash.
    """
    queries = db.module()
    
    # Use raw SQL to update only the via field
    connection = queries.engine.raw_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute("UPDATE links SET via = ? WHERE hash = ?", (via_value, hash_value))
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def preview_backfill_from_export(export_file_path):
    """
    Preview what would be updated without making changes.
    """
    print(f"Preview of backfill from {export_file_path}")
    
    export_links = load_pinboard_export(export_file_path)
    mlp_via_links = filter_mlp_with_via(export_links)
    
    candidates = []
    queries = db.module()
    db_links = list(queries.select_recent(count=10000))
    
    # Create hash lookup for faster matching
    db_links_by_hash = {link.get('hash'): link for link in db_links if link.get('hash')}
    
    for export_link in mlp_via_links:
        hash_value = export_link.get('hash')
        if not hash_value:
            continue
            
        via_value = extract_via_from_tags(export_link.get('tags', ''))
        if not via_value:
            continue
        
        # Expand via shorthand to full URL
        expanded_via = expand_via_shorthand(via_value)
            
        matching_db_link = db_links_by_hash.get(hash_value)
        if matching_db_link:
            candidates.append({
                'hash': hash_value,
                'url': matching_db_link['url'],
                'current_via': matching_db_link.get('via'),
                'extracted_via': expanded_via,
                'export_tags': export_link.get('tags', ''),
                'db_tags': matching_db_link.get('tags', '')
            })
    
    print(f"Found {len(candidates)} links that would be updated:")
    for candidate in candidates[:10]:  # Show first 10
        print(f"  Hash {candidate['hash']}: {candidate['url']}")
        print(f"    Current via: {candidate['current_via']}")
        print(f"    Would set via: {candidate['extracted_via']}")
        print(f"    Export tags: {candidate['export_tags']}")
        print(f"    DB tags: {candidate['db_tags']}")
        print()
    
    if len(candidates) > 10:
        print(f"... and {len(candidates) - 10} more")
    
    return candidates

def main():
    """
    Main function - preview first, then ask for confirmation before updating.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m blogmarks.backfill_from_export --preview <export.json>")
        print("  python -m blogmarks.backfill_from_export --execute <export.json>")
        return
    
    if sys.argv[1] == '--preview' and len(sys.argv) > 2:
        preview_backfill_from_export(sys.argv[2])
    elif sys.argv[1] == '--execute' and len(sys.argv) > 2:
        backfill_via_from_export(sys.argv[2])
    else:
        print("Invalid arguments. Use --preview or --execute followed by JSON file path.")

if __name__ == '__main__':
    main()