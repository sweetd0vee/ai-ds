"""Dev-сервер. Запуск из папки new/backend: python run_dev.py"""

import os
import sys
from pathlib import Path

API_PORT = int(os.environ.get("API_PORT", "8010"))
APP_TITLE = "Электронный Data Scientist API"

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


def check_port_available(port: int) -> None:
    import json
    import urllib.error
    import urllib.request

    url = f"http://127.0.0.1:{port}/openapi.json"
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError):
        return

    title = payload.get("info", {}).get("title", "unknown")
    if title != APP_TITLE:
        print(f"Порт {port} занят другим приложением: {title}")
        print(f"Запустите на свободном порту: set API_PORT=8800 && python run_dev.py")
        sys.exit(1)


if __name__ == "__main__":
    backend_dir = setup_paths()
    check_dependencies()
    check_port_available(API_PORT)

    import uvicorn

    print(f"API: http://localhost:{API_PORT}/api/health")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=True,
        reload_dirs=[str(backend_dir / "app")],
        reload_excludes=["data", "data/*", "data/**", "vendor", "vendor/*"],
    )
