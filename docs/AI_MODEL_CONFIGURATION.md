# 🤖 Configuring Your AI Model

This project uses LiteLLM, which allows you to switch between 100+ different LLM providers just by changing the `LLM_MODEL` name.

## 1. Set your Environment Variable

We use a single, generic environment variable for your API key. Set this in your `.env` file:

```bash
AI_KEY=your_actual_api_key_here
```

## 2. Choose Your Model Name

When setting the `LLM_MODEL` variable, you must use the correct provider prefix. This tells the system where to send your `AI_KEY`.

| Provider | Prefix | Example Model String |
| :------- | :----- | :------------------- |
| Google AI Studio | `gemini/` | `gemini/gemini-1.5-flash` |
| Groq | `groq/` | `groq/llama-3.1-70b-versatile` |
| OpenAI | (None) | `gpt-4o` or `gpt-3.5-turbo` |
| Anthropic | `anthropic/` | `anthropic/claude-3-5-sonnet` |
| Mistral | `mistral/` | `mistral/mistral-large-latest` |
| Ollama (Local) | `ollama/` | `ollama/llama3` |

## 3. Example Configurations

### To use Gemini 1.5 Flash (Default):

```bash
LLM_MODEL=gemini/gemini-1.5-flash
AI_KEY=AIzaSy... (Your Google AI Studio Key)
```

### To switch to Groq:

```bash
LLM_MODEL=groq/llama-3.1-8b-instant
AI_KEY=gsk_... (Your Groq API Key)
```

### To use OpenAI:

```bash
LLM_MODEL=gpt-4o
AI_KEY=sk-... (Your OpenAI API Key)
```

## ⚠️ Common Pitfall: The "Default Credentials" Error

If you use a Google model name (like `gemini-1.5-flash`) **without** the `gemini/` prefix, the system may try to look for "Google Cloud Application Default Credentials" on your machine and fail.

**Always include the prefix** to ensure the API key is used correctly.

## Supported Providers

LiteLLM supports 100+ LLM providers. Here are some popular ones:

| Provider | Prefix | Notes |
| :------- | :----- | :---- |
| Google Gemini | `gemini/` | Fast and cost-effective |
| OpenAI | (none) | Industry standard |
| Anthropic Claude | `anthropic/` | Strong reasoning capabilities |
| Groq | `groq/` | Extremely fast inference |
| Azure OpenAI | `azure/` | Enterprise Azure deployment |
| AWS Bedrock | `bedrock/` | AWS managed LLM service |
| Ollama | `ollama/` | Local model deployment |
| Together AI | `together_ai/` | Open-source models |
| Deepseek | `deepseek/` | Cost-effective alternative |

For a complete list of supported providers and model strings, see the [LiteLLM documentation](https://docs.litellm.ai/docs/providers).

## Troubleshooting

### Model not found error
- Verify the model string format includes the correct prefix
- Check that your API key is valid and has access to the model

### Authentication errors
- Ensure your `AI_KEY` is correct and hasn't expired
- Verify the API key has the necessary permissions for the model

### Rate limiting
- Check your API provider's rate limits
- Consider implementing retry logic in your configuration