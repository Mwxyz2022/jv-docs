# -*- coding: utf-8 -*-
import google.generativeai as genai
import time

def configure_gemini(api_key: str):
    """Налаштовує API-ключ для Gemini."""
    if not api_key:
        raise ValueError("API-ключ для Gemini не надано. Перевірте ваш .env файл.")
    genai.configure(api_key=api_key)

def generate_conspectus(system_prompt: str, user_prompt: str) -> str:
    """
    Генерує контент, використовуючи наданий системний та користувацький промпт.
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            system_instruction=system_prompt
        )
        
        print("   - Відправка запиту до Gemini API...")
        response = model.generate_content(user_prompt)
        
        # Затримка для уникнення перевищення лімітів API (60 запитів на хвилину для Free tier)
        time.sleep(1.5) 
        
        return response.text

    except Exception as e:
        print(f"   - ❗️ Помилка під час виклику Gemini API: {e}")
        return ""
