# Eta — Harness Engineer 2 — Role Memory

## Главный принцип диагностики

**Читай ошибку буквально, не интерпретируй.**

Когда что-то не работает — сначала прочитай точный текст ошибки из логов, не из UI и не из чужих слов. Разница в одном слове меняет весь диагноз.

Пример из зеркал:
- `denied to github-actions[bot]` → работает GITHUB_TOKEN (credential helper перехватил)
- `denied to danilagoleen` → PAT дошёл, но нет прав на репо

Три раза меняли токен — не помогало. Помогло прочитать `github-actions[bot]` и понять: это подпись GITHUB_TOKEN, а не PAT.

---

## Опыт: Наладка GitHub Actions зеркал (2026-04-02/05)

### Что сломалось
11 публичных зеркальных репо перестали синхронизироваться. Все одновременно — 403.

### Что не сработало (и почему)
1. **Fine-grained PAT** — credential helper в `actions/checkout@v4` перехватывает git push и подменяет на GITHUB_TOKEN. PAT не доходит до remote URL.
2. **Classic PAT** — та же проблема по той же причине.
3. **"Submodule — просто warning"** — после фикса credentials checkout упал именно на submodule scan.

### Что сработало
```yaml
- uses: actions/checkout@v4
  with:
    persist-credentials: false  # ← одна строка
```
Без этого флага — любой PAT бесполезен в скриптах которые делают git push.

### Сигналы для быстрой диагностики
| Что видишь в логе | Что это значит |
|-------------------|----------------|
| `denied to github-actions[bot]` | GITHUB_TOKEN используется (не PAT) |
| `Contents: read` в permissions | GITHUB_TOKEN read-only — push невозможен |
| Все зеркала падают одновременно | Единый корень (токен/auth), не per-repo |
| Checkout падает с exit 128 | Проверь stale submodule gitlinks: `git ls-files --stage | grep "^160000"` |

### Команда для диагностики stale submodules
```bash
git ls-files --stage | grep "^160000" | awk '{print $4}'
# Если нет .gitmodules — все эти записи стальные, удалить:
git rm --cached <path1> <path2> ...
```

---

## Архитектура памяти роли

Два уровня — знать когда тянуться за каждым:

- **`memory/roles/Eta/MEMORY.md`** (этот файл) — личная память, грузится первой. Мой характер, накопленный опыт, правила поведения. Приоритет при загрузке сессии.
- **`docs/190_ph_CUT_WORKFLOW_ARCH/feedback/`** — коллективная история всех агентов. Грепать когда нужно увидеть полную картину и прошлые векторы — чтобы продолжить развитие, а не изобретать колесо.

---

## Правила для будущих сессий

- **PAT + GitHub Actions:** всегда `persist-credentials: false` в checkout если скрипт делает push в другие репо
- **Classic PAT лучше Fine-grained** для multi-repo mirror workflows — `repo` scope покрывает всё без перечисления
- **`gh run view RUN_ID --log-failed`** — самый быстрый способ получить полные логи без браузера
- **Qdrant volume:** реальные данные в `qdrant_storage`, docker-compose должен использовать `external: true, name: qdrant_storage`

---

## PAT rotation reminder
Текущий `PUBLIC_MIRROR_TOKEN` создан: **2026-04-05** (Classic PAT, `ghp_k1...`)
Обновить до: **2027-04-05**
