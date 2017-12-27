Postgres DB diff
================

Command line tool to compare two PostgreSQL databases. It is based on parsing
``psql`` meta commands output. Such as ``\dt`` for tables and ``\dv`` for
views.

https://www.postgresql.org/docs/current/static/app-psql.html


How to install
==============

There are two options:

1) Use any python package installing tool. Recommended ``pip``.
2) Just copy/paste ``postgresdbdiff.py`` into your dir and run it using ``python postgresdbdiff.py``


Usage
=====

::

  usage: postgresdbdiff.py [-h] --db1 DB1 --db2 DB2 [--diff-folder DIFF_FOLDER]

  optional arguments:
    -h, --help            show this help message and exit
    --db1 DB1             First DB name
    --db2 DB2             Second DB name
    --diff-folder DIFF_FOLDER
                          Directory to output diffs



Example
=======

Create two DBs. One using this SQL:

.. code-block:: sql

  CREATE TABLE table_a (
    id INTEGER PRIMARY KEY,
    test_unique VARCHAR (100) UNIQUE,
    test_not_null VARCHAR (100) NOT NULL,
    test_checks INTEGER NOT NULL
  );

  CREATE TABLE table_b (
    id INTEGER PRIMARY KEY,
    table_a_id integer REFERENCES table_a (id)
  );

  CREATE TABLE table_c (
    id INTEGER PRIMARY KEY
  );

  CREATE VIEW view_a AS SELECT
    id, test_unique, 42 AS some_number
  FROM table_a;

Other using this SQL:

.. code-block:: sql

  CREATE TABLE table_a (
    id INTEGER PRIMARY KEY,
    test_unique VARCHAR (100),
    test_not_null VARCHAR (100),
    test_checks INTEGER NOT NULL CHECK (test_checks > 0)
  );

  CREATE TABLE table_b (
    id INTEGER PRIMARY KEY,
    table_a_no integer REFERENCES table_a (id)
  );

  CREATE VIEW view_a AS SELECT
    id, test_unique
  FROM table_a;

Then run this command ::

  python postgresdbdiff.py --db1 diff_a --db2 diff_b --diff-folder diffs

Output should be like this ::

  TABLES: additional in "diff_a"
    table_c

  TABLES: not matching
    table_a
    table_b

  VIEWS: not matching
    view_a

And there should be the folder named ``diffs`` with files looking like this

.. code-block:: diff

  # diffs/table_a.diff
  --- TABLES.diff_a.table_a
  +++ TABLES.diff_b.table_a
  @@ -1,12 +1,13 @@
                            Table "public.table_a"
       Column     |          Type          | Collation | Nullable | Default
   ---------------+------------------------+-----------+----------+---------
    id            | integer                |           | not null |
    test_checks   | integer                |           | not null |
  - test_not_null | character varying(100) |           | not null |
  + test_not_null | character varying(100) |           |          |
    test_unique   | character varying(100) |           |          |
   Indexes:
       "table_a_pkey" PRIMARY KEY, btree (id)
  -    "table_a_test_unique_key" UNIQUE CONSTRAINT, btree (test_unique)
  +Check constraints:
  +    "table_a_test_checks_check" CHECK (test_checks > 0)
   Referenced by:
  -    TABLE "table_b" CONSTRAINT "table_b_table_a_id_fkey" FOREIGN KEY (table_a_id) REFERENCES table_a(id)
  +    TABLE "table_b" CONSTRAINT "table_b_table_a_no_fkey" FOREIGN KEY (table_a_no) REFERENCES table_a(id)


  # diffs/table_b.diff
  --- TABLES.diff_a.table_b
  +++ TABLES.diff_b.table_b
  @@ -1,9 +1,9 @@
                   Table "public.table_b"
      Column   |  Type   | Collation | Nullable | Default
   ------------+---------+-----------+----------+---------
    id         | integer |           | not null |
  - table_a_id | integer |           |          |
  + table_a_no | integer |           |          |
   Indexes:
       "table_b_pkey" PRIMARY KEY, btree (id)
   Foreign-key constraints:
  -    "table_b_table_a_id_fkey" FOREIGN KEY (table_a_id) REFERENCES table_a(id)
  +    "table_b_table_a_no_fkey" FOREIGN KEY (table_a_no) REFERENCES table_a(id)


  # diffs/view_a.diff
  --- VIEWS.diff_a.view_a
  +++ VIEWS.diff_b.view_a
  @@ -1,6 +1,5 @@
                            View "public.view_a"
      Column    |          Type          | Collation | Nullable | Default
   -------------+------------------------+-----------+----------+---------
    id          | integer                |           |          |
  - some_number | integer                |           |          |
    test_unique | character varying(100) |           |          |
