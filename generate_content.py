# -*- coding: utf-8 -*-
import os
import yaml
import re
from config import GEMINI_API_KEY, load_prompt
from gemini_service import configure_gemini, generate_conspectus

# --- Налаштування ---
PROCESSING_LIST_FILE = "files_to_process.txt"
FAIL_LOG_FILE = "fail_process.txt"

def get_file_data(file_path: str) -> tuple[dict | None, str | None]:
    """
    Читає YAML Front Matter та основний контент з Markdown файлу.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
            if match:
                front_matter = yaml.safe_load(match.group(1))
                main_content = match.group(2).strip()
                return front_matter, main_content
    except Exception as e:
        print(f"   - Помилка читання файлу {file_path}: {e}")
    return None, None

def update_file_content(file_path: str, front_matter: dict, new_content: str):
    """
    Перезаписує файл, зберігаючи Front Matter та додаючи новий контент.
    """
    fm_string = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
    full_content_to_write = f"---\n{fm_string}---\n{new_content}"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_content_to_write)
    print(f"   - ✅ Файл '{file_path}' успішно оновлено.")

def get_files_to_process() -> list[str]:
    """Читає список файлів для обробки з керуючого файлу."""
    if not os.path.exists(PROCESSING_LIST_FILE):
        return []
    with open(PROCESSING_LIST_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]

def update_processing_list(remaining_files: list[str]):
    """Перезаписує керуючий файл списком файлів, що залишилися."""
    with open(PROCESSING_LIST_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(remaining_files) + "\n" if remaining_files else "")

def log_failed_file(file_path: str):
    """Додає шлях до файлу, який не вдалося обробити, у лог-файл."""
    with open(FAIL_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{file_path}\n")

def check_configuration() -> tuple[dict, bool]:
    """Перевіряє всю необхідну конфігурацію."""
    print("--- Перевірка конфігурації ---")
    
    if not GEMINI_API_KEY:
        print("❌ ПОМИЛКА: API ключ не знайдено в .env")
        return {}, False
    print("✅ API ключ завантажено.")

    prompt_files = {
        "section": "prompt/section_master_prompt.md",
        "overview": "prompt/overview_master_prompt.md",
        "topic": "prompt/topic_master_prompt.md",
        "faq": "prompt/faq_master_prompt.md"
    }
    
    loaded_prompts = {}
    config_ok = True
    for name, path in prompt_files.items():
        prompt_content = load_prompt(path)
        if prompt_content is None:
            print(f"❌ ПОМИЛКА: Файл інструкції не знайдено: '{path}'")
            config_ok = False
        else:
            loaded_prompts[name] = prompt_content
            print(f"✅ Інструкція '{name}' завантажена.")
            
    if not config_ok: return {}, False
        
    print("--- Конфігурація в порядку ---")
    return loaded_prompts, True

def main():
    """Головна функція для генерації контенту."""
    prompts, config_ok = check_configuration()
    if not config_ok: return
        
    try:
        configure_gemini(GEMINI_API_KEY)
    except ValueError as e:
        print(e)
        return

    files_queue = get_files_to_process()
    if not files_queue:
        print("\nСписок файлів ('files_to_process.txt') порожній. Завершення роботи.")
        return

    print(f"\n🚀 Початок генерації контенту. В черзі {len(files_queue)} файлів...")

    while files_queue:
        file_path_from_list = files_queue.pop(0)
        clean_file_path = file_path_from_list.lstrip('/')
        
        is_successful = False
        try:
            if not os.path.exists(clean_file_path):
                raise FileNotFoundError(f"Файл '{clean_file_path}' не знайдено.")
            
            print(f"\nОбробка файлу: '{clean_file_path}'")
            front_matter, _ = get_file_data(clean_file_path)
            if not front_matter:
                raise ValueError("Не вдалося прочитати Front Matter.")

            master_prompt_key = None
            user_prompt = None
            
            if clean_file_path.endswith('qa.md'):
                master_prompt_key = "faq"
                full_title = front_matter.get('title', '')
                topic_title = re.sub(r'[\d\.]+\s*Q&A\s*:?\s*', '', full_title, flags=re.IGNORECASE).strip()
                related_summary = "відсутній"
                related_index_path = os.path.join(os.path.dirname(clean_file_path), 'index.md')
                if os.path.exists(related_index_path):
                    _, summary_content = get_file_data(related_index_path)
                    if summary_content: related_summary = summary_content
                user_prompt = f'[TOPIC_TITLE]: "{topic_title}"\n[RELATED_SUMMARY]: "{related_summary[:4000]}"'

            elif clean_file_path.endswith('index.md'):
                full_title = front_matter.get('title', '')
                match = re.match(r'([\d\.]+)', full_title)
                if not match: raise ValueError("Не вдалося розпарсити номер з 'title' у Front Matter.")
                
                topic_number = match.group(1)
                level = len(topic_number.split('.'))
                
                if front_matter.get('has_children', False):
                    sub_topics_list = []
                    sub_dirs = sorted([d for d in os.listdir(os.path.dirname(clean_file_path)) if os.path.isdir(os.path.join(os.path.dirname(clean_file_path), d))])
                    for sub_dir in sub_dirs:
                        sub_index_path = os.path.join(os.path.dirname(clean_file_path), sub_dir, 'index.md')
                        if os.path.exists(sub_index_path):
                            sub_fm, _ = get_file_data(sub_index_path)
                            if sub_fm: sub_topics_list.append(sub_fm.get('title', ''))
                    sub_topics_str = ", ".join(filter(None, sub_topics_list)) if sub_topics_list else "відсутні"

                    if level <= 2:
                        master_prompt_key = "section"
                        user_prompt = f"Напиши дуже короткий оглядовий текст (1 абзац) для великого розділу '{full_title}'. Його основні підрозділи: {sub_topics_str}."
                    else:
                        master_prompt_key = "overview"
                        user_prompt = f"Напиши змістовний вступний текст (2-4 абзаци) для розділу '{full_title}'. Поясни, чому ця тема важлива, і коротко представ її підтеми: {sub_topics_str}."

                else: # не має дочірніх елементів
                    master_prompt_key = "topic"
                    topic_title = re.sub(r'[\d\.]+\s*', '', full_title).strip()
                    parent_title = front_matter.get('parent', 'N/A')
                    user_prompt = f'[TOPIC_NUMBER]: "{topic_number}"\n[TOPIC_TITLE]: "{topic_title}"\n[PARENT_TOPIC_TITLE]: "{parent_title}"'
            
            if not master_prompt_key: raise ValueError("Не вдалося визначити тип контенту.")
            
            master_prompt = prompts[master_prompt_key]
            generated_content = generate_conspectus(master_prompt, user_prompt)
            if not generated_content: raise Exception("API повернуло порожню відповідь.")

            # --- Оновлена логіка додавання посилань ---
            final_content = generated_content
            if clean_file_path.endswith('qa.md'):
                final_content += "\n\n* * *\n\n[Повернутись до теорії](./index.md)\n"
            elif clean_file_path.endswith('index.md'):
                qa_file_path = os.path.join(os.path.dirname(clean_file_path), 'qa.md')
                if os.path.exists(qa_file_path):
                    final_content += "\n\n* * *\n\n[Перейти до Q&A](./qa.md)\n"

            update_file_content(clean_file_path, front_matter, final_content)
            is_successful = True

        except Exception as e:
            print(f"   - ❌ Помилка під час обробки {clean_file_path}: {e}")
            is_successful = False

        if not is_successful:
            log_failed_file(file_path_from_list)
        
        update_processing_list(files_queue)
        print(f"   - Залишилось в черзі: {len(files_queue)} файлів.")

    print("\n✅ Черга обробки порожня. Роботу завершено.")

if __name__ == "__main__":
    main()
