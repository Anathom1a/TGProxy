import subprocess
import hashlib
import json
import os

# Эту строку GitHub автоматически заменит на твой секретный пароль при сборке
SECRET_SALT = "REPLACE_ME_SECRET_SALT"

# Прячем файл лицензии в системную папку AppData/Roaming/TGProxy
APP_DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'TGProxy')
CONFIG_FILE = os.path.join(APP_DATA_DIR, "license.json")

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
    if not SECRET_SALT:
        return "ERROR_NO_SALT"
    return hashlib.sha256((hwid + SECRET_SALT).encode()).hexdigest()[:12]

def is_activated():
    """Строго проверяет, есть ли правильный ключ в конфиге"""
    if not os.path.exists(CONFIG_FILE):
        return False
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            
        saved_key = data.get("key")
        
        if not saved_key or not str(saved_key).strip():
            return False
            
        current_hwid = get_hwid()
        expected_key = generate_key(current_hwid)
        
        return saved_key == expected_key
    except (json.JSONDecodeError, Exception):
        return False

def save_key(key):
    """Сохраняет валидный ключ в JSON"""
    # Создаем папку TGProxy в AppData, если её еще нет
    if not os.path.exists(APP_DATA_DIR):
        os.makedirs(APP_DATA_DIR)
        
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"key": key}, f)
