# Obscurify.ai provider for Hermes Agent

Adds [Obscurify.ai](https://obscurify.ai/?utm_source=hermes) to [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a model provider: pick **Obscurify.ai** in `hermes model`, or pass `--provider obscurify`.

Obscurify.ai is a privacy-focused, OpenAI-compatible API to 200+ models (DeepSeek, GLM, Kimi, Qwen, GPT, Claude, Gemini, Llama and more). Text requests only use zero-data-retention routes, prompts and responses aren't stored on its servers, and accounts are a random account number with no email.

What the plugin adds over a custom endpoint:

- **A model list Hermes can run.** It comes from the public `https://obscurify.ai/v1/models` catalog, minus decision models (they only answer structured questions) and models under the 64K-token context Hermes needs.
- **Context windows** from the same catalog.
- **Reasoning effort** sent as `reasoning_effort` (`none` through `max`). Models that don't reason ignore it.

## Install

```sh
hermes plugins install obscurify-provider
```

Or straight from this repository, pinned to a reviewed commit:

```sh
hermes plugins install https://github.com/Obscurify-ai/hermes-obscurify-provider --ref FULL_COMMIT_SHA
```

Needs Hermes 0.22.5 or newer and no other Python packages.

## Configure

1. Create an account at [obscurify.ai](https://obscurify.ai/?utm_source=hermes). You get a random account number: no email, no password.
2. Add a balance. The API works on every plan with a positive balance. Frontier models need the Casual plan or higher, and uncensored models need Pro.
3. On [obscurify.ai/account](https://obscurify.ai/account), click **Show API Key**, then put the key in your Hermes profile's environment:

```sh
export OBSCURIFY_API_KEY="sk-obs1_..."
```

Pick the provider and a model:

```sh
hermes model --provider obscurify
```

or run a one-shot request:

```sh
hermes -z "Reply with exactly: ok" --provider obscurify -m deepseek/deepseek-v4-flash
```

Good starting models: `deepseek/deepseek-v4-flash` (default auxiliary model), `z-ai/glm-5.3`, `moonshotai/kimi-k2-0905`, `qwen/qwen3-coder`. Prices per model: [obscurify.ai/model_cards](https://obscurify.ai/model_cards?utm_source=hermes).

## Disclosure

The plugin registers one model provider at import and nothing else: no tools, hooks, commands or background threads. Chat requests go to `https://obscurify.ai/v1` through Hermes' own client, with `OBSCURIFY_API_KEY`, which Hermes reads. The plugin itself only fetches the public model catalog (`GET https://obscurify.ai/v1/models`, no credentials), at most once an hour per process, to build the model list and context windows. It reads and writes no files and starts no processes. Using a model costs money from your Obscurify.ai balance at that model's price.

## Tested

With Hermes 0.22.5 and `main` (2026-10-28), using a Pay As You Go key:

- `hermes plugins validate --install-deps .` passes, including the security scan.
- `hermes -z ... --provider obscurify -m meta-llama/llama-3.3-70b-instruct` answers.
- With `deepseek/deepseek-v4-flash`, Hermes wrote a file through its file tool.

## License

MIT
