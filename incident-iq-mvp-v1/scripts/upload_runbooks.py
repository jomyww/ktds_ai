import os, glob, json, uuid, datetime, httpx, re
from dotenv import load_dotenv, find_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

dotenv_path = find_dotenv()
if dotenv_path:
    # override=True ensures .env values replace any existing shell placeholders
    load_dotenv(dotenv_path, override=True)
    print(f"Loaded .env from: {dotenv_path} (overriding shell environment variables)")
else:
    print("No .env file found; relying on environment variables.")
SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.environ.get("AZURE_SEARCH_API_KEY")
env_index = os.getenv("AZURE_SEARCH_INDEX")
if env_index:
    INDEX_NAME = env_index
else:
    # if not provided, try to find the latest auto-generated index that matches the
    # pattern created by create_search_index.py: incident-runbooks-v{dim}-YYYYMMDDTHHMMSSZ
    from azure.search.documents.indexes import SearchIndexClient
    from azure.core.credentials import AzureKeyCredential
    client = SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(SEARCH_KEY))
    all_names = list(client.list_index_names())
    # filter for pattern
    import re
    pattern = re.compile(rf"^incident-runbooks-v\d+-\d{{8}}T\d{{6}}Z$")
    candidates = [n for n in all_names if pattern.match(n)]
    if candidates:
        # pick the latest by lexicographic order (timestamp suffix is ISO-like)
        INDEX_NAME = sorted(candidates)[-1]
    else:
        INDEX_NAME = "incident-runbooks"

def _is_placeholder(val: str) -> bool:
    if not val:
        return True
    lv = val.lower()
    if '<' in val or 'your-search-name' in lv or '%3c' in lv or 'your-key' in lv:
        return True
    return False

if _is_placeholder(SEARCH_ENDPOINT) or _is_placeholder(SEARCH_KEY):
    print("Error: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set to your real Azure Search endpoint and admin key.")
    print("Example (PowerShell):")
    print("  $env:AZURE_SEARCH_ENDPOINT='https://<your-search-name>.search.windows.net'")
    print("  $env:AZURE_SEARCH_API_KEY='<your-search-admin-key>'")
    raise SystemExit(1)

AOAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AOAI_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
EMBED_DEPLOY = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

if not AOAI_ENDPOINT or not AOAI_KEY or not EMBED_DEPLOY:
    print("Error: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT must be set.")
    raise SystemExit(1)

DATA_DIR = os.getenv("DATA_DIR", "data/runbooks")

def md_to_text(md: str) -> str:
    # simple cleaner
    t = re.sub(r"`{1,3}[^`]*`{1,3}", " ", md, flags=re.S)
    t = re.sub(r"#+\s*", "", t)
    return t

def embed(texts):
    #url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_DEPLOY}/embeddings?api-version=2024-06-01"
    url = f"{AOAI_ENDPOINT}/openai/deployments/{EMBED_DEPLOY}/embeddings?api-version=2023-05-15"
#https://aoai-shs-0915.openai.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15

    headers = {"api-key": AOAI_KEY, "Content-Type": "application/json"}
    max_retries = 3
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            # use a higher timeout because embeddings for long documents may take longer
            r = httpx.post(url, headers=headers, json={"input": texts}, timeout=120.0)
            r.raise_for_status()
            return [d["embedding"] for d in r.json()["data"]]
        except httpx.ReadTimeout:
            print(f"Warning: embedding request timed out (attempt {attempt}/{max_retries}). Retrying after {backoff}s...")
        except httpx.HTTPStatusError as ex:
            # server returned 4xx/5xx
            print(f"Error: embedding request failed with status {ex.response.status_code}: {ex.response.text}")
            raise
        except httpx.RequestError as ex:
            print(f"Warning: embedding request error on attempt {attempt}/{max_retries}: {ex}")
        if attempt < max_retries:
            import time

            time.sleep(backoff)
            backoff *= 2
    # if we get here all retries failed
    raise RuntimeError("Failed to get embeddings after multiple attempts")

def main():
    sc = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))
    docs = []
    files = glob.glob(os.path.join(DATA_DIR, "*.md"))
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            md = f.read()
        text = md_to_text(md)
        vec = embed([text])[0]
        title = os.path.splitext(os.path.basename(fp))[0].replace("_", " ")
        doc = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": text,
            "service": "N/A",
            "severity": "P3",
            "impact": "N/A",
            "actions": "",
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
            "contentVector": vec
        }
        docs.append(doc)
    # upload in batches
    from azure.core.exceptions import HttpResponseError, ServiceRequestError
    print(f"Target index: {INDEX_NAME}")
    for i in range(0, len(docs), 1000):
        batch = docs[i:i+1000]
        try:
            res = sc.upload_documents(batch)
            print(f"Uploaded {len(batch)} documents, status: {res[0].succeeded if res else 'n/a'}")
        except ServiceRequestError as ex:
            print("Network/service error when contacting Azure Search. Check AZURE_SEARCH_ENDPOINT and network connectivity.")
            print(f"Details: {ex}")
            raise
        except HttpResponseError as ex:
            print("Azure Search rejected the batch. This is often caused by vector dimension mismatch or invalid document fields.")
            print(f"Status: {ex.status_code}, Error: {ex.message}")
            raise
    print("Completed upload.")

if __name__ == "__main__":
    main()
