"""Constants for OpenRouter Bridge."""

DOMAIN = "openrouter_bridge"

CONF_API_KEY = "api_key"
CONF_DEFAULT_MODEL = "default_model"
CONF_ALLOW_MODEL_OVERRIDE = "allow_model_override"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PROXY_BASE_PATH = "/api/openrouter_bridge"

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

# Models suitable for onboarding (free tier on OpenRouter)
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-r1:free",
    "mistralai/mistral-7b-instruct:free",
]

# Good paid models for Claude Code use
RECOMMENDED_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.5-haiku",
    "anthropic/claude-opus-4",
    "google/gemini-2.0-flash-001",
    "openai/gpt-4o",
    "meta-llama/llama-3.3-70b-instruct",
]

STATS_KEY = "_stats"
