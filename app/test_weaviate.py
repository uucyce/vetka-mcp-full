#!/usr/bin/env python3
"""Тест подключения к Weaviate"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import WEAVIATE_URL
import weaviate

print(f"🌳 Тестирование подключения к Weaviate")
print(f"URL: {WEAVIATE_URL}")

try:
    client = weaviate.connect_to_local(host="localhost", port=8080)
    print("✅ Подключение к Weaviate успешно!")
    
    # Проверяем метаданные
    meta = client.get_meta()
    print(f"Версия Weaviate: {meta['version']}")
    
    client.close()
    
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    sys.exit(1)