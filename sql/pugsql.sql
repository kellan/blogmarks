-- :name create_links_tables 
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,  -- seconds since unix epoch
    url TEXT,
    description TEXT,
    extended TEXT,
    tags TEXT,  -- space delimited
    hash TEXT unique)

-- :name upsert_link :insert
insert into links
    (ts, url, description, extended, tags, hash)
values
    (:ts, :url, :description, :extended, :tags, :hash)
on conflict do nothing;