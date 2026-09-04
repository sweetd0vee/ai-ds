#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ -x "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
  PYTHON="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
else
  PYTHON="python3"
fi

if [ ! -d "vendor" ]; then
  echo "Установка зависимостей в vendor/..."
  "$PYTHON" -m pip install -r requirements.txt --target ./vendor
fi

exec "$PYTHON" run_dev.py
