# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

def initialize_config():
    """
    Завантажує змінні оточення та повертає API-ключ.
    """
    print("   - Завантаження змінних з файлу .env...")
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    return api_key

GEMINI_API_KEY = initialize_config()

def load_prompt(file_path: str) -> str | None:
    """
    Завантажує текстовий промпт з файлу.
    """
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"ПОМИЛКА: Не вдалося прочитати файл '{file_path}': {e}")
        return None
