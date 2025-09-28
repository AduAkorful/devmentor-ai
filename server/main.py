import os
import shutil
from dotenv import load_dotenv
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from urllib.parse import urlparse
import requests
import jwt
from datetime import datetime, timedelta
from typing import Optional

from elasticsearch import Elasticsearch
from langchain_google_vertexai import VertexAIEmbeddings, ChatVertexAI
from git import Repo
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from elasticsearch.helpers import bulk

import uvicorn
import asyncio
import stat
import google.cloud.aiplatform as aip

# --- 1. CONFIGURATION ---
load_dotenv()
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "a-very-secret-key-that-should-be-in-env")

ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID")
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_REGION = os.getenv("GCP_REGION")

INDEX_NAME_PREFIX = "devmentor"
EMBEDDING_MODEL_NAME, CHAT_MODEL_NAME = "text-embedding-004", "gemini-2.0-flash"
LOCAL_REPO_PATH = "./temp_repo"

# --- GLOBAL CLIENTS ---
es_client = Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, basic_auth=("elastic", ELASTIC_PASSWORD), request_timeout=30)
embedding_client = VertexAIEmbeddings(model_name=EMBEDDING_MODEL_NAME)
chat_client = ChatVertexAI(model_name=CHAT_MODEL_NAME, streaming=True)

# --- 2. CORE LOGIC ---
def on_rm_error(func, path, exc_info):
    if not os.access(path, os.W_OK): os.chmod(path, stat.S_IWUSR); func(path)
    else: raise exc_info[1]

def ingest_repo(user_id: str, repo_name: str, clone_url: str, access_token: str):
    index_name = f"{INDEX_NAME_PREFIX}_{user_id}_{repo_name.replace('/', '_')}".lower()
    print(f"Starting ingestion for user {user_id} into index {index_name}")
    authenticated_url = f"https://{access_token}@{urlparse(clone_url).netloc}{urlparse(clone_url).path}"
    if os.path.exists(LOCAL_REPO_PATH): shutil.rmtree(LOCAL_REPO_PATH, onerror=on_rm_error)
    Repo.clone_from(authenticated_url, to_path=LOCAL_REPO_PATH)
    
    documents = []
    file_extensions_to_include = ['.js', '.ts', '.py', '.go', '.java', '.rb', '.php', '.cs', '.c', '.cpp', '.h', '.sh', '.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.md', '.txt', '.html', '.css', 'Dockerfile', '.dockerignore', 'docker-compose.yml', '.gitignore']
    
    for dirpath, _, filenames in os.walk(LOCAL_REPO_PATH):
        if ".git" in dirpath: continue
        for file in filenames:
            if file in file_extensions_to_include or any(file.endswith(s) for s in file_extensions_to_include):
                try:
                    with open(os.path.join(dirpath, file), "r", encoding="utf-8", errors="ignore") as f:
                        documents.append(Document(page_content=f.read(), metadata={"source": os.path.join(dirpath, file).replace("\\", "/")}))
                except Exception: pass
    
    print(f"Loaded {len(documents)} documents.")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    all_texts = [chunk.page_content for chunk in chunks]
    all_embeddings = embedding_client.embed_documents(all_texts)
    
    actions = []
    if all_embeddings and len(all_embeddings) == len(chunks):
        for i, chunk in enumerate(chunks):
            actions.append({"_index": index_name, "_source": {"text": chunk.page_content, "metadata": chunk.metadata, "embedding": all_embeddings[i]}})
    if actions:
        mapping = {"properties": {"text": {"type": "text"}, "metadata": {"type": "object", "enabled": False}, "embedding": {"type": "dense_vector", "dims": 768}}}
        if es_client.indices.exists(index=index_name): es_client.indices.delete(index=index_name)
        es_client.indices.create(index=index_name, mappings=mapping)
        success, _ = bulk(es_client, actions)
        print(f"Successfully indexed {success} documents into {index_name}.")
    print("Ingestion complete.")

