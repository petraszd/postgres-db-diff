import difflib
import os.path
import subprocess
import sys


db1_name = sys.argv[1]
db2_name = sys.argv[2]
out_dir = sys.argv[3]


def db_out(db_name, cmd):
    return subprocess.check_output(
        "psql -d '{}' -c '{}'".format(db_name, cmd), shell=True
    )


def get_db_objects(db_name):
    tables = []
    sequences = []
    for line in db_out(db_name, '\\d').splitlines():
        elems = line.split()
        if line and elems[0] == 'public':
            if elems[4] == 'table':
                tables.append(elems[2])
            elif elems[4] == 'sequence':
                sequences.append(elems[2])
    return set(tables), set(sequences)


def replace_with_sorted(lines, a, b):
    if a is None or b is None:
        return lines
    return lines[:a] + sorted(lines[a:b]) + lines[b:]


S_START = 1
S_COLUMNS = 2
S_INDEXES = 3
S_CHECK_CONSTR = 4
S_FOREIGN_CONSTR = 5
S_REFERENCES = 6
S_END = 7


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


def get_table_definition(db_name, table_name):
    lines = db_out(db_name, '\\d "{}"'.format(table_name)).splitlines()
    lines = [x for x in lines if x.strip()]

    columns_range = [None, None]
    indexes_range = [None, None]
    check_constr_range = [None, None]
    foreign_constr_range = [None, None]
    process_constr_range = [None, None]

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


db1_tables, db1_sequences = get_db_objects(db1_name)
db2_tables, db2_sequences = get_db_objects(db2_name)


def compare_number_of_tables():
    if db1_tables != db2_tables:
        additional_db1 = db1_tables - db2_tables
        additional_db2 = db2_tables - db1_tables

        if additional_db1:
            # TODO: use stdout ?
            print('"{}" has additional tables'.format(db1_name))
            for t in additional_db1:
                print('    {}'.format(t))
            print()

        if additional_db2:
            print('"{}" has additional tables'.format(db2_name))
            for t in additional_db2:
                print('    {}'.format(t))
            print()


def compare_each_table():
    not_matching_tables = []

    for t in sorted(db1_tables & db2_tables):
        t1 = get_table_definition(db1_name, t)
        t2 = get_table_definition(db2_name, t)
        if t1 != t2:
            not_matching_tables.append(t)

            diff = difflib.unified_diff(
                [x + '\n' for x in t1.splitlines()],
                [x + '\n' for x in t2.splitlines()],
                '{}.{}'.format(db1_name, t),
                '{}.{}'.format(db2_name, t),
                n=10000  # TODO: max int
            )

            with open(os.path.join(out_dir, '{}.diff'.format(t)), 'w') as f:
                for diff_line in diff:
                    f.write(diff_line)

    if not_matching_tables:
        print('Not matching tables:')
        for t in not_matching_tables:
            print('    {}'.format(t))  # TODO: use stdout ?


compare_number_of_tables()
compare_each_table()
