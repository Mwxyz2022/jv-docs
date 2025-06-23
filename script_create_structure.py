# -*- coding: utf-8 -*-
import os
import re
import shutil

def slugify(text: str) -> str:
    """
    Перетворює український текст на URL-дружній "слаг".
    Транслітерує, переводить у нижній регістр, замінює пробіли на '_'
    та видаляє всі неприпустимі символи.
    """
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e',
        'є': 'ie', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'i', 'й': 'i',
        'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'iu', 'я': 'ia'
    }
    text_lower = text.lower()
    slug = "".join(translit_map.get(char, char) for char in text_lower)
    slug = re.sub(r'[\s/]+', '_', slug)
    slug = re.sub(r'[^\w_]', '', slug)
    return slug.strip('_')

def parse_structure(content: str) -> dict:
    """
    Парсить вхідний текстовий контент і будує ієрархічне дерево.
    """
    root = {'children': [], 'title': 'Root', 'slug': ''}
    nodes_map = {'': root}
    
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('***'):
            continue

        num_match = re.search(r'([\d\.]+)', line)
        if not num_match:
            continue
        
        full_number = num_match.group(1).strip('.')
        
        # --- Оновлена, більш надійна логіка очищення заголовка ---
        # 1. Починаємо з повного рядка, видаляємо markdown-префікси
        title_text = re.sub(r'^(?:[#\s*-]|\*\*)*', '', line).strip()
        # 2. Видаляємо ключові слова, такі як "Тема", "Частина"
        title_text = re.sub(r'\b(Тема|Підрозділ|Частина)\b', '', title_text)
        # 3. Видаляємо сам номер
        title_text = title_text.replace(full_number, '')
        # 4. Видаляємо будь-які залишкові двокрапки, зірочки та зайві пробіли по краях
        title_text = title_text.strip(':* ')
        # 5. Стискаємо множинні пробіли в один
        title_text = re.sub(r'\s+', ' ', title_text).strip()
        # --- Кінець оновленої логіки ---

        if not title_text:
            print(f"ПОПЕРЕДЖЕННЯ: Не вдалося видобути заголовок для номера '{full_number}'. Рядок: '{line}'")
            continue

        parent_number = '.'.join(full_number.split('.')[:-1])
        parent_node = nodes_map.get(parent_number)

        if parent_node is None:
            print(f"ПОПЕРЕДЖЕННЯ: Не знайдено батьківський елемент для '{full_number}'. Рядок пропущено.")
            continue

        level = len(full_number.split('.'))
        slug = f"{full_number}_{slugify(title_text)}"

        new_node = {
            'full_number': full_number,
            'title_with_number': f"{full_number} {title_text}",
            'clean_title': title_text,
            'slug': slug,
            'nav_order': len(parent_node['children']) + 1,
            'level': level,
            'children': []
        }
        
        parent_node['children'].append(new_node)
        nodes_map[full_number] = new_node

    return root

def generate_files(node: dict, path_parts: list, parent_full_title: str = "", grand_parent_full_title: str = ""):
    """
    Рекурсивно обходить дерево та генерує папки і файли.
    """
    # Спеціальна обробка для кореневого вузла, який сам не є сторінкою
    if 'slug' not in node or not node['slug']:
        # Його нащадки мають своїм батьком головну сторінку документації
        for child in node['children']:
            generate_files(child, path_parts, parent_full_title="Документація")
        return

    current_path_str = os.path.join(*path_parts, node['slug'])
    os.makedirs(current_path_str, exist_ok=True)
    
    needs_qa_file = node.get('level', 0) >= 3

    # --- Формуємо заголовки ---
    current_full_title = f"{node['full_number']} {node['clean_title']}"
    title_escaped = current_full_title.replace("'", "''")

    # --- Формуємо Front Matter для index.md ---
    has_children_fm = 'true' if node['children'] else 'false'
    parent_fm = f"parent: '{parent_full_title.replace("'", "''")}'\n" if parent_full_title else ""
    grand_parent_fm = f"grand_parent: '{grand_parent_full_title.replace("'", "''")}'\n" if grand_parent_full_title else ""
    
    index_body = f"# {node['title_with_number']}\n"
    if needs_qa_file:
        index_body += "\n[Перейти до Q&A](./qa.md)\n"

    index_fm_content = f"""---
layout: default
title: '{title_escaped}'
{parent_fm}{grand_parent_fm}nav_order: {node['nav_order']}
has_children: {has_children_fm}
---
"""
    with open(os.path.join(current_path_str, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(index_fm_content + index_body)

    # --- Генерація qa.md, якщо необхідно ---
    if needs_qa_file:
        qa_full_title = f"{node['full_number']} Q&A {node['clean_title']}"
        qa_title_escaped = qa_full_title.replace("'", "''")
        qa_parent_title_escaped = current_full_title.replace("'", "''")
        
        qa_fm_content = f"""---
layout: default
title: '{qa_title_escaped}'
parent: '{qa_parent_title_escaped}'
nav_order: 999
---
"""
        qa_body = f"# {node['full_number']} Q&A {node['clean_title']}\n\n[Повернутись до теми](./index.md)\n"
        with open(os.path.join(current_path_str, 'qa.md'), 'w', encoding='utf-8') as f:
            f.write(qa_fm_content + qa_body)

    # --- Рекурсивний виклик для дочірніх елементів ---
    new_path_parts = path_parts + [node['slug']]
    for child in node['children']:
        # Поточний батько стає дідусем для наступного рівня
        generate_files(child, new_path_parts, parent_full_title=current_full_title, grand_parent_full_title=parent_full_title)

def generate_root_index(output_directory: str):
    """
    Створює головний index.md файл у корені документації.
    """
    root_fm = """---
layout: default
title: Документація
nav_order: 1
has_children: true
---

# Java всеохопна документація

Оберіть розділ для початку.
"""
    
    with open(os.path.join(output_directory, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(root_fm)

def main():
    """
    Головна функція скрипту.
    """
    input_file = "content.md"
    output_directory = "." # Генеруємо файли в поточну директорію

    if not os.path.exists(input_file):
        print(f"Помилка: Файл '{input_file}' не знайдено.")
        return

    print(f"Читання структури з файлу '{input_file}'...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Парсинг структури...")
    structure_tree = parse_structure(content)

    # --- Безпечне очищення ---
    print("Очищення попередньо згенерованих файлів...")
    top_level_dirs_to_delete = [child['slug'] for child in structure_tree.get('children', [])]
    for dirname in top_level_dirs_to_delete:
        if os.path.isdir(dirname):
            print(f"  - Видалення директорії: {dirname}")
            shutil.rmtree(dirname)
    root_index_path = os.path.join(output_directory, 'index.md')
    if os.path.realpath(root_index_path) != os.path.realpath(input_file) and os.path.exists(root_index_path):
        print("  - Видалення кореневого index.md")
        os.remove(root_index_path)
    # --- Кінець безпечного очищення ---

    print(f"Генерація файлів та папок у поточній директорії...")
    generate_files(structure_tree, [output_directory])
    generate_root_index(output_directory)

    print("\nГотово! Структура документації успішно згенерована.")
    print("Спробуйте запустити 'make dev' знову.")

if __name__ == "__main__":
    main()
