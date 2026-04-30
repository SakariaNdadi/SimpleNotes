# LLM Configuration

Notes uses [LiteLLM](https://docs.litellm.ai) to support 100+ LLM providers.
Configure your LLM in Settings → AI / LLM after logging in.

## Cloud Providers

| Provider | Provider name | Model example | Base URL |
| -------- | ------------- | ------------- | -------- |
| OpenAI | `openai` | `gpt-4o` | *(leave empty)* |
| Anthropic | `anthropic` | `claude-sonnet-4-6` | *(leave empty)* |
| Google Gemini | `gemini` | `gemini/gemini-2.0-flash` | *(leave empty)* |
| Mistral | `mistral` | `mistral/mistral-large-latest` | *(leave empty)* |
| Cohere | `cohere` | `command-r-plus` | *(leave empty)* |

## Self-Hosted via Ollama

1. Install [Ollama](https://ollama.com)
2. Pull a model: `ollama pull gemma3` or `ollama pull deepseek-r1`
3. In Settings → AI, add:
   - **Provider name:** `ollama`
   - **Model name:** `ollama/gemma3` (or `ollama/deepseek-r1`, `ollama/llama3.2`, etc.)
   - **Base URL:** `http://localhost:11434` (or your Ollama server address)
   - **API Key:** *(leave empty)*

## Any OpenAI-Compatible Endpoint

Works with llama.cpp server, vLLM, LM Studio, Jan, etc.:

- **Provider name:** `custom`
- **Model name:** your model name (e.g. `local-model`)
- **Base URL:** `http://localhost:8080` (your server's base URL — without `/v1`)
- **API Key:** *(leave empty or set if required)*

## Fallback Behavior

If LiteLLM can't reach your endpoint, the app falls back to a direct `httpx` call to `{base_url}/v1/chat/completions` using the OpenAI API format.

## API Key Security

API keys are encrypted at rest using Fernet symmetric encryption. The encryption key is generated automatically on first run and stored in the database — no configuration required. Keys are never exposed in the UI after saving.
