import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.getcwd())

EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "pycache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "site-packages",
}

print("Установка форматтеров...")

subprocess.check_call([sys.executable, "-m", "pip", "install", "black", "isort"])

python_files = []

for current_root, dirs, files in os.walk(ROOT):
    dirs[:] = [directory for directory in dirs if directory not in EXCLUDED]

    for filename in files:
        if filename.endswith(".py"):
            python_files.append(os.path.join(current_root, filename))

if not python_files:
    print("Python-файлы не найдены.")
    sys.exit(1)

print(f"Найдено Python-файлов: {len(python_files)}")

print("Сортировка импортов...")

subprocess.check_call(
    [
        sys.executable,
        "-m",
        "isort",
        "--profile",
        "black",
        "--line-length",
        "88",
        *python_files,
    ]
)

print("Форматирование кода...")

subprocess.check_call(
    [sys.executable, "-m", "black", "--line-length", "88", *python_files]
)

print("Форматирование завершено.")
print(f"Обработано файлов: {len(python_files)}")
