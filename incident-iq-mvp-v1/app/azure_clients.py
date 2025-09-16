import os, base64, hashlib, json
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv

# Load project .env and override any existing env vars (prevents placeholder shell vars)
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path, override=True)
else:
    # still call load_dotenv without path to allow default behavior
    load_dotenv()

class Settings(BaseModel):
    AZURE_SEARCH_ENDPOINT: str
    AZURE_SEARCH_API_KEY: str
    AZURE_SEARCH_INDEX: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT: str  # text-embedding and chat model names reused via suffixes
    AZURE_OPENAI_CHAT_DEPLOYMENT: str
    BING_SEARCH_ENDPOINT: str | None = None
    BING_SEARCH_API_KEY: str | None = None

def load_settings() -> Settings:
    required = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY",
        "AZURE_SEARCH_INDEX",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
    ]
    for k in required:
        if not os.getenv(k):
            raise RuntimeError(f"환경변수 {k} 가 설정되지 않았습니다.")
    # Basic placeholder detection: reject common placeholder patterns
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    if any(token in endpoint for token in ("<your-search-name>", "%3cyour-search-name%3e", "your-search-name", "<your", "%3c")):
        raise RuntimeError(
            "AZURE_SEARCH_ENDPOINT looks like a placeholder (e.g. '<your-search-name>.search.windows.net').\n"
            "Please set a real endpoint in the environment or in the project's .env file."
        )
    return Settings(
        AZURE_SEARCH_ENDPOINT=os.environ["AZURE_SEARCH_ENDPOINT"],
        AZURE_SEARCH_API_KEY=os.environ["AZURE_SEARCH_API_KEY"],
        AZURE_SEARCH_INDEX=os.environ["AZURE_SEARCH_INDEX"],
        AZURE_OPENAI_ENDPOINT=os.environ["AZURE_OPENAI_ENDPOINT"],
        AZURE_OPENAI_API_KEY=os.environ["AZURE_OPENAI_API_KEY"],
        AZURE_OPENAI_DEPLOYMENT=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        AZURE_OPENAI_CHAT_DEPLOYMENT=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        BING_SEARCH_ENDPOINT=os.getenv("BING_SEARCH_ENDPOINT"),
        BING_SEARCH_API_KEY=os.getenv("BING_SEARCH_API_KEY"),
    )

def search_client(settings: Settings) -> SearchClient:
    return SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=settings.AZURE_SEARCH_INDEX,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_API_KEY),
    )

def index_client(settings: Settings) -> SearchIndexClient:
    return SearchIndexClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_API_KEY),
    )
