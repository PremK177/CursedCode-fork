"""
Local SQLite database adapter implementing the Debug Dojo schema from docs/17-schema.md.
Used when Supabase credentials are not provided or as a local zero-config database.
"""
import sqlite3
import json
import uuid
import os
from typing import Any
from app.core.logging import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "debug_dojo.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS learners (
      id TEXT PRIMARY KEY,
      learner_key TEXT NOT NULL UNIQUE,
      display_name TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      last_active_at TEXT
    );

    CREATE TABLE IF NOT EXISTS concepts (
      id TEXT PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      description TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS challenges (
      id TEXT PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      title TEXT NOT NULL,
      description TEXT NOT NULL DEFAULT '',
      statement TEXT NOT NULL,
      function_signature TEXT NOT NULL DEFAULT '',
      starter_code TEXT NOT NULL,
      difficulty TEXT NOT NULL,
      grade TEXT NOT NULL DEFAULT 'Grade 4',
      estimated_time TEXT NOT NULL DEFAULT '10 min',
      language TEXT NOT NULL DEFAULT 'python',
      is_published INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0,
      example TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS challenge_concepts (
      challenge_id TEXT NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
      concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE RESTRICT,
      is_primary INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (challenge_id, concept_id)
    );

    CREATE TABLE IF NOT EXISTS test_cases (
      id TEXT PRIMARY KEY,
      challenge_id TEXT NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
      visibility TEXT NOT NULL,
      ordinal INTEGER NOT NULL,
      input_payload TEXT NOT NULL,
      expected_output TEXT NOT NULL,
      description TEXT,
      timeout_ms INTEGER NOT NULL DEFAULT 1500,
      UNIQUE (challenge_id, visibility, ordinal)
    );

    CREATE TABLE IF NOT EXISTS mistake_categories (
      id TEXT PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      description TEXT NOT NULL,
      detection_guidance TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS submissions (
      id TEXT PRIMARY KEY,
      public_id TEXT NOT NULL UNIQUE,
      learner_id TEXT NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
      challenge_id TEXT NOT NULL REFERENCES challenges(id) ON DELETE RESTRICT,
      source_code TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued',
      visible_passed INTEGER NOT NULL DEFAULT 0,
      visible_total INTEGER NOT NULL DEFAULT 0,
      hidden_passed INTEGER NOT NULL DEFAULT 0,
      hidden_total INTEGER NOT NULL DEFAULT 0,
      overall_passed INTEGER NOT NULL DEFAULT 0,
      hints_requested INTEGER NOT NULL DEFAULT 0,
      execution_ms INTEGER,
      resource_limit_hit TEXT,
      explanation TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS test_results (
      id TEXT PRIMARY KEY,
      submission_id TEXT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
      test_case_id TEXT NOT NULL REFERENCES test_cases(id) ON DELETE RESTRICT,
      outcome TEXT NOT NULL,
      actual_output TEXT,
      safe_message TEXT,
      duration_ms INTEGER,
      resource_limit_hit TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE (submission_id, test_case_id)
    );

    CREATE TABLE IF NOT EXISTS submission_mistakes (
      submission_id TEXT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
      mistake_category_id TEXT NOT NULL REFERENCES mistake_categories(id) ON DELETE RESTRICT,
      confidence REAL,
      evidence_summary TEXT NOT NULL DEFAULT '',
      detected_by TEXT NOT NULL DEFAULT 'rules',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (submission_id, mistake_category_id)
    );

    CREATE TABLE IF NOT EXISTS challenge_hints (
      id TEXT PRIMARY KEY,
      challenge_id TEXT NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
      mistake_category_id TEXT REFERENCES mistake_categories(id) ON DELETE CASCADE,
      hint_level INTEGER NOT NULL,
      hint_text TEXT NOT NULL,
      is_active INTEGER NOT NULL DEFAULT 1,
      UNIQUE (challenge_id, mistake_category_id, hint_level)
    );

    CREATE TABLE IF NOT EXISTS concept_mastery (
      learner_id TEXT NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
      concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
      mastery_score REAL NOT NULL DEFAULT 0,
      attempts INTEGER NOT NULL DEFAULT 0,
      successful_attempts INTEGER NOT NULL DEFAULT 0,
      independent_successes INTEGER NOT NULL DEFAULT 0,
      last_assessed_at TEXT,
      updated_at TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (learner_id, concept_id)
    );
    """)
    conn.commit()
    conn.close()
    seed_initial_data()


def seed_initial_data():
    conn = get_connection()
    cur = conn.cursor()

    # Clean up legacy unhyphenated challenge slugs if present without submissions
    for old_slug, new_slug in (("countpasses", "count-passes"), ("middlethree", "middle-three")):
        cur.execute("SELECT id FROM challenges WHERE slug = ?", (old_slug,))
        row = cur.fetchone()
        if row:
            old_id = row[0]
            new_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"challenge.{new_slug}"))
            cur.execute("UPDATE submissions SET challenge_id = ? WHERE challenge_id = ?", (new_id, old_id))
            cur.execute("DELETE FROM test_cases WHERE challenge_id = ?", (old_id,))
            cur.execute("DELETE FROM challenge_concepts WHERE challenge_id = ?", (old_id,))
            cur.execute("DELETE FROM challenge_hints WHERE challenge_id = ?", (old_id,))
            cur.execute("DELETE FROM challenges WHERE id = ?", (old_id,))

    # 1. Mistake categories from 17-schema.md & rules.md
    mistakes = [
        ('off_by_one', 'Off-by-one error', 'Loop or index range is one position too short or too long.',
         'Inspect loop bounds and first/last included index; check boundary cases.'),
        ('unhandled_short_input', 'Unhandled short input', 'Empty or too-short input is not handled correctly.',
         'Check empty input and input lengths below the expected minimum.'),
        ('print_not_return', 'Print instead of return', 'The function prints instead of returning the required value.',
         'Compare captured stdout with the required return value.'),
        ('boundary_comparison', 'Boundary comparison', 'A strict comparison is used where an inclusive comparison is required, or vice versa.',
         'Test values exactly on the boundary.'),
        ('mutates_input', 'Mutates input', 'The function changes an input collection when it should preserve it.',
         'Compare input snapshots before and after execution.'),
        ('syntax_or_name_error', 'Syntax or name error', 'Python could not run your code because of a typo, missing colon, or undefined name.',
         'Check syntax and variable names.'),
        ('infinite_loop', 'Runs too long', 'Your code kept running until time ran out.',
         'Check loop termination conditions.'),
        ('hardcoded_values', 'Hard-coded values', 'Your code passes examples by returning literal values rather than the general rule.',
         'Check for literal constants matching visible tests.'),
        ('other_logic_error', 'Logic error', 'Something in the logic is off. Use the explanation and hints to narrow it down.',
         'Fallback for general logic errors.')
    ]
    for slug, name, desc, guidance in mistakes:
        cur.execute("""
            INSERT INTO mistake_categories (id, slug, name, description, detection_guidance)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET name=excluded.name, description=excluded.description
        """, (str(uuid.uuid5(uuid.NAMESPACE_DNS, f"mistake.{slug}")), slug, name, desc, guidance))

    # 2. Concepts matching frontend and rules.md
    concepts = [
        ('lists', 'Lists', 'Indexing, slicing, and collection behavior'),
        ('loops', 'Loops', 'Iteration and loop boundaries'),
        ('strings', 'Strings', 'String manipulation and formatting'),
        ('slicing', 'Slicing', 'Sequence slicing and step intervals'),
        ('indexing', 'Indexing', 'Array/string index addressing'),
        ('comparison', 'Comparison', 'Relational operators and edge thresholds')
    ]
    concept_map = {}
    for slug, name, desc in concepts:
        cid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"concept.{slug}"))
        concept_map[slug] = cid
        cur.execute("""
            INSERT INTO concepts (id, slug, name, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET name=excluded.name, description=excluded.description
        """, (cid, slug, name, desc))

    # 3. Seed 12 challenges with visible & hidden tests, concepts and hint ladders
    from app.integrations.seed_challenges import SEED_CHALLENGES
    for idx, c in enumerate(SEED_CHALLENGES):
        cid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"challenge.{c['id']}"))
        cur.execute("""
            INSERT INTO challenges (id, slug, title, description, statement, function_signature, starter_code,
                                    difficulty, grade, estimated_time, language, is_published, sort_order, example)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'python', 1, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                statement=excluded.statement,
                function_signature=excluded.function_signature,
                starter_code=excluded.starter_code,
                difficulty=excluded.difficulty,
                grade=excluded.grade,
                estimated_time=excluded.estimated_time,
                sort_order=excluded.sort_order,
                example=excluded.example
        """, (
            cid, c['id'], c['title'], c.get('description', ''), c['statement'],
            c.get('function_signature', ''), c['starterCode'],
            c['difficulty'], c['grade'], c.get('estimatedTime', '10 min'),
            idx + 1, json.dumps(c.get('example', {}))
        ))

        # Concepts mapping
        for tag in c.get('tags', []):
            tag_slug = tag.lower()
            if tag_slug in concept_map:
                cur.execute("""
                    INSERT INTO challenge_concepts (challenge_id, concept_id, is_primary)
                    VALUES (?, ?, 1)
                    ON CONFLICT(challenge_id, concept_id) DO NOTHING
                """, (cid, concept_map[tag_slug]))

        # Test cases (ordinal is 1..N within each visibility group, or sequential across challenge)
        ordinal = 1
        for vt in c.get('visibleTests', []):
            t_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.{c['id']}.vis.{ordinal}"))
            cur.execute("""
                INSERT INTO test_cases (id, challenge_id, visibility, ordinal, input_payload, expected_output, description, timeout_ms)
                VALUES (?, ?, 'visible', ?, ?, ?, ?, 1500)
                ON CONFLICT(challenge_id, visibility, ordinal) DO UPDATE SET
                    input_payload=excluded.input_payload,
                    description=excluded.description,
                    expected_output=excluded.expected_output
            """, (t_id, cid, ordinal, json.dumps({"call": vt['call']}), str(vt['expected']), vt['call']))
            ordinal += 1

        for ht in c.get('hiddenTests', []):
            t_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test.{c['id']}.hid.{ordinal}"))
            cur.execute("""
                INSERT INTO test_cases (id, challenge_id, visibility, ordinal, input_payload, expected_output, description, timeout_ms)
                VALUES (?, ?, 'hidden', ?, ?, ?, ?, 1500)
                ON CONFLICT(challenge_id, visibility, ordinal) DO UPDATE SET
                    input_payload=excluded.input_payload,
                    description=excluded.description,
                    expected_output=excluded.expected_output
            """, (t_id, cid, ordinal, json.dumps({"call": ht['call']}), str(ht['expected']), ht['call']))
            ordinal += 1

        # Hints ladder (1 to 4)
        for h_level, h_text in enumerate(c.get('hints', []), start=1):
            h_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"hint.{c['id']}.{h_level}"))
            cur.execute("""
                INSERT INTO challenge_hints (id, challenge_id, mistake_category_id, hint_level, hint_text, is_active)
                VALUES (?, ?, NULL, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET hint_text=excluded.hint_text
            """, (h_id, cid, h_level, h_text))

    conn.commit()
    conn.close()


class QueryResult:
    def __init__(self, data: list[dict] | None = None):
        self.data = data or []


class TableQuery:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_fields = "*"
        self.filters = []  # list of (field, op, val)
        self.order_by_clause = None
        self.limit_val = None
        self._single = False

    def select(self, fields: str = "*"):
        self.select_fields = fields
        return self

    def eq(self, field: str, value: Any):
        self.filters.append((field, "=", value))
        return self

    def is_(self, field: str, value: Any):
        if value is None:
            self.filters.append((field, "IS NULL", None))
        else:
            self.filters.append((field, "=", value))
        return self

    def in_(self, field: str, values: list):
        if not values:
            self.filters.append((field, "IN ()", []))
        else:
            self.filters.append((field, f"IN ({','.join(['?']*len(values))})", list(values)))
        return self

    def order(self, field: str, desc: bool = False):
        self.order_by_clause = f"{field} {'DESC' if desc else 'ASC'}"
        return self

    def limit(self, count: int):
        self.limit_val = count
        return self

    def single(self):
        self._single = True
        self.limit_val = 1
        return self

    def execute(self) -> QueryResult:
        conn = get_connection()
        cur = conn.cursor()

        where_parts = []
        params = []
        for field, op, val in self.filters:
            if op == "IS NULL":
                where_parts.append(f"{field} IS NULL")
            elif op == "IN ()":
                where_parts.append("1=0")
            elif op.startswith("IN ("):
                where_parts.append(f"{field} {op}")
                params.extend(val)
            else:
                where_parts.append(f"{field} = ?")
                params.append(val)

        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
        order_clause = f" ORDER BY {self.order_by_clause}" if self.order_by_clause else ""
        limit_clause = f" LIMIT {self.limit_val}" if self.limit_val else ""

        # Handle nested relation syntax like `concepts(slug, name)`
        clean_select = self.select_fields
        if "concepts(" in clean_select:
            # Join with concepts
            query = f"""
                SELECT cm.mastery_score, cm.concept_id, c.slug, c.name
                FROM concept_mastery cm
                JOIN concepts c ON cm.concept_id = c.id
                {where_clause.replace('learner_id', 'cm.learner_id')}
                {order_clause.replace('mastery_score', 'cm.mastery_score')}
            """
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            data = [
                {
                    "mastery_score": r["mastery_score"],
                    "concept_id": r["concept_id"],
                    "concepts": {"slug": r["slug"], "name": r["name"]}
                }
                for r in rows
            ]
            conn.close()
            return QueryResult(data)

        if "mistake_categories(" in clean_select:
            query = f"""
                SELECT sm.submission_id, mc.slug
                FROM submission_mistakes sm
                JOIN mistake_categories mc ON sm.mistake_category_id = mc.id
                {where_clause.replace('submission_id', 'sm.submission_id')}
            """
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            data = [
                {
                    "submission_id": r["submission_id"],
                    "mistake_categories": {"slug": r["slug"]}
                }
                for r in rows
            ]
            conn.close()
            return QueryResult(data)

        query = f"SELECT {clean_select} FROM {self.table_name}{where_clause}{order_clause}{limit_clause}"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if self._single:
            return QueryResult(rows[0] if rows else None)
        return QueryResult(rows)

class TableInserter:
    def __init__(self, table_name: str, data: dict | list[dict]):
        self.table_name = table_name
        self.data = data

    def execute(self) -> QueryResult:
        conn = get_connection()
        cur = conn.cursor()
        rows_to_insert = self.data if isinstance(self.data, list) else [self.data]
        inserted = []

        for row in rows_to_insert:
            row_dict = dict(row)
            if "id" not in row_dict and self.table_name not in ("concept_mastery", "submission_mistakes", "challenge_concepts"):
                row_dict["id"] = str(uuid.uuid4())
            if self.table_name == "submissions" and "public_id" not in row_dict:
                row_dict["public_id"] = "sub_" + uuid.uuid4().hex[:12]

            cols = list(row_dict.keys())
            placeholders = ", ".join(["?"] * len(cols))
            vals = [
                json.dumps(row_dict[c]) if isinstance(row_dict[c], (list, dict)) else row_dict[c]
                for c in cols
            ]

            query = f"INSERT INTO {self.table_name} ({', '.join(cols)}) VALUES ({placeholders})"
            cur.execute(query, vals)
            inserted.append(row_dict)

        conn.commit()
        conn.close()
        return QueryResult(inserted)


class TableUpdater:
    def __init__(self, table_name: str, data: dict):
        self.table_name = table_name
        self.data = data
        self.filters = []

    def eq(self, field: str, value: Any):
        self.filters.append((field, value))
        return self

    def execute(self) -> QueryResult:
        conn = get_connection()
        cur = conn.cursor()

        set_parts = [f"{k} = ?" for k in self.data.keys()]
        set_vals = list(self.data.values())

        where_parts = [f"{f} = ?" for f, _ in self.filters]
        where_vals = [v for _, v in self.filters]

        query = f"UPDATE {self.table_name} SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}"
        cur.execute(query, set_vals + where_vals)
        conn.commit()

        # Fetch updated row
        cur.execute(f"SELECT * FROM {self.table_name} WHERE {' AND '.join(where_parts)}", where_vals)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return QueryResult(rows)


class LocalDBClient:
    """Mock/SQLite client matching the supabase Client interface."""

    def table(self, table_name: str):
        class TableProxy:
            def __init__(self, name: str):
                self.name = name

            def select(self, fields: str = "*"):
                return TableQuery(self.name).select(fields)

            def insert(self, data: dict | list[dict]):
                return TableInserter(self.name, data)

            def update(self, data: dict):
                return TableUpdater(self.name, data)

        return TableProxy(table_name)

    def rpc(self, func_name: str, params: dict):
        class RpcProxy:
            def __init__(self, fn: str, p: dict):
                self.fn = fn
                self.params = p

            def execute(self) -> QueryResult:
                conn = get_connection()
                cur = conn.cursor()
                if self.fn == "get_recurring_mistakes":
                    # Mistakes appearing in >= 2 distinct challenges
                    learner_id = self.params.get("p_learner_id")
                    query = """
                        SELECT mc.slug, COUNT(DISTINCT s.challenge_id) as challenge_count
                        FROM submission_mistakes sm
                        JOIN submissions s ON sm.submission_id = s.id
                        JOIN mistake_categories mc ON sm.mistake_category_id = mc.id
                        WHERE s.learner_id = ?
                        GROUP BY mc.slug
                        HAVING COUNT(DISTINCT s.challenge_id) >= 2
                    """
                    cur.execute(query, (learner_id,))
                    rows = [dict(r) for r in cur.fetchall()]
                    conn.close()
                    return QueryResult(rows)
                elif self.fn == "increment_hints_requested":
                    sub_id = self.params.get("sub_id")
                    cur.execute("UPDATE submissions SET hints_requested = hints_requested + 1 WHERE id = ?", (sub_id,))
                    conn.commit()
                    conn.close()
                    return QueryResult([{"status": "ok"}])
                conn.close()
                return QueryResult([])

        return RpcProxy(func_name, params)
