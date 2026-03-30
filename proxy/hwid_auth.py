import subprocess
import hashlib
import json
import os

# Эту строку GitHub автоматически заменит на твой секретный пароль при сборке
SECRET_SALT = "REPLACE_ME_SECRET_SALT"
CONFIG_FILE = "license.json"

def get_hwid():
    """Получает серийный номер системного диска Windows"""
    try:
        cmd = 'wmic diskdrive get serialnumber'
        result = subprocess.check_output(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW).decode().split()
        return result[1] if len(result) > 1 else "UNKNOWN_HWID"
    except Exception:
        return "FALLBACK_HWID"

def generate_key(hwid):
    """Генерирует уникальный ключ на основе HWID и секретной соли"""
    # Защита от запуска без подстановки секрета на этапе сборки
    if not SECRET_SALT or SECRET_SALT == "REPLACE_ME_SECRET_SALT":
        return "ERROR_NO_SALT"
        
    return hashlib.sha256((hwid + SECRET_SALT).encode()).hexdigest()[:12]

def is_activated():
    """Строго проверяет, есть ли правильный ключ в конфиге"""
    # 1. Если файла вообще нет — блокируем
    if not os.path.exists(CONFIG_FILE):
        return False
        
    try:
        # Пытаемся прочитать файл
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            
        saved_key = data.get("key")
        
        # 2. Если ключ равен None, пустой строке или состоит из пробелов — блокируем
        if not saved_key or not str(saved_key).strip():
            return False
            
        # 3. Сравниваем сохраненный ключ с правильным ключом для текущего ПК
        current_hwid = get_hwid()
        expected_key = generate_key(current_hwid)
        
        return saved_key == expected_key
        
    except (json.JSONDecodeError, Exception):
        # 4. Если файл пустой или внутри невалидный JSON (каша) — блокируем
        return False

def save_key(key):
    """Сохраняет валидный ключ в JSON"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"key": key}, f)