"""
Create Azure AI Search index with vector + semantic (SDK 11.6.0b12)
"""
import os
from dotenv import load_dotenv, find_dotenv
from azure.core.exceptions import HttpResponseError
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SimpleField, SearchableField, ComplexField,
    SearchFieldDataType, VectorSearch, VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration, SemanticConfiguration,
    InputFieldMappingEntry, OutputFieldMappingEntry, 
    VectorSearchProfile
)

dotenv_path = find_dotenv()
if dotenv_path:
    # override=True ensures .env values replace any existing shell placeholders
    load_dotenv(dotenv_path, override=True)
    print(f"Loaded .env from: {dotenv_path} (overriding shell environment variables)")
else:
    print("No .env file found; relying on environment variables.")

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_API_KEY"]
# If AZURE_SEARCH_INDEX is not provided, auto-generate a new index name to avoid
# attempting to change an existing index's field definitions.
env_index = os.getenv("AZURE_SEARCH_INDEX")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", os.getenv("AZURE_OPENAI_EMBEDDING_DIM", "1536")))

if env_index:
    INDEX_NAME = env_index
else:
    from datetime import datetime
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    INDEX_NAME = f"incident-runbooks-v{EMBEDDING_DIM}-{ts}"

index_client = SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(SEARCH_KEY))

# Vector search configuration
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(name="hnsw")
    ],
    profiles=[
        VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")
    ]
)



fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, sortable=True, filterable=True, analyzer_name="ko.lucene"),
    SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ko.lucene"),
    SearchableField(name="service", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SimpleField(name="severity", type=SearchFieldDataType.String, filterable=True, facetable=True),
    SearchableField(name="impact", type=SearchFieldDataType.String),
    SearchableField(name="actions", type=SearchFieldDataType.String),
    SimpleField(name="createdAt", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    # vector field (1536 or 3072 depending on the embedding model)
    SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=EMBEDDING_DIM, vector_search_profile_name="vprofile")
]

index = SearchIndex(
    name=INDEX_NAME,
    fields=fields,
    vector_search=vector_search
)

print(f"Creating or updating index: {INDEX_NAME}")
try:
    created = index_client.create_or_update_index(index)
    print(f"Done. Created index: {getattr(created, 'name', INDEX_NAME)}")
except HttpResponseError as ex:
    # If the error indicates an existing field cannot be changed, create a new index name
    msg = str(ex)
    if 'CannotChangeExistingField' in msg or 'Existing field' in msg:
        from datetime import datetime
        # use a lowercase, dash-separated timestamp to satisfy Azure index name rules
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        # ensure lowercase and allowed characters only
        base = INDEX_NAME.lower()
        new_name = f"{base}-v{EMBEDDING_DIM}-{ts}"
        print(f"Index update failed because existing fields cannot be changed. Creating a new index: {new_name}")
        index.name = new_name
        created = index_client.create_or_update_index(index)
        print(f"Done. Created new index: {getattr(created, 'name', new_name)}")
    else:
        raise
