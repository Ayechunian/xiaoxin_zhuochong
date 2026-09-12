from pathlib import Path


project = Path(SPEC).resolve().parent

a = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=[
        (str(project / "assets" / "poses"), "assets/poses"),
        (str(project / "assets" / "pet.ico"), "assets"),
        (str(project / "assets" / "character.png"), "assets"),
        (str(project / "assets" / "down-arrow.svg"), "assets"),
        (str(project / "pet" / "speak.ps1"), "pet"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project / "packaging" / "runtime_dll_paths.py")],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# PyInstaller can resolve Qt's Windows ICU shim against an unrelated ICU DLL
# present on the build machine's PATH. Do not bundle that incompatible copy.
blocked_icu_binaries = {"icuuc.dll", "icudt78.dll"}
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in blocked_icu_binaries]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="小新桌宠",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project / "assets" / "pet.ico"),
    version=str(project / "packaging" / "version_info.txt"),
)
