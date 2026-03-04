# Open Source Credits

`vetka-elisya-runtime` is built on open APIs and OSS runtimes in the LLM
inference ecosystem.

## Runtime and Core Libraries

- Python
  - https://www.python.org/
  - License: PSF License.
  - Role: runtime for routing, provider adapters, and fallback orchestration.

- HTTPX
  - https://github.com/encode/httpx
  - License: BSD-3-Clause.
  - Role: HTTP client for provider API communication.

## Provider Ecosystem References

- OpenAI API
  - https://platform.openai.com/docs
  - Role: provider endpoint and tool-calling runtime lane.

- Anthropic API
  - https://docs.anthropic.com/
  - Role: provider endpoint and tool use runtime lane.

- Google Gemini API
  - https://ai.google.dev/
  - Role: provider endpoint and function/tool execution lane.

- Ollama
  - https://github.com/ollama/ollama
  - License: MIT.
  - Role: local model runtime lane.

- OpenRouter
  - https://openrouter.ai/
  - Role: multi-provider routing gateway lane.

## Notes

- Preserve upstream terms/licenses and attribution when adapting provider code.
- This module references provider APIs; verify usage terms for each deployment.
