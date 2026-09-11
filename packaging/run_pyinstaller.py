import sys
from pathlib import Path


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: run_pyinstaller.py TOOL_ROOT [SPEC_FILE]")
    tool_root = Path(sys.argv[1]).resolve()
    project = Path(__file__).resolve().parent.parent
    spec_file = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else project / "desktop_pet.spec"
    sys.path.insert(0, str(tool_root))
    import PyInstaller.__main__

    PyInstaller.__main__.run([
        "--noconfirm",
        "--clean",
        "--distpath", str(project / "release"),
        "--workpath", str(project / "build" / "pyinstaller"),
        str(spec_file),
    ])


if __name__ == "__main__":
    main()
