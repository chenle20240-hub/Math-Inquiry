"""Project reviewed records, then build all learner outputs from that projection."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

FIELDS = {
    "concepts": "id origin title condition thought action".split(),
    "tasks": "id origin scene title problem start solution".split(),
    "links": "id origin task concept reason".split(),
}
IDS = {
    "concepts": set("DEMO-K01 DEMO-K02 DEMO-K03 DEMO-K04".split()),
    "tasks": set("DEMO-A01 DEMO-B01 DEMO-B01-TRANSFER DEMO-C01 DEMO-D01 DEMO-D01-RESTRICTED".split()),
    "links": {f"DEMO-R{index:02}" for index in range(1, 7)},
}
SCENES = {"A": "做题卡住", "B": "复习旧知识", "C": "预习新课", "D": "探讨数学思维"}


def generate(source, output):
    catalog = json.loads(source.read_text(encoding="utf-8"))
    if set(catalog) != set(FIELDS):
        raise ValueError("未登记的数据集合")
    demo = output / "data/demo"
    pages = output / "examples"
    demo.mkdir(parents=True, exist_ok=False)
    pages.mkdir(parents=True, exist_ok=True)
    rows = {}
    for table, fields in FIELDS.items():
        approved = []
        for record in catalog[table]:
            if (set(record) != set(fields) or record["origin"] != "original_demo"
                    or not all(isinstance(record[key], str) and record[key].strip() for key in fields)):
                raise ValueError("非原创来源、未知字段或空字段：" + table)
            approved.append({key: record[key] for key in fields})
        if len(approved) != len(IDS[table]) or {row["id"] for row in approved} != IDS[table]:
            raise ValueError("未登记或重复 ID：" + table)
        path = demo / (table + ".jsonl")
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sorted(approved, key=lambda obj: obj["id"])), encoding="utf-8")
        rows[table] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    with closing(sqlite3.connect(demo / "demo.sqlite")) as db:
        db.execute("PRAGMA foreign_keys=ON")
        for table, fields in FIELDS.items():
            columns = [key + " TEXT NOT NULL" + (" PRIMARY KEY" if key == "id" else "") for key in fields]
            if table == "links":
                columns += ["FOREIGN KEY(task) REFERENCES tasks(id)", "FOREIGN KEY(concept) REFERENCES concepts(id)", "UNIQUE(task,concept)"]
            db.execute(f"CREATE TABLE {table} (" + ",".join(columns) + ")")
            db.executemany(f"INSERT INTO {table} VALUES (" + ",".join("?" for _ in fields) + ")", ([row[key] for key in fields] for row in rows[table]))
        db.commit()
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",) or db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("演示数据库校验失败")
    student = ["# 学生任务｜今天先做一件事", "四个场景均为项目自拟，不是教材原题。挑一题，把题目、开场语和自己的第一稿交给 AI。独立自查时不要先看参考解。"]
    reference = ["# 原创演示｜参考解与思想卡", "供作答后核对或 AI 备课。以下均为 original_demo；不用教材页码。给提示后要把下一步留给学生，不要把提示后完成记成独立完成。"]
    for task in rows["tasks"]:
        heading = f"## {SCENES[task['scene']]} · {task['title']}（{task['id']}）"
        student.extend([heading, task["problem"], "> " + task["start"]])
        reference.extend([heading, task["problem"], task["solution"]])
        for link in rows["links"]:
            if link["task"] == task["id"]:
                card = next(card for card in rows["concepts"] if card["id"] == link["concept"])
                reference.append(f"**{card['thought']}** · {link['reason']}\n\n适用条件：{card['condition']}\n\n留给学生的动作：{card['action']}")
    student.extend(["## 收尾", "留下三行：我独立完成了什么；提示后补了什么；什么尚未检查。没有做过变式，就不要把它记为会做。", "[学习记录](../docs/LEARNING_RECORD.md) · [作答后核对](DEMO_PACK.md)"])
    reference.append("[学生任务](STUDENT_TASKS.md) · [模拟对话](DEMO_DIALOGUE.md)")
    for filename, paragraphs in [("STUDENT_TASKS.md", student), ("DEMO_PACK.md", reference)]:
        (pages / filename).write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8")
