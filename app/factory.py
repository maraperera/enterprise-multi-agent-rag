from contextlib import asynccontextmanager
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.identity.aio import DefaultAzureCredential as AsyncAzureCredential
from azure.search.documents.aio import SearchClient
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from app.config import get_settings
from app.retrieval import DemoRetriever, AzureRetriever
from app.agents import DemoAgents, AzureAgents
from app.graph import build_graph


@asynccontextmanager
async def graph_lifespan():
    settings = get_settings()
    if settings.app_mode == "demo":
        yield build_graph(DemoRetriever(), DemoAgents())
        return
    sync_credential = DefaultAzureCredential(managed_identity_client_id=settings.azure_client_id or None)
    async_credential = AsyncAzureCredential(managed_identity_client_id=settings.azure_client_id or None)
    provider = get_bearer_token_provider(sync_credential, "https://cognitiveservices.azure.com/.default")
    model = AzureChatOpenAI(azure_endpoint=settings.azure_openai_endpoint, azure_deployment=settings.azure_openai_chat_deployment, api_version=settings.azure_openai_api_version, azure_ad_token_provider=provider, temperature=0, timeout=60, max_retries=2)
    embeddings = AzureOpenAIEmbeddings(azure_endpoint=settings.azure_openai_endpoint, azure_deployment=settings.azure_openai_embedding_deployment, api_version=settings.azure_openai_api_version, azure_ad_token_provider=provider)
    client = SearchClient(endpoint=settings.azure_search_endpoint, index_name=settings.azure_search_index, credential=async_credential)
    try:
        yield build_graph(AzureRetriever(client, embeddings, settings.azure_search_semantic_config), AzureAgents(model))
    finally:
        await client.close()
        await async_credential.close()
        sync_credential.close()
