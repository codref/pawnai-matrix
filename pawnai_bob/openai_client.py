import json
import logging
from qdrant_client import QdrantClient
from llama_index.llms.openai_like import OpenAILike
from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    Settings,
)
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai_like import OpenAILikeEmbedding



log = logging.getLogger(__name__)

class OpenAIClient:
    """Creates an openai object to interact with the llm"""
    def __init__(self, settings, init_from_settings = True) -> None:
        self.timeout = settings.openai_timeout
        self.url = settings.openai_url
        self.api_key = settings.openai_api_key
        self.llm_model = settings.openai_default_llm_model
        self.embed_model = settings.openai_default_embed_model
        self.chunk_size = settings.openai_default_chunk_size
        self.context_length = settings.openai_default_context_length
        self.prompt = settings.openai_default_prompt
        self.collection_name = settings.qdrant_default_collection_name
        self.client = QdrantClient(url=settings.qdrant_url)
        self.chat_mode = "context"
        self.index = None
        if init_from_settings:
            self.init_llm()
   
    def fromJSON(self, json_string):
        obj = json.loads(json_string)
        self.llm_model = obj["llm_model"]
        self.embed_model = obj["embed_model"]
        self.chunk_size = obj["chunk_size"]
        self.context_length = obj["context_length"]
        self.prompt = obj["prompt"]
        self.collection_name = obj["collection_name"]
        self.chat_mode = obj["chat_mode"]
        self.init_llm()
        self.init_index()
        return self

    def toJSON(self):
        return json.dumps(
            {
                'llm_model':  self.llm_model,
                'embed_model': self.embed_model,
                'chunk_size': self.chunk_size,
                'context_length': self.context_length,
                'prompt': self.prompt,
                'collection_name': self.collection_name,
                'chat_mode': self.chat_mode,
            },
            indent=2)

    def init_llm(self):
        self.llm = OpenAILike(model=self.llm_model, is_chat_model=True, is_function_calling_model=True, api_base=self.url, timeout=self.timeout, api_key=self.api_key)
        Settings.llm = self.llm
        Settings.embed_model = OpenAILikeEmbedding(
            model_name=self.embed_model,
            api_base=self.url,
            api_key=self.api_key,
            timeout=self.timeout
        )

        Settings.chunk_size = self.chunk_size

    def init_index(self):
        vector_store = QdrantVectorStore(client=self.client, collection_name=self.collection_name)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )
        self.init_chat_engine()

    def init_chat_engine(self):
        # Initialize chat memory buffer
        memory = ChatMemoryBuffer.from_defaults(token_limit=self.context_length)

        # TODO this is just an experiment, ReAct agents should have more tools!
        if self.chat_mode == "react":
            tools = [
                QueryEngineTool(
                    query_engine=self.index.as_query_engine(),
                    metadata=ToolMetadata(
                        name="context_index",
                        description=(
                            "Provides generic information about the current context."
                        ),
                    ),
                ),
                FunctionTool.from_defaults(fn=nothing_to_do),
                FunctionTool.from_defaults(fn=tomorrow),
                FunctionTool.from_defaults(fn=today),
            ]

            self.chat_engine = ReActAgent.from_tools(tools, llm=self.llm, memory=memory, verbose=True)
        
        # If not ReAct, the fallback is always context mode
        else:
            self.chat_engine = self.index.as_chat_engine(
                chat_mode="context",
                memory=memory,
                system_prompt=(self.prompt),
                verbose=True
                )

    def reset_chat_engine(self):
        self.chat_engine.reset()

    def set_chat_mode(self, mode):
        self.chat_mode = mode

    def set_llm_model(self, model):
        self.llm_model = model

    def set_embed_model(self, model):
        self.embed_model = model

    def set_collection_name(self, collection_name):
        self.collection_name = collection_name

    def set_chunk_size(self, chunk_size):
        self.chunk_size = chunk_size

    def set_model(self, model_name):
        self.model = model_name

    def set_context_length(self, token_limit):
        self.context_length = token_limit

    def set_prompt(self, prompt):
        self.prompt = prompt

    def index_document(self, documents):
        for document in documents:
            self.index.insert(document)     