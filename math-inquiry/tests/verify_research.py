"""Validate a privately held V1.1 dataset without changing it."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from database import build, readonly


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def verify(kb):
    dataset = kb / "data"
    original = kb / "database/math_kb.sqlite"
    inputs = [original, *sorted(dataset.glob("*.jsonl"))]
    before = {path: digest(path) for path in inputs}
    with tempfile.TemporaryDirectory() as folder:
        area = Path(folder)
        rebuilt = area / "rebuilt.sqlite"
        counts = build(dataset, rebuilt, original)
        assert len(counts) == 20
        commands = [line.split()[2:] for line in (kb / "README.md").read_text(encoding="utf-8").splitlines() if line.startswith("python3 scripts/query.py ")]
        expected = [9, 2, 1, 7, 1, 1, 17]
        assert len(commands) == len(expected)
        def run(args, db, ok=True):
            process = subprocess.run([sys.executable, "scripts/query.py", *args], cwd=ROOT,
                                     env={**os.environ, "MATH_KB_DB": str(db)}, text=True, capture_output=True)
            assert (process.returncode == 0) == ok, process.stderr
            return [json.loads(line) for line in process.stdout.splitlines()], process.stderr
        for command, count in zip(commands, expected):
            old, _ = run(command, original)
            new, _ = run(command, rebuilt)
            assert len(old) == count and sorted(map(str, old)) == sorted(map(str, new)), command
        selected, _ = run(["examples", "勾股定理"], original)
        all_rows, _ = run(["examples", "勾股定理", "--all-status"], original)
        assert all(row["extraction_status"] == "verified" for row in selected)
        assert {row["example_id"] for row in selected} <= {row["example_id"] for row in all_rows}
        assert run(["concept", "不存在的概念"], rebuilt)[1]
        run(["contrast", "平方根"], original, False)
        absent = area / "missing.sqlite"
        run(["concept", "平方根"], absent, False)
        assert not absent.exists()
        with closing(readonly(original)) as db:
            for ready in (0, 1):
                ident = db.execute("SELECT question_id FROM exam_questions WHERE study_ready=? LIMIT 1", (ready,)).fetchone()[0]
                assert len(run(["exam", ident], original)[0]) == ready
                index, _ = run(["exam-index", ident], original)
                assert index[0]["study_ready"] == ready and index[0]["evidence_basis"]
        try:
            build(dataset, original, original)
        except ValueError:
            pass
        else:
            raise AssertionError("allowed existing output")
        testdata = area / "data"
        shutil.copytree(dataset, testdata)
        for name in ("concepts", "relationships", "examples"):
            path = testdata / (name + ".jsonl")
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
        assert build(testdata, area / "reordered.sqlite", original) == counts
        path = testdata / "relationships.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        invalid = json.loads(lines[0])
        invalid["to_id"] = "invalid-concept"
        lines[0] = json.dumps(invalid, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            build(testdata, area / "invalid.sqlite", original)
        except ValueError as error:
            assert "FOREIGN KEY" in str(error)
        else:
            raise AssertionError("accepted invalid reference")
        assert not (area / "invalid.sqlite").exists()
    assert before == {path: digest(path) for path in inputs}
    print(json.dumps({"queries": expected, "tables_and_views": counts, "input_files_unchanged": len(before), "db_sha256": before[original]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kb", type=Path)
    verify(parser.parse_args().kb.resolve())
