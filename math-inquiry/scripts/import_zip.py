"""Extract legacy ZIP names to a fresh directory. Standard library only."""
import argparse
import json
import re
import shutil
import stat
import unicodedata
from pathlib import Path
from zipfile import ZipFile


def extract(archive, destination):
    names, mapping, kinds = [], {}, {}
    with ZipFile(archive) as bundle:
        for member in bundle.infolist():
            name = member.orig_filename
            if not member.flag_bits & 0x800:
                try:
                    name = name.encode("cp437").decode("utf-8")
                except UnicodeDecodeError:
                    pass
            if name != member.orig_filename:
                mapping[member.orig_filename] = name
            parts = name.removesuffix("/").split("/")
            if (any(part in ("", ".", "..") or ":" in part for part in parts)
                    or re.search(r"[\\\x00-\x1f]", name)
                    or stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError(f"unsafe member: {name!r}")
            for depth in range(1, len(parts) + 1):
                path = "/".join(parts[:depth])
                key = unicodedata.normalize("NFC", path).casefold()
                directory = depth < len(parts) or member.is_dir()
                prior = kinds.get(key)
                if prior and (prior[:2] != (path, directory) or (depth == len(parts) and prior[2])):
                    raise ValueError(f"name collision: {name!r}")
                kinds[key] = path, directory, depth == len(parts) or bool(prior and prior[2])
            names.append((member, name))
        destination.mkdir(parents=True, exist_ok=False)
        try:
            for member, name in names:
                target = destination / name
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(member) as source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return {"members": len(names), "files": sum(not item.is_dir() for item, _ in names), "restored": mapping}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.archive, args.destination), ensure_ascii=False, indent=2))
