"""
LLM Client Factory

Creates clients for three LLM backends:
- openai: OpenAI API (requires OPENAI_API_KEY)
- ollama-local: Local Ollama server at localhost:11434
- ollama-cloud: Ollama Cloud API (requires OLLAMA_API_KEY)
"""

from openai import OpenAI

OLLAMA_LOCAL_URL = 'http://localhost:11434'
OLLAMA_CLOUD_URL = 'https://ollama.com'


def create_client(llm_mode: str, api_key: str = None):
    """Create LLM client based on mode.

    Args:
        llm_mode: Backend mode - 'openai', 'ollama-local', or 'ollama-cloud'
        api_key: API key (required for openai and ollama-cloud modes)

    Returns:
        OpenAI client (for openai) or Ollama Client (for ollama-local/ollama-cloud)

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
    elif llm_mode == 'ollama-local':
        from ollama import Client
        return Client(host=OLLAMA_LOCAL_URL)
    else:  # openai
        if not api_key:
            raise ValueError("API key required for openai mode")
        return OpenAI(api_key=api_key)


def is_ollama_mode(llm_mode: str) -> bool:
    """Check if the mode is an Ollama-based backend.

    Args:
        llm_mode: Backend mode

    Returns:
        True if ollama-cloud or ollama-local
    """
    return llm_mode in ('ollama-cloud', 'ollama-local')


def is_ollama_client(llm_mode: str) -> bool:
    """Check if the mode uses native Ollama Python client.

    Args:
        llm_mode: Backend mode

    Returns:
        True if ollama-cloud or ollama-local
    """
    return llm_mode in ('ollama-cloud', 'ollama-local')


def is_ollama_cloud(llm_mode: str) -> bool:
    """Check if the mode is ollama-cloud (uses Ollama Python client).

    Args:
        llm_mode: Backend mode

    Returns:
        True if ollama-cloud
    """
    return llm_mode == 'ollama-cloud'
