-- :name select_recent :many
select 
        id, ts, url, description, extended, via, tags, hash
from links
order by ts desc
limit :count;

-- :name create_links_tables 
create table if not exists links (
    id integer primary key autoincrement,
    ts integer,  -- seconds since unix epoch
    url text,
    description text,
    extended text,
    via text,
    tags text,  -- space delimited
    hash text unique)

-- :name upsert_link :insert
insert or replace into links
    (ts, url, description, extended, via, tags, hash)
values
    (:ts, :url, :description, :extended, :via, :tags, :hash)


-- :name distinct_year_months :many
select distinct strftime('%Y-%m', ts, 'unixepoch') as year_month from links;

-- :name select_by_year_month :many
select * from links where strftime('%Y-%m', ts, 'unixepoch') = :year_month;

-- :name latest_ts :scalar
select max(ts) from links;