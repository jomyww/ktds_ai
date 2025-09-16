import os
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX", "incident-runbooks")

if not endpoint or not key:
    print("AZURE_SEARCH_ENDPOINT or AZURE_SEARCH_API_KEY not set in environment")
    raise SystemExit(1)

client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# Use list_index_names() to check existing indexes
existing = list(client.list_index_names())
if existing:
    if index_name in existing:
        print(f"Deleting index: {index_name}")
        client.delete_index(index_name)
        print("Deleted")
    else:
        print(f"Index {index_name} not found; nothing to delete")
else:
    print("No indexes found")
