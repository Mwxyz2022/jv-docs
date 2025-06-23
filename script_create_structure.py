# -*- coding: utf-8 -*-

# === ІМПОРТ НЕОБХІДНИХ БІБЛІОТЕК ===
# os: для взаємодії з операційною системою (створення папок, шляхів)
import os
# re: для роботи з регулярними виразами (пошук патернів у тексті)
import re
# shutil: для операцій з файлами високого рівня (наприклад, видалення дерев каталогів)
import shutil
# slugify: для перетворення тексту в URL-сумісний формат (напр. "Привіт Світ" -> "privit-svit")
from slugify import slugify

def clean_generated_folders(base_path='.'):
    """
    Очищує раніше згенеровані папки.
    Це потрібно, щоб уникнути конфліктів та застарілих файлів при повторному запуску скрипту.
    Функція читає `content.md` і видаляє папки, що відповідають його структурі.
    """
    # Перевірка, чи існує файл `content.md`. Якщо ні, очищення не потрібне.
    if not os.path.exists('content.md'):
        print("Файл content.md не знайдено. Очищення не потрібне.")
        return
        
    print("Запускаю очищення раніше згенерованих каталогів...")
    # Відкриваємо `content.md` для читання
    with open('content.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Проходимо по кожному рядку файлу
    for line in lines:
        # Шукаємо рядки, що відповідають формату "1.2.3 Назва розділу"
        match = re.match(r'^(\d+(\.\d+)*)\s+(.+)', line)
        if match:
            # Витягуємо назву розділу
            title = match.group(3).strip()
            # Перетворюємо назву на безпечне ім'я для папки
            folder_name = slugify(title)
            # Ми видаляємо тільки папки верхнього рівня, оскільки скрипт створює їх з нуля.
            # Це перевіряється по наявності крапки в номері (напр. "1" - верхній рівень, "1.1" - ні).
            if '.' not in match.group(1):
                path_to_remove = os.path.join(base_path, folder_name)
                # Якщо така папка існує, видаляємо її рекурсивно
                if os.path.isdir(path_to_remove):
                    shutil.rmtree(path_to_remove)
                    print(f"Видалено каталог: {path_to_remove}")
    print("Очищення завершено.")

def create_structure(lines, parent_path='.', parent_title='Home', level=1):
    """
    Рекурсивно створює структуру каталогів та файли `index.md`.
    Функція обробляє список рядків з `content.md` і для кожного створює
    відповідну папку та файл `index.md` з необхідною службовою інформацією (Jekyll Front Matter).
    
    :param lines: Список рядків, що залишилися для обробки.
    :param parent_path: Шлях до батьківського каталогу.
    :param parent_title: Назва батьківського розділу для навігації.
    :param level: Поточний рівень вкладеності (1 для кореневих розділів).
    :return: Кількість оброблених рядків.
    """
    i = 0
    # Цикл проходить по рядках, доки вони не закінчаться
    while i < len(lines):
        line = lines[i]
        
        # Визначаємо рівень вкладеності поточного елемента за його номером
        match = re.match(r'^(\d+(\.\d+)*)\s+(.+)', line)
        if not match:
            # Якщо рядок не відповідає формату, ігноруємо його
            i += 1
            continue
            
        current_level_str = match.group(1)
        current_level = len(current_level_str.split('.'))
        
        # Якщо поточний рівень менший за очікуваний, це означає, що ми повернулися
        # на рівень вище, тому потрібно завершити рекурсивний виклик.
        if current_level < level:
            return i 

        # Якщо поточний рівень більший, це означає, що це дочірній елемент.
        # Ми викликаємо цю ж функцію рекурсивно для обробки вкладеної структури.
        if current_level > level:
            # `lines[i:]` передає залишок списку в рекурсію.
            lines_processed = create_structure(lines[i:], current_path, title, level + 1)
            # Пропускаємо рядки, які були оброблені в рекурсивному виклику.
            i += lines_processed
            continue

        # --- ОБРОБКА ЕЛЕМЕНТА ПОТОЧНОГО РІВНЯ ---

        # Витягуємо назву і створюємо slug (ім'я для папки/URL)
        title = match.group(3).strip()
        slug = slugify(title)
        # Формуємо повний шлях до нового каталогу
        current_path = os.path.join(parent_path, slug)
        
        # Створюємо каталог, якщо він ще не існує
        os.makedirs(current_path, exist_ok=True)
        
        # Шлях до файлу index.md всередині нового каталогу
        index_path = os.path.join(current_path, 'index.md')
        
        # Перевіряємо, чи є у цього елемента дочірні.
        # Це потрібно для Jekyll-теми, щоб відобразити стрілочку для розгортання меню.
        has_children = False
        if i + 1 < len(lines): # Перевіряємо, чи є наступний рядок
            next_line = lines[i+1]
            next_match = re.match(r'^(\d+(\.\d+)*)', next_line)
            if next_match:
                # Якщо рівень наступного елемента більший, значить, поточний має дочірні
                next_level = len(next_match.group(1).split('.'))
                if next_level > level:
                    has_children = True

        # Створюємо файл index.md та записуємо в нього службову інформацію Jekyll (Front Matter)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('---\n')
            f.write('layout: default\n')             # Шаблон сторінки
            f.write(f'title: {title}\n')             # Заголовок сторінки
            f.write(f'parent: {parent_title}\n')     # Батьківський елемент для навігації
            
            # Витягуємо останню цифру з номера (напр. з "1.2.3" беремо "3") для сортування
            nav_order = current_level_str.split('.')[-1]
            f.write(f'nav_order: {nav_order}\n')
            
            # Якщо є дочірні елементи, додаємо відповідний прапорець
            if has_children:
                f.write('has_children: true\n')
                
            f.write('---\n\n') # Кінець Front Matter
            # Додаємо основний заголовок на сторінку
            f.write(f'# {title}\n\n')
            f.write('This is a placeholder for the content.\n') # Тимчасовий текст-заглушка
        
        i += 1
    
    return i # Повертаємо кількість оброблених рядків

def main():
    """
    Головна функція, яка керує виконанням скрипту.
    """
    # 1. Спершу очищуємо старі згенеровані папки
    clean_generated_folders()

    # 2. Намагаємося прочитати файл `content.md`
    try:
        with open('content.md', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Помилка: файл content.md не знайдено. Будь ласка, створіть цей файл зі структурою документації.")
        return

    # 3. Створюємо кореневий файл index.md для сайту (головна сторінка)
    with open('index.md', 'w', encoding='utf-8') as f:
        f.write('---\n')
        f.write('layout: home\n')
        f.write('title: Home\n')
        f.write('nav_order: 1\n')
        f.write('---\n\n')
        f.write('# Welcome to the Documentation\n\n')
        f.write('Select a topic from the navigation to get started.\n')
        
    # 4. Запускаємо рекурсивний процес створення структури
    create_structure(lines)
    print("Структура каталогів та файли index.md успішно створені.")

# Цей блок виконується тільки тоді, коли скрипт запускається напряму
if __name__ == '__main__':
    main()
