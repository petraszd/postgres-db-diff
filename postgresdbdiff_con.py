#!/usr/bin/env python

# If you are reading this code and thinking: why this file have not been
# split into smaller and easier to read modules? The answer is quite simple:
# I want users to be able just copy/paste this file and run it
import argparse
import difflib
import os.path
import subprocess
import sys


def check_database_name(name):
    try:
        out = db_out(name, "SELECT 42", stderr=None)
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
    parser.add_argument('--schema1', help='First schema name',
                        required=True)
    parser.add_argument('--db2', help='Second DB name',
                        type=check_database_name, required=True)
    parser.add_argument('--schema2', help='Second schema name',
                        required=True)
    parser.add_argument('--diff-folder',
                        help='Directory to output diffs',
                        type=check_diff_directory, required=False)
    parser.add_argument('--rowcount',
                        help='Compare tables row count',
                        action='store_true')

    return parser.parse_args()


def db_out(url, cmd, stderr=subprocess.STDOUT):
    return subprocess.check_output(
        'psql -c "{0}" {1}'.format(cmd, url), shell=True, stderr=stderr
    ).decode('utf-8')


def get_table_rowcount(url, schema, table_name, stderr=subprocess.STDOUT):
    cmd = 'select count(1) from "{0}.{1}";'.format(schema, table_name)
    output = subprocess.check_output(
        'psql -c "{0}" --quiet --tuples-only {1}'.format(cmd, url), shell=True, stderr=stderr
    ).decode('utf-8')
    return int(output.strip())


def get_db_tables(db_name, schema):
    tables = set()
    for line in db_out(db_name, '\\dt {0}.*'.format(schema)).splitlines():
        elems = line.split()
        if line and elems[0] == str(schema):
            tables.add(elems[2])
    return tables


def get_db_views(db_name, schema):
    views = set()
    for line in db_out(db_name, '\\dv {0}.*'.format(schema)).splitlines():
        elems = line.split()
        if line and elems[0] == str(schema):
            views.add(elems[2])
    return views


def get_db_mat_views(db_name, schema):
    views = set()
    for line in db_out(db_name, '\\dmv {0}.*'.format(schema)).splitlines():
        elems = line.split()
        if line and elems[0] == str(schema):
            views.add(elems[2])
    return views


def get_table_definition(db_name, schema, table_name):
    ## lines = db_out(db_name, '\\d {0}.{1}'.format(schema,table_name)).splitlines()
    temps = db_out(db_name, '\\d {0}.{1}'.format(schema,table_name)).splitlines()
    lines = []
    for line in temps:
        line = line.replace(schema + '.', '')
        if re.match(r'.*tablespace ".*".*', line):
            line = re.sub(r'(.*tablespace ").*(".*)',r'\1\2',line)
        if re.match(r'.*Tablespace: ".*".*', line):
            line = re.sub(r'(.*Tablespace: ").*(".*)',r'\1\2',line)
        if re.match(r'.*Table ".*".*', line):
            line = line.strip()
        lines.append(line)
    lines = [x for x in lines if x.strip()]

    print(f"get_table_definition: {schema}.{table_name}")
    
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

    def update_range(line_range, i):
        if line_range[0] is None:
            line_range[0] = i
            line_range[1] = i + 1
        else:
            line_range[1] = i + 1

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


def compare_number_of_items(options, db1_items, db2_items, items_name):
    if db1_items != db2_items:
        additional_db1 = db1_items - db2_items
        additional_db2 = db2_items - db1_items

        if additional_db1:
            sys.stdout.write(
                '{0}: additional in "{1}"\n'.format(items_name, options.db1)
            )
            for t in additional_db1:
                sys.stdout.write('\t{0}\n'.format(t))
            sys.stdout.write('\n')

        if additional_db2:
            sys.stdout.write(
                '{0}: additional in "{1}"\n'.format(items_name, options.db2)
            )
            for t in additional_db2:
                sys.stdout.write('\t{0}\n'.format(t))
            sys.stdout.write('\n')


# TODO: Using same function to compare tables and views. It is not very suited
# for views. But I do not see any clear way to have cleaner interface
def compare_each_table(options, db1_tables, db2_tables, items_name):
    not_matching_tables = []
    not_matching_rowcount = []

    for t in sorted(db1_tables & db2_tables):
        t1 = get_table_definition(options.db1, options.schema1, t)
        t2 = get_table_definition(options.db2, options.schema2, t)
        if t1 != t2:
            not_matching_tables.append(t)

            diff = difflib.unified_diff(
                [x + '\n' for x in t1.splitlines()],
                [x + '\n' for x in t2.splitlines()],
                '{0}.{1}.{2}'.format(items_name, options.db1, t),
                '{0}.{1}.{2}'.format(items_name, options.db2, t),
                n=sys.maxsize
            )

            if options.diff_folder:
                if not os.path.exists(options.diff_folder):
                    os.mkdir(options.diff_folder)
                filepath = os.path.join(
                    options.diff_folder, '{0}.diff'.format(t)
                )
                with open(filepath, 'w') as f:
                    for diff_line in diff:
                        f.write(diff_line)

        elif options.rowcount:
            t1_rowcount = get_table_rowcount(options.db1, options.schema1, t)
            t2_rowcount = get_table_rowcount(options.db2, options.schema2, t)
            if t1_rowcount != t2_rowcount:
                not_matching_rowcount.append('{0} ({1} != {2})'.format(t, t1_rowcount, t2_rowcount))

    if not_matching_tables:
        sys.stdout.write('{0}: not matching\n'.format(items_name))
        for t in not_matching_tables:
            sys.stdout.write('\t{0}\n'.format(t))
        sys.stdout.write('\n')

    if not_matching_rowcount:
        sys.stdout.write('{0}: not matching rowcount\n'.format(items_name))
        for t in not_matching_rowcount:
            sys.stdout.write('\t{0}\n'.format(t))
        sys.stdout.write('\n')


def main():
    options = parser_arguments()

    db1_tables = get_db_tables(options.db1, options.schema1)
    db2_tables = get_db_tables(options.db2, options.schema2)

    compare_number_of_items(options, db1_tables, db2_tables, 'TABLES')
    compare_each_table(options, db1_tables, db2_tables, 'TABLES')

    db1_views = get_db_views(options.db1, options.schema1)
    db2_views = get_db_views(options.db2, options.schema2)
    compare_number_of_items(options, db1_views, db2_views, 'VIEWS')
    compare_each_table(options, db1_views, db2_views, 'VIEWS')
    
    db1_views = get_db_mat_views(options.db1, options.schema1)
    db2_views = get_db_mat_views(options.db2, options.schema2)
    compare_number_of_items(options, db1_views, db2_views, 'MATERIALIZED VIEWS')
    compare_each_table(options, db1_views, db2_views, 'MATERIALIZED VIEWS')


if __name__ == "__main__":
    main()
