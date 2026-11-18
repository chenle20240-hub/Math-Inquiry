"""Read a prebuilt original task without revealing its solution."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3

DB = Path(__file__).resolve().parents[1] / "data/demo/demo.sqlite"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="?", help="omit to list tasks")
    parser.add_argument("--after-attempt", action="store_true", help="show reference only after an attempt")
    args = parser.parse_args()
    try:
        with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as db:
            if not args.task:
                for ident, title in db.execute("SELECT id,title FROM tasks ORDER BY id"):
                    print(ident, title)
                return
            row = db.execute("SELECT origin,problem,start,solution FROM tasks WHERE id=?", (args.task,)).fetchone()
            if not row:
                parser.error("没有这个任务；不带参数运行可列出全部 ID")
            print(f"[{row[0]}] {args.task}\n{row[1]}\n\n{row[2]}")
            if args.after_attempt:
                print("\n作答后核对：" + row[3])
    except sqlite3.Error as error:
        parser.exit(1, f"无法打开已有演示数据：{error}\n")


if __name__ == "__main__":
    main()
