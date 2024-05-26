-- :name select_recent :many
select 
        id, ts, url, description, extended, tags, hash
from links
order by ts desc
limit :count;

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
insert or replace into links
    (ts, url, description, extended, tags, hash)
values
    (:ts, :url, :description, :extended, :tags, :hash)


-- :name distinct_year_months :many
select DISTINCT strftime('%Y-%m', ts, 'unixepoch') as year_month from links;

-- :name select_by_year_month :many
SELECT * FROM links WHERE strftime('%Y-%m', ts, 'unixepoch') = :year_month;

-- :name latest_ts :scalar
select max(ts) from links;