"""V1.1 research database: one JSON object per matching row, read-only."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys

DEFAULT = Path(__file__).resolve().parents[1] / "database/math_kb.sqlite"
QUERIES = {
    "chapter": "SELECT * FROM chapter_concepts WHERE chapter_id=?",
    "concept": "SELECT knowledge_id,name,definition,formulas,conditions,source_status,source_book,source_pages FROM concepts WHERE name LIKE ?",
    "prerequisites": "SELECT p.* FROM prerequisites p JOIN concepts c USING(knowledge_id) WHERE c.name=?",
    "example": "SELECT e.*, (SELECT group_concat(c.name,'、') FROM example_concepts m JOIN concepts c USING(knowledge_id) WHERE m.example_id=e.example_id) mapped_concepts FROM examples e WHERE example_id=?",
    "examples": """SELECT e.example_id,e.source_book,e.printed_page,e.pdf_page,e.original_label,e.problem_text,
        e.answer,e.extraction_status,e.evidence_images FROM examples e JOIN example_concepts m USING(example_id)
        JOIN concepts c ON c.knowledge_id=m.knowledge_id WHERE c.name=? AND e.source_type='textbook_example'""",
    "contrast": """SELECT r.explanation,a.name,b.name AS compared_to,r.source_type FROM relationships r
        JOIN concepts a ON a.knowledge_id=r.from_id JOIN concepts b ON b.knowledge_id=r.to_id
        WHERE relation_type='confusable' AND ((a.name=? AND b.name=?) OR (a.name=? AND b.name=?))""",
    "topic": """SELECT DISTINCT c.knowledge_id,c.name,o.grade,o.book_id,o.chapter FROM concept_topics t
        JOIN concepts c USING(knowledge_id) JOIN occurrences o USING(knowledge_id) WHERE t.topic=?""",
    "exam": """SELECT question_id,stem_status,study_ready,checked_stem,checked_answer,
        json_extract(payload,'$.evidence_basis') AS evidence_basis FROM checked_exam_questions WHERE question_id=?""",
    "exam-index": """SELECT question_id,stem_status,study_ready,json_extract(payload,'$.evidence_basis') AS evidence_basis
        FROM exam_questions WHERE question_id=?"""
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=QUERIES)
    parser.add_argument("key")
    parser.add_argument("other", nargs="?")
    parser.add_argument("--db", type=Path, default=os.environ.get("MATH_KB_DB", DEFAULT))
    parser.add_argument("--all-status", action="store_true")
    parser.add_argument("--grade", type=int, choices=[7, 8, 9])
    args = parser.parse_args()
    query = QUERIES[args.mode]
    params = [args.key]
    if bool(args.other) != (args.mode == "contrast"):
        parser.error("contrast 需要两个概念名称，其他查询只需一个参数")
    if (args.grade and args.mode != "topic") or (args.all_status and args.mode != "examples"):
        parser.error("--grade 仅用于 topic；--all-status 仅用于 examples")
    if args.mode == "contrast":
        params = [args.key, args.other, args.other, args.key]
    elif args.mode == "concept":
        params = ["%" + args.key + "%"]
    elif args.mode == "examples" and not args.all_status:
        query += " AND e.extraction_status='verified'"
    elif args.grade:
        query += " AND o.grade=?"
        params.append(args.grade)
    try:
        with closing(sqlite3.connect(args.db.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(query, params).fetchall()
            for row in rows:
                print(json.dumps(dict(row), ensure_ascii=False))
            if not rows:
                print("没有符合当前条件的记录。", file=sys.stderr)
    except sqlite3.Error as error:
        parser.exit(1, f"无法查询；请用 --db 指定已有 V1.1 研究库：{error}\n")


if __name__ == "__main__":
    main()
