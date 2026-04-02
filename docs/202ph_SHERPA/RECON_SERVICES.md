# SHERPA — AI Services Compatibility Matrix
# Phase 202 | Recon: 50 Underdog Services

**Task:** tb_1775156378_36952_1
**Agent:** Eta
**Date:** 2026-04-02
**Gold standard:** DeepSeek (textarea + Enter + DOM `.ds-markdown`) and Kimi

## How to Test a Service

```bash
# Add entry to config/sherpa.yaml (enabled: false)
# Then open browser for manual test:
python sherpa.py --setup --service <name>

# Check:
# 1. textarea visible?    → input_selector found
# 2. fill() + Enter sends? → message appears in chat
# 3. DOM extractable?     → response_selector returns text
# 4. Bot detection?       → captcha / block observed
# 5. Rate limit?          → daily cap, token cap
```

## Compatibility Legend

| Symbol | Meaning |
|--------|---------|
| PASS | Works fully with Sherpa automation |
| PARTIAL | Works but limited (e.g. extraction issues) |
| FAIL | Bot detection / structural block |
| UNTESTED | Not yet tested |

---

## Priority Tier 1 — Most Promising

| Service | URL | textarea | send | DOM extract | bot detect | rate limit | verdict | notes |
|---------|-----|----------|------|-------------|-----------|------------|---------|-------|
| arena.ai | lmarena.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | LMSYS benchmark, always responds, anonymous |
| HuggingChat | huggingface.co/chat | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Open models (Llama, Qwen, Mistral), OSS |
| Mistral Le Chat | chat.mistral.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Large context, code-strong |
| Poe | poe.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | 45+ models, strict rate limits |
| Monica | monica.im | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Browser extension + web UI |
| Diaglam | dialagram.me | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Free router with Qwen/GLM |
| Phind | phind.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Dev-focused, code search + answer |
| Perplexity | perplexity.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Search-augmented, strong recon |

---

## Priority Tier 2 — Chinese Direct (High Potential)

| Service | URL | textarea | send | DOM extract | bot detect | rate limit | verdict | notes |
|---------|-----|----------|------|-------------|-----------|------------|---------|-------|
| Doubao | doubao.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | ByteDance, very large free tier |
| MiniMax | minimaxi.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | MiniMax-01, 1M context |
| ChatGLM | chatglm.cn | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Zhipu direct, strong coding |
| Baichuan | baichuan-ai.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Baichuan-4, Chinese focus |
| 360 AI | ai.360.cn | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Chinese, large free tier |
| Tiangong | tiangong.cn | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Kunlun Tech |
| Spark | xinghuo.xfyun.cn | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | iFlytek Spark |
| Tongyi | tongyi.aliyun.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Alibaba Qwen web interface |
| Sensenova | sensechat.sensetime.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | SenseTime |
| Moonshot Kimi INT | kimi.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | International Kimi, vs kimi.com |

---

## Priority Tier 3 — Western Underdog

| Service | URL | textarea | send | DOM extract | bot detect | rate limit | verdict | notes |
|---------|-----|----------|------|-------------|-----------|------------|---------|-------|
| You.com | you.com/chat | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Search + chat, generous free |
| Pi | pi.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Conversational Inflection AI |
| Cohere Coral | coral.cohere.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Command R+, long context |
| Groq | groq.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Ultra-fast, Llama/Mixtral |
| Together | api.together.ai (playground) | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Multi-model playground |
| Fireworks | fireworks.ai/chat | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Fast inference, many models |
| Lepton | lepton.ai/playground | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Cloud inference, free tier |
| Vercel v0 | v0.dev | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UI code gen, React-focused |
| Bolt | bolt.new | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Full-stack code gen |
| Replit | replit.com/ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Code-first, full sandbox |

---

## Priority Tier 4 — Domain Specific

| Service | URL | textarea | send | DOM extract | bot detect | rate limit | verdict | notes |
|---------|-----|----------|------|-------------|-----------|------------|---------|-------|
| Blackbox AI | blackbox.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Code search + chat, generous |
| Codeium | codeium.com/chat | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Dev-focused, context-aware |
| Tabnine | app.tabnine.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Code assistant |
| Sourcegraph Cody | sourcegraph.com/cody | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Codebase-aware |
| AskCodi | askcodi.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Code-only, free tier |
| Forefront | forefront.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Multi-model, free messages |
| Andi | andisearch.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Search-first, answers only |
| Elicit | elicit.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Research papers, extraction |
| Consensus | consensus.app | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Academic research |

---

## Priority Tier 5 — Misc / Experimental

| Service | URL | textarea | send | DOM extract | bot detect | rate limit | verdict | notes |
|---------|-----|----------|------|-------------|-----------|------------|---------|-------|
| Ora | ora.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Multi-model, GPT-4 free tier |
| OpenRouter | openrouter.ai/chat | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | 200+ models router |
| Nat.dev | nat.dev | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Model comparison playground |
| Chub AI | chub.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Roleplay-focused, large context |
| SpicyChat | spicychat.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Uncensored, research interest |
| Venice | venice.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Privacy-first, local inference |
| Jan | jan.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Local-first (desktop app) |
| LM Studio | lmstudio.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Local only, no web UI |
| TextSynth | textsynth.com | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Very small free tier |
| Forefront | chat.forefront.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | alt URL |
| Nomi | nomi.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Companion AI |
| Character.ai | character.ai | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | Roleplay, not code-focused |

---

## Already Tested (Reference)

| Service | Verdict | Notes |
|---------|---------|-------|
| DeepSeek | PASS (GOLD) | `.ds-markdown`, unlimited, best selector |
| Kimi | PASS | `.assistant-message`, good DOM |
| Grok | FAIL | Bot protection blocks Playwright |
| Qwen chat.qwen.ai | FAIL | Cannot find input reliably |
| Claude.ai | PARTIAL | Copies prompt instead of response |
| ChatGPT | PARTIAL | Copies prompt instead of response |
| cto.new | UNTESTED | Slow but produces full code |

---

## Top-5 Recommended (to be filled after testing)

1. TBD
2. TBD
3. TBD
4. TBD
5. TBD

---

## Selectors Quick Reference (add to sherpa.yaml)

```yaml
# arena.ai (LMSYS)
input_selector: 'textarea'
send_selector: 'button[aria-label="Send"], button:has-text("Send")'
response_selector: '.message-content, .prose, [class*="message"]'

# HuggingChat
input_selector: 'textarea'
send_selector: 'button[type="submit"]'
response_selector: '.prose, [class*="message"]'

# Mistral Le Chat
input_selector: 'textarea'
send_selector: 'button[aria-label*="Send"], button[type="submit"]'
response_selector: '[class*="message"], .prose'

# Phind
input_selector: 'textarea'
send_selector: 'button[type="submit"]'
response_selector: '[class*="answer"], [class*="response"], .prose'

# Groq
input_selector: 'textarea'
send_selector: 'button[type="submit"]'
response_selector: '[class*="message"], .prose, article'

# Doubao (ByteDance)
input_selector: 'textarea'
send_selector: 'button[aria-label*="发送"], button[type="submit"]'
response_selector: '[class*="message"], [class*="content"]'
```

---

*Last updated: 2026-04-02 by Eta (Harness Engineer)*
