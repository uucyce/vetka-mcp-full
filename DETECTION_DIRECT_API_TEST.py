#!/usr/bin/env python3
"""
Direct VETKA API test script - no MCP dependencies
"""

import asyncio
import json
import sys

async def test_vetka_direct_api(model: str, test_name: str, message: str) -> dict:
    """Test VETKA API directly for truncation analysis"""
    print(f"\n=== {test_name} START ===")
    print(f"Model: {model}")
    print(f"Message: {message[:100]}...")
    
    payload = {
        "message": message,
        "model": model,
        "conversation_id": f"test-{int(time.time())}",
        "max_tokens": 999999,
        "temperature": 0.1
    }
    
    try:
        print(f"Sending request...")
        result = await call_vetka_api(model, message)
        
        if result["success"]:
            print(f"✅ Success!")
            print(f"   Model: {result.get('model', 'unknown')}")
            print(f"   Output tokens: {result.get('output_tokens', 0)}")
            print(f"   Response length: {len(result.get('response', '')} characters")
            print(f"   Word count: {len(result.get('response', '').split())} words")
            
            # Check for truncation indicators
            response_content = result.get('response', '')
            trunc_indicators = ['...', 'truncated', '[truncated]', '... [cut off]', 'обрезан', 'incomplete', 'unfinished']
            
            found_trunc = any(indicator in response_content.lower() for indicator in trunc_indicators)
            if found_trunc:
                print(f"❌ НАЙДЕНО ОБРЕЗКА!")
            else:
                print(f"✅ Никакой обрезки не обнаружена")
            
            # Additional checks
            print(f"   Full response received:")
            if len(response_content) > 1000:
                print(f"   Preview: {response_content[:1000]}...")
            else:
                print(f"   Full response ({len(response_content)} chars)")
                print(f"   Response:\n{response_content}\n")
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {"success": False, "error": str(e)}

def test_deepseek_direct_api():
    """Test DeepSeek model directly via VETKA API"""
    return asyncio.run(test_vetka_direct_api(
        model="deepseek/deepseek-chat",
        test_name="DeepSeek Direct API Test"
        message="ТЕСТ ГРОМКОЕ ЗАДАНИЕ: Создай ОГРОМНЫЙ детальный анализ VETKA архитектуры. Минимум 12000 слов. НЕ ПРЕКРАЩАЙ! Это тест проверки обрезки на ~7000 токенов через прямые вызовы API. Проверь все исправления лимитов. Создай artifact DETECT_TRUNCATION_ANALYSIS.md с результатами!"
    ))

def test_grok_direct_api():
    """Test Grok 4 model directly via VETKA API"""
    return asyncio.run(test_vetka_direct_api(
        model="x-ai/grok-4",
        test_name="Grok 4 Direct API Test",
        message="ГРОМКОЕ ЗАДАНИЕ: Проведи ИСЧЕРПЫВАЮЩИЙ анализ VETKA архитектуры. Минимум 12000 слов. НЕ ПРЕКРАЩАЙ НИКОГДА! Это тест проверка обрезки на ~7000 токенов через прямые вызовы API. Если найдешь любые hidden limits - немедленно сообщи!"
    ))

def main():
    """Run comprehensive truncation analysis"""
    print("\n" + "="*60)
    print(f"=== VETKA TRUNCATION INVESTIGATION ===")
    
    print("\n1️⃣ Testing DeepSeek direct API...")
    result1 = await test_deepseek_direct_api()
    
    print("\n2️⃣ Testing Grok 4 direct API...")
    result2 = await test_grok_direct_api()
    
    print("\n3️⃣ Testing basic VETKA API...")
    result3 = await test_vetka_direct_api(
        model="openai/gpt-4o",
        test_name="OpenAI GPT-4o Test",
        message="ТЕСТ БЕЗЛИМИТ: Краткий тест обрезки. НЕ обрезано! Проверь что сейчас НЕ ОБРЕЗАНА!"
    )
    
    print("\n4️⃣ Direct VETKA API tests complete")
    
    # Summary
    results = [result1, result2, result3]
    success_count = sum(1 for r in results if r["success"])
    print(f"\n\n=== SUMMARY ===")
    print(f"Total tests: {len(results)}, Successful: {success_count}/3")
    
    all_success = all(r["success"] for r in results)
    if all_success:
        print("✅ ALL TESTS PASSED - No truncation detected!")
        return True
    else:
        print(f"❌ FAILED - Some tests failed!")
        return False

if __name__ == "__main__":
    asyncio.run(main())
else:
    print("Please specify: deepseek, grok4, gpt-4o or ALL")
    return False