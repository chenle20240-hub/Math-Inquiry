"""Export the reviewed candidate to a NEW directory; no recursive copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from public_demo import generate

ROOT = Path(__file__).resolve().parents[1]
LOCK = "release/files.json"


def export(output):
    output = output.resolve()
    if output.exists():
        raise ValueError("输出目录已存在")
    manifest = json.loads((ROOT / LOCK).read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        candidate = Path(staging) / "candidate"
        candidate.mkdir()
        for name, expected in manifest.items():
            source = ROOT / name
            if not source.resolve().is_relative_to(ROOT) or source.is_symlink() or source.relative_to(ROOT).as_posix() != name:
                raise ValueError("无效路径：" + name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError("文件内容有变化，请先复审：" + name)
            target = candidate / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (candidate / LOCK).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / LOCK, candidate / LOCK)
        generate(candidate / "catalog/demo.json", candidate)
        candidate.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        export(args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f"导出失败：{error}\n")
