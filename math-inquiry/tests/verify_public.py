"""Inspect the public candidate and reproduce the first experience in isolation."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from export_public import export, LOCK
from import_zip import extract
from public_demo import FIELDS


def hashfile(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and not any(part in {".git", "__pycache__", "build", "dist", "records", "local-inputs"} for part in path.relative_to(root).parts)}


def main():
    manifest = json.loads((ROOT / LOCK).read_text(encoding="utf-8"))
    generated = {"examples/STUDENT_TASKS.md", "examples/DEMO_PACK.md", "data/demo/demo.sqlite", *("data/demo/" + name + ".jsonl" for name in FIELDS)}
    assert tree(ROOT) == set(manifest) | generated | {LOCK}, tree(ROOT) ^ (set(manifest) | generated | {LOCK})
    link_count = 0
    for name in tree(ROOT):
        path = ROOT / name
        if path.suffix == ".sqlite":
            continue
        content = path.read_text(encoding="utf-8")
        assert not re.search(r"(?:/(?:Users|home)/[^/\s]+/|[A-Za-z]:\\Users\\[^\\]+\\)", content), name
        if path.suffix != ".md":
            continue
        for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", content):
            parsed = urlsplit(target)
            if parsed.scheme in {"http", "https", "mailto"}:
                continue
            dest = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            assert dest.is_relative_to(ROOT) and dest.is_file(), (name, target)
            link_count += 1
    cases = json.loads((ROOT / "evals/learning_cases.json").read_text(encoding="utf-8"))["cases"]
    assert {case["id"] for case in cases} == {f"MATH-EVAL-{index:02}" for index in range(1, 17)}
    assert len(cases) == 16 and all(case["status"] == "not_run" for case in cases)
    ElementTree.parse(ROOT / "evals/fixtures/triangle_without_marks.svg")
    with tempfile.TemporaryDirectory() as folder:
        area = Path(folder)
        candidate = area / "fresh"
        export(candidate)
        assert tree(candidate) == tree(ROOT)
        for name in tree(candidate) - {"data/demo/demo.sqlite"}:
            assert (candidate / name).read_bytes() == (ROOT / name).read_bytes(), name
        def values(base):
            with closing(sqlite3.connect((base / "data/demo/demo.sqlite").as_uri() + "?mode=ro", uri=True)) as db:
                assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",) and not db.execute("PRAGMA foreign_key_check").fetchall()
                assert {row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")} == set(FIELDS)
                return {name: db.execute(f"SELECT * FROM {name} ORDER BY id").fetchall() for name in FIELDS}
        assert values(candidate) == values(ROOT)
        db = candidate / "data/demo/demo.sqlite"
        before = hashfile(db)
        quick = (candidate / "docs/QUICKSTART.md").read_text(encoding="utf-8")
        commands = re.findall(r"^python3 scripts/demo\.py.*$", quick, re.M)
        assert len(commands) == 3
        for command in commands:
            result = subprocess.check_output([sys.executable, *command.split()[1:]], cwd=candidate, text=True)
            if "--after-attempt" in command:
                assert "x≠3" in result
            else:
                assert "x≠3" not in result
        assert hashfile(db) == before
        missing = subprocess.run([sys.executable, "scripts/demo.py", "unknown"], cwd=candidate, capture_output=True)
        assert missing.returncode != 0
        for index, members in enumerate([["../outside"], ["/absolute"], ["A/file", "a/file"], ["a", "a/b"]]):
            archive = area / f"invalid{index}.zip"
            with ZipFile(archive, "w") as bundle:
                for name in members:
                    bundle.writestr(name, "x")
            try:
                extract(archive, area / f"invalid{index}")
            except ValueError:
                pass
            else:
                raise AssertionError("accepted unsafe archive")
    print(json.dumps({"files": len(tree(ROOT)), "local_links": link_count, "demo_rows": {key: len(rows) for key, rows in values(ROOT).items()}, "quickstart_commands": commands, "eval_designs": len(cases)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
