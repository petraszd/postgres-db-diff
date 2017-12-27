import argparse
import difflib
import os.path
import subprocess
import sys


def check_database_name(name):
    try:
        out = db_out(name, "SELECT 42")
    except subprocess.CalledProcessError:
        raise argparse.ArgumentTypeError(
            'Can not access DB using psql. Probably it does not exists.'
        )

    if '42' not in out:
        raise argparse.ArgumentTypeError(
            'Unknown problem executing SQL statements using psql. Aborting.'
        )

    return name


def check_diff_directory(name):
    path = os.path.join(name)
    if not os.path.exists(path):
        return name

    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError('It is not a directory')

    if os.listdir(path):
        raise argparse.ArgumentTypeError('Directory must be empty')

    return name


def parser_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('--db1', help='First DB name',
                        type=check_database_name, required=True)
    parser.add_argument('--db2', help='Second DB name',
                        type=check_database_name, required=True)
    parser.add_argument('--tdiff', help='Directory to output tables\'s diffs',
                        type=check_diff_directory, required=False)

    return parser.parse_args()


def db_out(db_name, cmd):
    return subprocess.check_output(
        "psql -d '{}' -c '{}'".format(db_name, cmd), shell=True
    ).decode('utf-8')


def get_db_tables(db_name):
    tables = set()
    for line in db_out(db_name, '\\dt').splitlines():
        elems = line.split()
        if line and elems[0] == 'public':
            if elems[4] == 'table':
                tables.add(elems[2])
    return tables


def update_range(line_range, i):
    if line_range[0] is None:
        line_range[0] = i
        line_range[1] = i + 1
    else:
        line_range[1] = i + 1


def get_table_definition(db_name, table_name):
    lines = db_out(db_name, '\\d "{}"'.format(table_name)).splitlines()
    lines = [x for x in lines if x.strip()]

    columns_range = [None, None]
    indexes_range = [None, None]
    check_constr_range = [None, None]
    foreign_constr_range = [None, None]
    process_constr_range = [None, None]

    S_START = 1
    S_COLUMNS = 2
    S_INDEXES = 3
    S_CHECK_CONSTR = 4
    S_FOREIGN_CONSTR = 5
    S_REFERENCES = 6
    S_END = 7

    def replace_with_sorted(lines, a, b):
        if a is None or b is None:
            return lines
        return lines[:a] + sorted(lines[a:b]) + lines[b:]

    def get_after_columns_state(x):
        if x == 'Indexes:':
            return S_INDEXES
        elif x == 'Check constraints:':
            return S_CHECK_CONSTR
        elif x == 'Foreign-key constraints:':
            return S_FOREIGN_CONSTR
        elif x == 'Referenced by:':
            return S_REFERENCES
        return S_END

    def process_start(i, x):
        if x[0:2] == '--':
            return S_COLUMNS
        return S_START

    def process_columns(i, x):
        if x[0] != ' ':
            return get_after_columns_state(x)
        update_range(columns_range, i)
        return S_COLUMNS

    def process_indexes(i, x):
        if x[0] != ' ':
            return get_after_columns_state(x)
        update_range(indexes_range, i)
        return S_INDEXES

    def process_check_constr(i, x):
        if x[0] != ' ':
            return get_after_columns_state(x)
        update_range(check_constr_range, i)
        return S_CHECK_CONSTR

    def process_foreign_constr(i, x):
        if x[0] != ' ':
            return get_after_columns_state(x)
        update_range(foreign_constr_range, i)
        return S_FOREIGN_CONSTR

    def process_references(i, x):
        if x[0] != ' ':
            return get_after_columns_state(x)
        update_range(process_constr_range, i)
        return S_REFERENCES

    def process_end(i, x):
        return S_END

    processes = {
        S_START: process_start,
        S_COLUMNS: process_columns,
        S_INDEXES: process_indexes,
        S_CHECK_CONSTR: process_check_constr,
        S_FOREIGN_CONSTR: process_foreign_constr,
        S_REFERENCES: process_references,
        S_END: process_end,
    }

    state = S_START
    for i, x in enumerate(lines):
        state = processes[state](i, x)

    lines = replace_with_sorted(lines, *columns_range)
    lines = replace_with_sorted(lines, *indexes_range)
    lines = replace_with_sorted(lines, *check_constr_range)
    lines = replace_with_sorted(lines, *foreign_constr_range)
    lines = replace_with_sorted(lines, *process_constr_range)
    return '\n'.join(lines)


def compare_number_of_tables(db1_tables, db2_tables):
    if db1_tables != db2_tables:
        additional_db1 = db1_tables - db2_tables
        additional_db2 = db2_tables - db1_tables

        if additional_db1:
            print('"{}" has additional tables'.format(options.db1))
            for t in additional_db1:
                print('    {}'.format(t))
            print()

        if additional_db2:
            print('"{}" has additional tables'.format(options.db2))
            for t in additional_db2:
                print('    {}'.format(t))
            print()


def compare_each_table(db1_tables, db2_tables):
    not_matching_tables = []

    for t in sorted(db1_tables & db2_tables):
        t1 = get_table_definition(options.db1, t)
        t2 = get_table_definition(options.db2, t)
        if t1 != t2:
            not_matching_tables.append(t)

            diff = difflib.unified_diff(
                [x + '\n' for x in t1.splitlines()],
                [x + '\n' for x in t2.splitlines()],
                '{}.{}'.format(options.db1, t),
                '{}.{}'.format(options.db2, t),
                n=sys.maxsize
            )

            if options.tdiff:
                if not os.path.exists(options.tdiff):
                    os.mkdir(options.tdiff)
                filepath = os.path.join(options.tdiff, '{}.diff'.format(t))
                with open(filepath, 'w') as f:
                    for diff_line in diff:
                        f.write(diff_line)

    if not_matching_tables:
        print('Not matching tables:')
        for t in not_matching_tables:
            print('    {}'.format(t))


options = parser_arguments()

db1_tables = get_db_tables(options.db1)
db2_tables = get_db_tables(options.db2)

compare_number_of_tables(db1_tables, db2_tables)
compare_each_table(db1_tables, db2_tables)
