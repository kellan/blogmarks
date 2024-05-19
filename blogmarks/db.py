import sqlite3
import pugsql, pugsql.compiler

def module():
    queries = pugsql.module('sql/')
    queries.connect('sqlite:///data.db')
    queries.create_links_tables()
    return queries

def insert_link(link):
    queries = module()
    return queries.upsert_link(**link)

if __name__ == '__main__':
   print("Hello world")
   queries = module()
