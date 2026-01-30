"""
Collect training data for Llama 3.1 fine-tuning
Create dataset from classification examples
"""

TRAINING_DATASET = [
    # MICRO - Simple UI changes
    {"task": "Добавь кнопку логина", "complexity": "MICRO"},
    {"task": "Измени цвет фона на синий", "complexity": "MICRO"},
    {"task": "Добавь поле email в форму", "complexity": "MICRO"},
    {"task": "Изменить размер шрифта заголовка", "complexity": "MICRO"},
    {"task": "Добавить иконку в меню", "complexity": "MICRO"},
    
    # SMALL - Simple feature
    {"task": "Создай форму контакта", "complexity": "SMALL"},
    {"task": "Добавь простой поиск по странице", "complexity": "SMALL"},
    {"task": "Реализуй переключатель темы (light/dark)", "complexity": "SMALL"},
    {"task": "Добавь валидацию email", "complexity": "SMALL"},
    {"task": "Создай модальное окно подтверждения", "complexity": "SMALL"},
    
    # MEDIUM - Standard feature
    {"task": "Добавь систему аутентификации с JWT", "complexity": "MEDIUM"},
    {"task": "Реализуй поиск по базе данных", "complexity": "MEDIUM"},
    {"task": "Создай дашборд с метриками", "complexity": "MEDIUM"},
    {"task": "Добавь REST API для пользователей", "complexity": "MEDIUM"},
    {"task": "Реализуй кэширование результатов", "complexity": "MEDIUM"},
    {"task": "Интегрируй платежную систему Stripe", "complexity": "MEDIUM"},
    
    # LARGE - Complex system change
    {"task": "Переделай систему логирования", "complexity": "LARGE"},
    {"task": "Добавь микросервис обработки очереди", "complexity": "LARGE"},
    {"task": "Реализуй реальное время уведомлений (WebSocket)", "complexity": "LARGE"},
    {"task": "Добавь полнотекстовый поиск с Elasticsearch", "complexity": "LARGE"},
    {"task": "Переделай работу с авторизацией на OAuth2", "complexity": "LARGE"},
    
    # EPIC - Full system redesign
    {"task": "Переделай всю архитектуру системы на микросервисы", "complexity": "EPIC"},
    {"task": "Перейди с SQL на NoSQL для всего проекта", "complexity": "EPIC"},
    {"task": "Реализуй полную систему обработки видео с AI", "complexity": "EPIC"},
    {"task": "Переделай фронтенд с jQuery на React + TypeScript", "complexity": "EPIC"},
    {"task": "Добавь распределённый кэш и очередь для всей системы", "complexity": "EPIC"},
]

# Экспортируем в JSON для fine-tuning
import json

def export_dataset(filename="vetka_classification_dataset.json"):
    """Export dataset for Unsloth fine-tuning"""
    
    # Преобразуем в формат для fine-tuning
    formatted = []
    for item in TRAINING_DATASET:
        formatted.append({
            "text": f"Task: {item['task']}\nComplexity: {item['complexity']}"
        })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(formatted, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Dataset exported: {filename}")
    print(f"   Total examples: {len(formatted)}")
    print(f"   Size: {len(json.dumps(formatted))} bytes")
    
    return formatted

def export_csv(filename="vetka_classification_dataset.csv"):
    """Export as CSV for analysis"""
    
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['task', 'complexity'])
        writer.writeheader()
        writer.writerows(TRAINING_DATASET)
    
    print(f"✅ CSV exported: {filename}")
    
    # Print statistics
    from collections import Counter
    counts = Counter(item['complexity'] for item in TRAINING_DATASET)
    print(f"   Distribution:")
    for complexity, count in sorted(counts.items()):
        print(f"     {complexity}: {count}")

if __name__ == "__main__":
    export_dataset()
    export_csv()
    
    # Show dataset info
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total examples: {len(TRAINING_DATASET)}")
    print(f"   Ready for: Unsloth LoRA fine-tuning")
    print(f"   Model: Llama 3.1 8B")
    print(f"   Format: JSON (text) or CSV")
