"""Dev-сервер. Запуск из папки new/backend: python run_dev.py"""

import sys
from pathlib import Path

REQUIRED = ("fastapi", "uvicorn", "pandas", "langchain_community", "langchain_classic")


def setup_paths():
    backend_dir = Path(__file__).resolve().parent
    vendor = backend_dir / "vendor"
    if vendor.is_dir():
        sys.path.insert(0, str(vendor))
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    return backend_dir


def check_dependencies():
    missing = []
    for module in REQUIRED:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        print("Не установлены зависимости:", ", ".join(missing))
        print("Выполните:")
        print("  python3 -m pip install -r requirements.txt --target ./vendor")
        sys.exit(1)


if __name__ == "__main__":
    backend_dir = setup_paths()
    check_dependencies()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir / "app")],
        reload_excludes=["data", "data/*", "data/**", "vendor", "vendor/*"],
    )
