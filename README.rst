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
2) Just copy/paste ``postgresdbdiff.py`` into your dir and run it using
``python postgresdbdiff.py``


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

.. code-block:: diff
