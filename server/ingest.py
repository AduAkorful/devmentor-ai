import os
import shutil
from dotenv import load_dotenv
from git import Repo

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from langchain_google_vertexai import VertexAIEmbeddings

from elasticsearch import Elasticsearch
# Correctly import the synchronous 'bulk' helper
from elasticsearch.helpers import bulk 
import google.cloud.aiplatform as aip

import time
import asyncio
import stat

# --- 1. CONFIGURATION ---
load_dotenv()
ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_REGION = os.getenv("GCP_REGION")

REPO_URL = "https://github.com/axios/axios.git"
LOCAL_REPO_PATH = "./temp_repo"
INDEX_NAME = "devmentor_codebase"
EMBEDDING_MODEL_NAME = "text-embedding-004"


# --- 2. HELPER FUNCTIONS & INITIALIZATION ---
aip.init(project=GCP_PROJECT_ID, location=GCP_REGION)
embedding_client = VertexAIEmbeddings(model_name=EMBEDDING_MODEL_NAME)

def get_embeddings(texts):
    print(f"Requesting embeddings for {len(texts)} chunks...")
    try:
        return embedding_client.embed_documents(texts)
    except Exception as e:
        print(f"An error occurred while getting embeddings: {e}")
        return []

def on_rm_error(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise exc_info[1]

def load_and_parse_repo():
    if os.path.exists(LOCAL_REPO_PATH):
        print(f"Removing existing repo at {LOCAL_REPO_PATH}")
        shutil.rmtree(LOCAL_REPO_PATH, onerror=on_rm_error)
    
    print(f"Cloning repository from {REPO_URL} to {LOCAL_REPO_PATH}...")
    Repo.clone_from(REPO_URL, to_path=LOCAL_REPO_PATH)
    print("Repository cloned successfully.")

    documents = []
    for dirpath, dirnames, filenames in os.walk(LOCAL_REPO_PATH):
        if ".git" in dirpath: continue
        for file in filenames:
            if file.endswith((".js", ".md")):
                try:
                    file_path = os.path.join(dirpath, file)
                    with open(file_path, "r", encoding="utf-8") as f: content = f.read()
                    doc = Document(page_content=content, metadata={"source": file_path.replace("\\", "/"), "language": "javascript" if file.endswith(".js") else "markdown"})
                    documents.append(doc)
                except Exception as e: print(f"Error reading file {file_path}: {e}")
    
    print(f"Loaded {len(documents)} documents from the repository.")
    return documents

def split_documents(documents):
    js_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.JS, chunk_size=2000, chunk_overlap=200)
    markdown_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.MARKDOWN, chunk_size=2000, chunk_overlap=200)
    chunks = []
    for doc in documents:
        if doc.metadata["language"] == "javascript": chunks.extend(js_splitter.split_documents([doc]))
        elif doc.metadata["language"] == "markdown": chunks.extend(markdown_splitter.split_documents([doc]))
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks

# --- 3. MAIN EXECUTION ---
async def main():
    start_time = time.time()
    print("Connecting to Elastic Cloud...")
    try:
        es_client = Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, basic_auth=("elastic", ELASTIC_PASSWORD), request_timeout=30)
        print(es_client.info())
    except Exception as e:
        print(f"Could not connect to Elasticsearch: {e}")
        return

    documents = load_and_parse_repo()
    chunks = split_documents(documents)
    all_texts = [chunk.page_content for chunk in chunks]
    all_embeddings = get_embeddings(all_texts)
        
    actions = []
    if all_embeddings and len(all_embeddings) == len(chunks):
        for i, chunk in enumerate(chunks):
            action = {"_index": INDEX_NAME, "_source": {"text": chunk.page_content, "metadata": chunk.metadata, "embedding": all_embeddings[i]}}
            actions.append(action)

    if actions:
        print(f"Preparing to index {len(actions)} documents...")
        mapping = {"properties": {"text": {"type": "text"}, "metadata": {"type": "object", "enabled": False}, "embedding": {"type": "dense_vector", "dims": 768, "index": True, "similarity": "cosine"}}}
        
        if es_client.indices.exists(index=INDEX_NAME):
            print(f"Deleting existing index '{INDEX_NAME}'...")
            es_client.indices.delete(index=INDEX_NAME)
        print(f"Creating new index '{INDEX_NAME}'...")
        es_client.indices.create(index=INDEX_NAME, mappings=mapping)
        
        # --- FINAL FIX: Use a thread pool executor for the blocking 'bulk' call ---
        print("Bulk indexing documents...")
        loop = asyncio.get_running_loop()
        
        success, failed = await loop.run_in_executor(
            None,  # Use the default thread pool executor
            lambda: bulk(es_client, actions, request_timeout=60)
        )
        
        print(f"Successfully indexed {success} documents.")
        if failed:
            print(f"Failed to index {len(failed)} documents.")
    else:
        print("No documents were prepared for indexing. An issue occurred during embedding.")
    
    es_client.close()
    end_time = time.time()
    print(f"Phase 1 completed in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main())