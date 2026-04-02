# SHERPA — AI Services Probe Report

**Generated:** 2026-04-02 22:22 by `python sherpa.py --probe`
**Total probed:** 40 | **PASS:** 1 | **NEED_LOGIN:** 7 | **NO_INPUT:** 28 | **FAIL:** 1 | **BOT:** 0

---

## Legend

- **PASS** — textarea found, no login required. Ready to use.
- **NEED_LOGIN** — textarea found but requires account. Run `--setup --service <name>` then re-probe.
- **NO_INPUT** — page loads but textarea not found (SPA needs more wait, or different selector).
- **FAIL** — timeout / page didn't load.
- **BOT** — Cloudflare/captcha. Playwright blocked.

---

## Key Finding: NO bot detection on ANY service

Zero Cloudflare blocks. All services allow Playwright navigation. The main issue is **SPA textarea loading** — most modern chat UIs render textarea after JS init (needs longer wait or session cookie).

---

## Raw Probe Results

| profile | loads | input | bot | popup | login | models | rate_limit | verdict | notes |
|---------|-------|-------|-----|-------|-------|--------|------------|---------|-------|
| deepseek_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA — textarea loads after JS init |
| grok_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| qwen_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| claude_1 | Y | N | N | N | N | Y | usage limit | NO_INPUT | Model selector visible. SPA. |
| chatgpt_1 | Y | Y | N | Y | Y | Y | - | NEED_LOGIN | contenteditable div, not textarea |
| deepseek_2 | Y | N | N | N | N | N | - | NO_INPUT | same as deepseek_1 |
| kimi_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| kimi_2 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| cto_1 | Y | Y | N | Y | Y | Y | - | NEED_LOGIN | textarea works |
| **arena_1** | Y | Y | N | Y | N | N | - | **PASS** | Anonymous mode! No login needed |
| huggingchat_1 | Y | Y | N | Y | Y | N | - | NEED_LOGIN | textarea works |
| mistral_1 | Y | Y | N | Y | Y | N | - | NEED_LOGIN | textarea works |
| phind_1 | Y | N | N | N | N | N | - | NO_INPUT | 404 — URL changed |
| perplexity_1 | Y | N | N | N | N | Y | - | NO_INPUT | Model selector visible. SPA. |
| you_1 | Y | N | N | Y | N | N | - | NO_INPUT | SPA |
| groq_1 | Y | N | N | N | N | N | subscribe | NO_INPUT | Rate limit hint in text |
| cohere_1 | Y | N | N | Y | N | N | - | NO_INPUT | Login page title |
| doubao_1 | Y | N | N | N | N | N | - | NO_INPUT | Chinese SPA |
| minimax_1 | Y | N | N | N | N | N | - | NO_INPUT | Chinese SPA |
| chatglm_1 | Y | N | N | N | N | N | - | NO_INPUT | Chinese SPA — 智谱清言 |
| tongyi_1 | Y | N | N | N | N | Y | - | NO_INPUT | Model selector visible |
| spark_1 | Y | N | N | N | N | N | - | NO_INPUT | Chinese SPA |
| tiangong_1 | Y | N | N | N | N | N | - | NO_INPUT | Chinese SPA — 首页 |
| baichuan_1 | Y | N | N | N | N | N | - | NO_INPUT | Chinese SPA — 百小应 |
| sensenova_1 | N | N | N | N | N | N | - | FAIL | Timeout 20s |
| blackbox_1 | Y | N | N | N | N | Y | - | NO_INPUT | Model selector visible |
| pi_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| poe_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| monica_1 | Y | Y | N | Y | Y | N | - | NEED_LOGIN | textarea works |
| forefront_1 | Y | N | N | N | N | N | - | NO_INPUT | Empty page |
| openrouter_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| venice_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| together_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| fireworks_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| ora_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| nat_1 | Y | N | N | N | N | N | - | NO_INPUT | SPA |
| bolt_1 | Y | Y | N | Y | Y | N | - | NEED_LOGIN | textarea works — code gen |
| v0_1 | Y | Y | N | Y | Y | Y | limit reached | NEED_LOGIN | Model selector, rate limit hint |
| codeium_1 | Y | N | N | N | N | N | - | NO_INPUT | 404 — URL changed |
| andi_1 | Y | N | N | N | N | N | - | NO_INPUT | input[type=text] not in textarea |

---

## Analysis

### Why NO_INPUT for known-working services (DeepSeek, Kimi)?
Probe runs headless without cookies — SPAs require:
- Session cookie to render chat UI (deepseek, kimi — show landing page without login)
- Additional JS wait time (2s not enough for heavy React apps)
- These services ARE working in Sherpa with proper `--setup` login

### Probe limitations
- 2s JS wait — insufficient for heavy SPAs
- No cookies = landing page instead of chat UI for many services
- `contenteditable` div (ChatGPT) not matched by `textarea` selector — needs config fix

---

## Top-5 Recommended

| Rank | Service | Why |
|------|---------|-----|
| 1 | **arena_1** (lmarena.ai) | ONLY true anonymous PASS. No login. Rotates 50+ models. Unlimited. |
| 2 | **mistral_1** (chat.mistral.ai) | textarea confirmed, strong coding, large context. After --setup. |
| 3 | **huggingchat_1** (huggingface.co/chat) | textarea confirmed, open models (Llama/Qwen/Mistral). After --setup. |
| 4 | **monica_1** (monica.im) | textarea confirmed, all-in-one AI. After --setup. |
| 5 | **chatgpt_1** (chatgpt.com) | input confirmed (contenteditable). Fix selector + --setup. |

---

## Action Plan

### 1. Enable arena immediately — no login needed
```yaml
# config/sherpa.yaml — change arena_1 to enabled: true
```

### 2. Fix ChatGPT selector
```yaml
input_selector: 'div[contenteditable="true"]'  # not textarea
```

### 3. Setup login for NEED_LOGIN services (user action required)
```bash
python sherpa.py --setup --service mistral    # opens chat.mistral.ai
python sherpa.py --setup --service huggingchat
python sherpa.py --setup --service monica
python sherpa.py --setup --service cto
python sherpa.py --setup --service bolt       # code-gen, not recon
```

### 4. Re-probe after login to verify extraction works
```bash
python sherpa.py --probe --service mistral
```

### 5. Chinese SPAs — need longer wait + session
Most Chinese services (doubao, chatglm, tongyi) are SPA-based. Need:
- Login session (account required)
- Probe with `--visible` to inspect actual DOM
- Possibly `wait_for_selector` instead of fixed 2s wait

---

## Services to Disable / Skip

| Service | Reason |
|---------|--------|
| phind_1 | 404 — URL dead |
| codeium_1 | 404 — URL changed (now Windsurf) |
| sensenova_1 | Timeout — unreachable |
| forefront_1 | Empty page |

---

*Run `python sherpa.py --probe --visible` to inspect DOM of failing services.*
*Run `python sherpa.py --probe` after --setup to verify login worked.*
