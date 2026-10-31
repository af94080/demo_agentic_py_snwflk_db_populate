# This program checks the quality of the demo databases built by build_demo_dbs.py.
# It looks at every database starting with "demo_oct_31" and reports PASS, WARN or FAIL.
# Usage: python3 -u check_demo_dbs.py 2>&1 | tee -a check_demo_dbs_log.txt

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

# What this program checks:
# - Each database has 2-4 tables, and each table has 10-20 rows.
# - No empty columns, blank text, or duplicate rows (a PASS line is printed when clean).
# - The first column of each table (the ID) is unique and never empty.
# - Columns that point to another table's ID (like CUSTOMER_ID) match a real row there.
# Example: DEMO_OCT_31_SALES.PUBLIC.ORDERS has CUSTOMER_ID = 99 but no customer 99 exists -> FAIL.

PREFIX = "demo_oct_31"
MIN_TABLES, MAX_TABLES = 2, 4
MIN_ROWS, MAX_ROWS = 10, 20

TEXT_TYPES = {"TEXT", "VARCHAR", "STRING", "CHAR"}

results = {"PASS": 0, "WARN": 0, "FAIL": 0}


def connect():
    # Logs in to Snowflake using your saved credentials, using the limited demo role.
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role="DEMO_AGENT_ROLE",
        warehouse="COMPUTE_WH",
    )


def report(status, where, message):
    # Prints one result line and keeps count of how many passed, warned, or failed.
    results[status] += 1
    print(f"[{status}] {where}: {message}")


def fetch(cur, sql):
    # Runs a question against Snowflake and returns all the answers.
    cur.execute(sql)
    return cur.fetchall()


def check_table(cur, db, table, all_tables):
    # Runs every quality check on one table and reports what it finds.
    where = f"{db}.{table}"
    full = f'{db}."PUBLIC"."{table}"'

    cols = fetch(cur, f"""SELECT COLUMN_NAME, DATA_TYPE
                          FROM {db}.INFORMATION_SCHEMA.COLUMNS
                          WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = '{table}'
                          ORDER BY ORDINAL_POSITION""")

    # Row count
    rows = fetch(cur, f"SELECT COUNT(*) FROM {full}")[0][0]
    if rows == 0:
        report("FAIL", where, "table is empty")
        return
    if MIN_ROWS <= rows <= MAX_ROWS:
        report("PASS", where, f"{rows} rows (expected {MIN_ROWS}-{MAX_ROWS})")
    else:
        report("WARN", where, f"{rows} rows (expected {MIN_ROWS}-{MAX_ROWS})")

    # Empty values and blank text, column by column
    empty_found = False
    blank_found = False
    text_columns = 0
    for name, dtype in cols:
        nulls = fetch(cur, f'SELECT COUNT_IF("{name}" IS NULL) FROM {full}')[0][0]
        if nulls:
            empty_found = True
            report("WARN", where, f"column {name} has {nulls} empty values")
        if dtype.upper() in TEXT_TYPES:
            text_columns += 1
            blanks = fetch(cur, f"""SELECT COUNT_IF(TRIM("{name}") = '') FROM {full}""")[0][0]
            if blanks:
                blank_found = True
                report("WARN", where, f"column {name} has {blanks} blank text values")
    if not empty_found:
        report("PASS", where, f"no empty values in any of the {len(cols)} columns")
    if text_columns and not blank_found:
        report("PASS", where, f"no blank text in any of the {text_columns} text columns")

    # Duplicate rows
    distinct = fetch(cur, f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {full})")[0][0]
    if distinct < rows:
        report("WARN", where, f"{rows - distinct} duplicate rows")
    else:
        report("PASS", where, "no duplicate rows")

    # First column should be a unique, non-empty ID
    key = cols[0][0]
    total, non_null, uniq = fetch(
        cur, f'SELECT COUNT(*), COUNT("{key}"), COUNT(DISTINCT "{key}") FROM {full}')[0]
    if non_null < total or uniq < non_null:
        report("FAIL", where, f"ID column {key} has empty or repeated values")
    else:
        report("PASS", where, f"ID column {key} is unique and never empty")

    # Columns that point to another table's ID must match a real row
    for name, _ in cols[1:]:
        for other, other_key in all_tables.items():
            if other != table and name == other_key:
                orphans = fetch(cur, f"""SELECT COUNT(*) FROM {full}
                                         WHERE "{name}" IS NOT NULL AND "{name}" NOT IN
                                         (SELECT "{other_key}" FROM {db}."PUBLIC"."{other}")""")[0][0]
                if orphans:
                    report("FAIL", where, f"{orphans} rows in {name} match nothing in {other}")
                else:
                    report("PASS", where, f"every {name} matches a row in {other}")


def check_database(cur, db):
    # Checks the table count for one database, then checks each table inside it.
    print(f"\n=== {db} ===")
    tables = [r[0] for r in fetch(cur, f"""SELECT TABLE_NAME FROM {db}.INFORMATION_SCHEMA.TABLES
                                           WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_TYPE = 'BASE TABLE'
                                           ORDER BY TABLE_NAME""")]
    if MIN_TABLES <= len(tables) <= MAX_TABLES:
        report("PASS", db, f"{len(tables)} tables (expected {MIN_TABLES}-{MAX_TABLES})")
    else:
        report("WARN", db, f"{len(tables)} tables (expected {MIN_TABLES}-{MAX_TABLES})")

    # Remember each table's first column so we can look for matching links between tables
    first_cols = {}
    for t in tables:
        first_cols[t] = fetch(cur, f"""SELECT COLUMN_NAME FROM {db}.INFORMATION_SCHEMA.COLUMNS
                                       WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = '{t}'
                                       ORDER BY ORDINAL_POSITION LIMIT 1""")[0][0]

    for t in tables:
        try:
            check_table(cur, db, t, first_cols)
        except Exception as e:
            report("FAIL", f"{db}.{t}", f"check could not run: {e}")


def main():
    # Finds all the demo databases, checks each one, and prints a final scorecard.
    conn = connect()
    try:
        cur = conn.cursor()
        dbs = [r[1] for r in fetch(cur, f"SHOW DATABASES LIKE '{PREFIX.upper()}%'")]
        if not dbs:
            print("No demo databases found.")
            sys.exit(1)
        for db in dbs:
            check_database(cur, db)
    finally:
        conn.close()

    print(f"\nSUMMARY: {results['PASS']} passed, {results['WARN']} warnings, {results['FAIL']} failed")
    sys.exit(1 if results["FAIL"] else 0)


if __name__ == "__main__":
    main()