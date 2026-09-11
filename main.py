import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from pet.paths import resource_path, user_data_file
from pet.window import PetWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName('小新桌宠')
    icon_path = resource_path('assets', 'pet.ico')
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    pet = PetWindow()
    if '--export-assets' in sys.argv:
        root = Path(__file__).resolve().parent / 'assets'
        for state, frames in pet.frames.items():
            folder = root / state.lower(); folder.mkdir(parents=True,exist_ok=True)
            for i, image in enumerate(frames):
                target = folder / f'{i:02}.png'
                if not image.save(str(target)):
                    raise RuntimeError(f'Cannot save {target}')
        return 0
    pet.show()
    if '--smoke-test' in sys.argv:
        for i,state in enumerate(pet.frames):
            QTimer.singleShot(i*250,lambda s=state: (setattr(pet,'state',s),pet.update()))
        QTimer.singleShot(1600,app.quit)
    return app.exec()

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        import traceback
        message = traceback.format_exc()
        error_path = user_data_file('error.log')
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text(message, encoding='utf-8')
        if sys.stderr is not None:
            sys.stderr.write(message)
        raise
