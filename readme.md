## 1. Открытие папки проекта

Откройте PowerShell и выполните:

Set-Location "$HOME\Desktop\system_collection"
Проверка расположения:

Get-Location
Проверка файлов проекта:

Get-ChildItem
## 2. Проверка Python

python --version
Проверка доступности pip:

python -m pip --version
## 3. Обновление установщика пакетов

python -m pip install --upgrade pip
## 4. Создание виртуального окружения

python -m venv .venv
## 5. Активация виртуального окружения

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```powershell
.\.venv\Scripts\Activate.ps1

После активации слева в строке терминала должно появиться `(.venv)`.

## 6. Установка зависимостей проекта

powershell
python -m pip install -r requirements.txt

Проверка установленных библиотек:

powershell
python -m pip list

Проверка зависимостей:

powershell
python -m pip check

## 7. Проверка синтаксиса Python

powershell
python -m compileall -q app config database tests main.py

## 8. Запуск автоматических тестов

powershell
python -m pytest -v

Для повторного запуска с подробным выводом:

powershell
python -m pytest -vv


