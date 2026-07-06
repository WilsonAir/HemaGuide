"""
LLM Client Factory

Creates clients for four LLM backends:
- openai: OpenAI API (requires OPENAI_API_KEY)
- ollama-local: Local Ollama server at localhost:11434
- ollama-cloud: Ollama Cloud API (requires OLLAMA_API_KEY)
- vllm: Local vLLM OpenAI-compatible server (default http://127.0.0.1:8010/v1)
"""

import os

from openai import OpenAI

OLLAMA_LOCAL_URL = 'http://localhost:11434'
OLLAMA_CLOUD_URL = 'https://ollama.com'
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', '').rstrip('/') or None
OPENAI_DEFAULT_DECISION_MODEL = os.getenv('OPENAI_DECISION_MODEL', 'qwen-plus')
OPENAI_DEFAULT_EXTRACTION_MODEL = os.getenv('OPENAI_EXTRACTION_MODEL', 'qwen-flash')
DEFAULT_LLM_MODE = os.getenv('DEFAULT_LLM_MODE', 'openai')
VLLM_BASE_URL = os.getenv('VLLM_BASE_URL', 'http://127.0.0.1:8010/v1')
VLLM_DEFAULT_MODEL = os.getenv('VLLM_MODEL', 'gpt-oss-20b')

LLM_MODE_CHOICES = ('openai', 'ollama-local', 'ollama-cloud', 'vllm')


def create_client(llm_mode: str, api_key: str = None):
    """Create LLM client based on mode.

    Args:
        llm_mode: Backend mode - 'openai', 'ollama-local', 'ollama-cloud', or 'vllm'
        api_key: API key (required for openai and ollama-cloud modes)

    Returns:
        OpenAI client (for openai/vllm) or Ollama Client (for ollama-local/ollama-cloud)

    Raises:
        ValueError: If api_key is required but not provided
    """
    if llm_mode == 'ollama-cloud':
        from ollama import Client
        if not api_key:
            raise ValueError("API key required for ollama-cloud mode")
        return Client(
            host=OLLAMA_CLOUD_URL,
            headers={'Authorization': f"Bearer {api_key}"}
        )
    if llm_mode == 'ollama-local':
        from ollama import Client
        return Client(host=OLLAMA_LOCAL_URL)
    if llm_mode == 'vllm':
        return OpenAI(
            base_url=VLLM_BASE_URL,
            api_key=api_key or os.getenv('VLLM_API_KEY', 'EMPTY'),
        )
    # openai (optional OPENAI_BASE_URL for DashScope / Azure / other compatible APIs)
    if not api_key:
        raise ValueError("API key required for openai mode")
    if OPENAI_BASE_URL:
        return OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
    return OpenAI(api_key=api_key)


def resolve_api_key(
    llm_mode: str,
    mode_config: dict,
    explicit_key: str | None = None,
) -> str:
    """Resolve API key for a backend mode."""
    if explicit_key:
        return explicit_key

    env_name = mode_config.get('api_key_env')
    if env_name:
        key = os.getenv(env_name)
        if not key:
            raise ValueError(f"API key not found. Set {env_name} environment variable.")
        return key

    if llm_mode == 'vllm':
        return os.getenv('VLLM_API_KEY', 'EMPTY')
    return 'ollama'


def is_ollama_mode(llm_mode: str) -> bool:
    """Check if the mode is an Ollama-based backend."""
    return llm_mode in ('ollama-cloud', 'ollama-local')


def is_ollama_client(llm_mode: str) -> bool:
    """Check if the mode uses native Ollama Python client."""
    return llm_mode in ('ollama-cloud', 'ollama-local')


def is_openai_compatible(llm_mode: str) -> bool:
    """Check if the mode uses the OpenAI Python client."""
    return llm_mode in ('openai', 'vllm')


def get_default_decision_model(llm_mode: str | None = None) -> str:
    """Default decision/routing model for the given backend mode."""
    mode = llm_mode or DEFAULT_LLM_MODE
    if mode == 'openai':
        return OPENAI_DEFAULT_DECISION_MODEL
    if mode == 'vllm':
        return VLLM_DEFAULT_MODEL
    return 'gpt-oss:120b'


def get_default_extraction_model(llm_mode: str | None = None) -> str:
    """Default document extraction model for the given backend mode."""
    mode = llm_mode or DEFAULT_LLM_MODE
    if mode == 'openai':
        return OPENAI_DEFAULT_EXTRACTION_MODEL
    if mode == 'vllm':
        return VLLM_DEFAULT_MODEL
    return 'gpt-oss:120b'


def is_ollama_cloud(llm_mode: str) -> bool:
    """Check if the mode is ollama-cloud (uses Ollama Python client)."""
    return llm_mode == 'ollama-cloud'
