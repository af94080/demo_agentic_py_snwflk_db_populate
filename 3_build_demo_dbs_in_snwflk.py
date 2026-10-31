# This program is an AI helper that builds demo databases in Snowflake for you.
# You tell it in plain English what kind of databases you want (for example, a retail one).
# It then creates each database, adds tables, and fills them with realistic sample data.

import os
import re
import json
import snowflake.connector
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

# What this program does:
# - Takes a plain-English request and lets ChatGPT decide which steps to take.
# - Carries out those steps in Snowflake, always naming databases starting with "demo_oct_31".
# - Repeats until the work is done, then reports a summary.
# Example: asking for "a retail sales database" creates DEMO_OCT_31_SALES with
# tables like customers, products, and orders, each holding about 10-20 sample rows.

client = OpenAI()

PREFIX = "demo_oct_31"


def connect(database=None):
    # Logs in to Snowflake using your saved credentials, using the limited demo role.
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role="DEMO_AGENT_ROLE",
        warehouse="COMPUTE_WH",
        database=database,
    )


# ---------- Tools ----------

def _full_name(name: str) -> str:
    # Cleans up a database name and makes sure it always starts with "demo_oct_31".
    name = re.sub(r"[^a-z0-9_]", "_", name.lower())
    if not name.startswith(PREFIX):
        name = f"{PREFIX}_{name}"
    return name.upper()


def create_database(name: str) -> str:
    # Creates a new, empty demo database with the correct name prefix.
    db = _full_name(name)
    conn = connect()
    try:
        conn.cursor().execute(f"CREATE DATABASE {db}")
    finally:
        conn.close()
    return f"Created database {db}"


def run_sql(database: str, statement: str) -> str:
    # Carries out one instruction inside a demo database, like adding a table or some data.
    db = _full_name(database)
    conn = connect(database=db)
    try:
        cur = conn.cursor()
        cur.execute(statement)  # one statement per call
        if cur.description:
            return json.dumps(cur.fetchmany(20), default=str)
        return "OK"
    finally:
        conn.close()


def list_demo_databases() -> str:
    # Shows which demo databases already exist so nothing gets duplicated.
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(f"SHOW DATABASES LIKE '{PREFIX.upper()}%'")
        return json.dumps([row[1] for row in cur.fetchall()])  # column 2 = name
    finally:
        conn.close()


TOOL_FUNCS = {
    "create_database": create_database,
    "run_sql": run_sql,
    "list_demo_databases": list_demo_databases,
}

tools = [
    {"type": "function", "function": {
        "name": "create_database",
        "description": f"Create a new Snowflake database. The '{PREFIX}_' prefix is added automatically.",
        "parameters": {"type": "object",
                       "properties": {"name": {"type": "string", "description": "Short name, e.g. 'sales'"}},
                       "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "run_sql",
        "description": ("Run ONE Snowflake SQL statement in a demo database "
                        "(CREATE TABLE, INSERT, SELECT). Tables go in the PUBLIC schema. "
                        "Do not send multiple statements in one call."),
        "parameters": {"type": "object",
                       "properties": {"database": {"type": "string"},
                                      "statement": {"type": "string"}},
                       "required": ["database", "statement"]}}},
    {"type": "function", "function": {
        "name": "list_demo_databases",
        "description": "List existing demo databases.",
        "parameters": {"type": "object", "properties": {}}}},
]

SYSTEM = (
    f"You build demo databases in Snowflake. Every database name starts with '{PREFIX}'. "
    "For each database: create it, create 2-4 related tables in the PUBLIC schema, "
    "and insert 10-20 realistic rows per table using one multi-row INSERT per table. "
    "Use simple unquoted UPPER_SNAKE_CASE names for tables and columns (e.g. PRODUCT_ID). "
    "Never use double quotes around identifiers. Verify with a SELECT, then summarize."
    "Each table MUST have at least 10 rows. After inserting, run SELECT COUNT(*) on each table, "
    "and if any table has fewer than 10 rows, insert more before summarizing. "
)


# ---------- Agent loop ----------

def run_agent(task: str, max_steps: int = 25):
    # Takes your request, lets ChatGPT work through the steps one by one, and returns a final summary.
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]

    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=tools
        )
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            try:
                result = TOOL_FUNCS[call.function.name](**args)
            except Exception as e:
                result = f"ERROR: {e}"
            print(f"-> {call.function.name}({args}) = {result[:100]}")
            messages.append({"role": "tool",
                             "tool_call_id": call.id,
                             "content": result})
    return "Stopped: hit max steps."


if __name__ == "__main__":
    print(run_agent("Build three demo databases: a retail sales one, "
                    "a hospital scheduling one, and a cell phone usage by countries in south america one."))
