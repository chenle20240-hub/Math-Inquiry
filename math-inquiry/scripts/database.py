"""Build V1.1 from its explicit-ID JSONL records; never replace an existing file."""
import argparse
from collections import Counter
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile

SCHEMA = Path(__file__).with_name("schema_v11.sql")
DIRECT = "books chapters sections structure concepts examples relationships occurrences issues".split()
EXAMS = ["exam_papers", "exam_questions", "exam_knowledge_links"]


def readonly(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def packed(value):
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value


def book_path(value):
    return "textbooks/" + value.replace("\\", "/").rsplit("/", 1)[-1]


def load_table(db, dataset, table):
    columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
    params = ",".join("?" for _ in columns)
    with (dataset / (table + ".jsonl")).open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
                if table in DIRECT and set(record) - set(columns):
                    raise ValueError("schema 未登记字段")
                values = []
                for key in columns:
                    if table == "books" and key == "source_file":
                        value = book_path(record[key])
                    elif key == "payload":
                        value = record
                    elif key == "number_count":
                        value = record["question_count"]
                    else:
                        value = record.get(key) if table in DIRECT else record[key]
                    values.append(packed(value))
                db.execute(f"INSERT INTO {table} VALUES ({params})", values)
            except (KeyError, ValueError, sqlite3.Error) as error:
                raise ValueError(f"{table}:{lineno}: {error}") from error


def check(db):
    if db.execute("pragma integrity_check").fetchall() != [("ok",)] or db.execute("pragma foreign_key_check").fetchall():
        raise ValueError("完整性或外键错误")


def compare(db, original):
    def objects(conn):
        return dict(conn.execute("SELECT name,type FROM sqlite_schema WHERE type IN ('table','view')"))
    expected = objects(original)
    if expected != objects(db):
        raise ValueError("表或视图集合不一致")
    counts = {}
    for name in expected:
        query = f'SELECT * FROM "{name}"'
        source = original.execute(query)
        pos = [field[0] for field in source.description].index("source_file") if name == "books" else None
        rows = Counter(tuple(book_path(value) if idx == pos else value for idx, value in enumerate(row)) for row in source)
        if rows != Counter(db.execute(query)):
            raise ValueError("与基线不符（全列、重复数或身份）: " + name)
        counts[name] = sum(rows.values())
    return counts


def build(dataset, output, baseline=None):
    dataset, output = dataset.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(dataset):
        raise ValueError("请在数据目录外指定尚不存在的输出文件")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tempdir:
        temp = Path(tempdir) / "candidate.sqlite"
        with closing(sqlite3.connect(temp)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA.read_text(encoding="utf-8"))
            with db:
                for name in DIRECT + EXAMS:
                    load_table(db, dataset, name)
                db.execute("INSERT INTO example_concepts SELECT example_id,j.value FROM examples,json_each(knowledge_ids) j")
                db.execute("INSERT INTO concept_topics SELECT knowledge_id,j.value FROM concepts,json_each(topics) j")
            check(db)
            counts = {}
            if baseline:
                with closing(readonly(baseline)) as original:
                    check(original)
                    counts = compare(db, original)
        os.link(temp, output)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="V1.1 data directory")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="compare all tables and views before publishing")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.dataset, args.output, args.baseline), ensure_ascii=False))
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"未生成数据库：{error}\n")