async def rag_pipeline_stream(user_query: str, index_name: str):
    if not es_client.indices.exists(index=index_name):
        yield f"Error: The index for this repository ('{index_name}') does not exist. Please re-ingest it by selecting it from the dashboard again."
        return
    try:
        query_vector = embedding_client.embed_query(user_query)
        search_response = es_client.search(
            index=index_name,
            query={"bool": {"should": [{"match": {"text": {"query": user_query, "boost": 1.0}}}]}},
            knn={"field": "embedding", "query_vector": query_vector, "k": 10, "num_candidates": 50, "boost": 1.5},
            rank={"rrf": {"rank_window_size": 100, "rank_constant": 20}},
            size=10
        )
        context = "".join([f"Source: {h['_source']['metadata'].get('source', 'N/A')}\nContent:\n{h['_source']['text']}\n\n---\n\n" for h in search_response["hits"]["hits"]])
        if not context:
            yield "I could not find relevant information in the codebase for that query. Try asking a more general question about the file structure."
            return
        system_prompt = f"""You are DevMentor AI, a world-class software engineering assistant. Your purpose is to help developers understand a codebase by answering questions based *only* on the provided context.

        Rules:
        1.  Your answer MUST be derived exclusively from the `CONTEXT` block. Do not use any outside knowledge.
        2.  If the context does not contain the information to answer the question, you MUST state: "The provided context does not contain the information to answer this question."
        3.  Be professional, concise, and clear.
        4.  Format your entire response using GitHub Flavored Markdown.
        5.  When referencing code or filenames, enclose them in backticks (`like_this.js`).
        6.  If you provide code snippets, use appropriate Markdown code blocks with language identifiers.

        CONTEXT:
        {context}
        """
        async for chunk in chat_client.astream([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}]):
            yield chunk.content
    except Exception as e:
        print(f"RAG Error: {e}")
        yield "An error occurred on the server during response generation."

# --- 3. FastAPI APP & ENDPOINTS ---
app = FastAPI(title="DevMentor AI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup_event():
    aip.init(project=GCP_PROJECT_ID, location=GCP_REGION)
    print("Ready.")

# --- AUTHENTICATION ---
@app.get("/login/github")
def login_github(): return {"url": f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo"}

@app.get("/auth/github/callback")
def auth_github_callback(code: str):
    token_url = "https://github.com/login/oauth/access_token"
    params = {"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code}
    headers = {"Accept": "application/json"}
    token_res = requests.post(token_url, params=params, headers=headers).json()
    access_token = token_res.get("access_token")
    if not access_token: raise HTTPException(400, "Failed to retrieve access token from GitHub")

    user_url = "https://api.github.com/user"
    headers = {"Authorization": f"token {access_token}"}
    user_res = requests.get(user_url, headers=headers).json()
    user_id = str(user_res.get("id"))
    
    jwt_payload = {"sub": user_id, "login": user_res.get("login"), "gh_token": access_token, "exp": datetime.utcnow() + timedelta(hours=8)}
    session_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")
    
    return {"status": "success", "token": session_token, "user": {"login": user_res.get("login")}}

# --- PROTECTED ENDPOINTS ---
async def get_current_user(request: Request, authorization: Optional[str] = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    else:
        token = request.query_params.get("token")
    if not token: raise HTTPException(status_code=401, detail="Not authenticated")
    try: return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError: raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError: raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/user/me")
async def get_user_me(user: dict = Depends(get_current_user)):
    return {"login": user.get("login")}

@app.get("/user/repos")
async def get_user_repos(user: dict = Depends(get_current_user)):
    gh_token, repos, page = user.get("gh_token"), [], 1
    while True:
        repos_url = f"https://api.github.com/user/repos?type=all&sort=pushed&per_page=100&page={page}"
        headers = {"Authorization": f"token {gh_token}"}
        res = requests.get(repos_url, headers=headers)
        if res.status_code != 200 or not res.json(): break
        repos.extend(res.json())
        if len(res.json()) < 100: break # Break if we've reached the last page
        page += 1
    return repos

@app.post("/ingest-repo")
async def ingest_repo_endpoint(request: Request, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    body = await request.json()
    repo_name, clone_url = body.get("repo_name"), body.get("clone_url")
    if not repo_name or not clone_url: raise HTTPException(400, "repo_name and clone_url required")
    background_tasks.add_task(ingest_repo, user['sub'], repo_name, clone_url, user['gh_token'])
    return {"status": "success", "message": f"Ingestion started for {repo_name}."}

@app.get("/concierge")
async def concierge_endpoint(repo_name: str, user_query: str, user: dict = Depends(get_current_user)):
    if not repo_name: raise HTTPException(400, "repo_name query parameter is required")
    index_name = f"{INDEX_NAME_PREFIX}_{user['sub']}_{repo_name.replace('/', '_')}".lower()
    async def stream_wrapper():
        try:
            async for chunk in rag_pipeline_stream(user_query, index_name): yield chunk
        finally:
            yield {'event': 'close', 'data': ''}
    return EventSourceResponse(stream_wrapper())

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)