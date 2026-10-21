# graph-service

Graph service is a fast api server implementing the [graphiti](https://github.com/getzep/graphiti) package.

> **Security:** This server is a reference implementation. Do not use the server as a production deployment. The server has no authentication, no authorization, and no prompt-injection protection. These omissions are intentional. Any caller can read, change, or delete all graph data. Do not expose the server to an untrusted network. For production options, see [Reference MCP and REST servers](../README.md#reference-mcp-and-rest-servers). For the security scope, see the [security policy scope](../SECURITY.md#scope).

To expose the server on all interfaces, run Uvicorn with `--host 0.0.0.0` or change the host-side port mapping in
Docker Compose; the server has no authentication.

## Container Releases

The FastAPI server container is automatically built and published to Docker Hub when a `v*.*.*` tag is pushed (the same tags that publish `graphiti-core` to PyPI).

**Image:** `zepai/graphiti`

**Available tags:**
- `latest` - Latest stable release
- `0.30.2` - Specific version (matches graphiti-core version)

**Platforms:** linux/amd64, linux/arm64

The automated release workflow:
1. Triggers on `v*.*.*` tag pushes (and can be run manually via `workflow_dispatch`)
2. Waits for that `graphiti-core` version to be available on PyPI
3. Builds multi-platform Docker image
4. Tags with version number and `latest`
5. Pushes to Docker Hub

Only stable releases are built automatically (pre-release versions are skipped).

## Running Instructions

1. Ensure you have Docker and Docker Compose installed on your system.

2. Add `zepai/graphiti:latest` to your service setup

3. Make sure to pass the following environment variables to the service

   ```
   OPENAI_API_KEY=your_openai_api_key
   NEO4J_USER=your_neo4j_user
   NEO4J_PASSWORD=your_neo4j_password
   NEO4J_PORT=your_neo4j_port
   ```

4. This service depends on having access to a neo4j instance, you may wish to add a neo4j image to your service setup as well. Or you may wish to use neo4j cloud or a desktop version if running this locally.

   An example of docker compose setup may look like this:

   ```yml
      version: '3.8'

      services:
      graph:
         image: zepai/graphiti:latest
         ports:
            - "127.0.0.1:8000:8000"
         
         environment:
            - OPENAI_API_KEY=${OPENAI_API_KEY}
            - NEO4J_URI=bolt://neo4j:${NEO4J_PORT}
            - NEO4J_USER=${NEO4J_USER}
            - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      neo4j:
         image: neo4j:5.22.0
         
         ports:
            - "7474:7474"  # HTTP
            - "${NEO4J_PORT}:${NEO4J_PORT}"  # Bolt
         volumes:
            - neo4j_data:/data
         environment:
            - NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}

      volumes:
      neo4j_data:
   ```

5. Once you start the service, it will be available at `http://localhost:8000` (or the port you have specified in the docker compose file).

6. You may access the swagger docs at `http://localhost:8000/docs`. You may also access redocs at `http://localhost:8000/redoc`.

7. You may also access the neo4j browser at `http://localhost:7474` (the port depends on the neo4j instance you are using).

### Local OpenAI-compatible models

Set these variables on the REST API container to use a local Ollama endpoint:

```dotenv
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://host.containers.internal:11434/v1
MODEL_NAME=qwen3:8b
LLM_TEMPERATURE=0
LLM_MAX_TOKENS=8192
EMBEDDING_MODEL_NAME=nomic-embed-text:v1.5
EMBEDDING_DIM=768
GRAPHITI_TELEMETRY_ENABLED=false
```

For Docker Desktop, use `host.docker.internal` instead of `host.containers.internal`.
For a server running directly on the host, use `localhost`.
The custom base URL applies to extraction, embeddings, and reranking, and selects
the OpenAI-compatible chat-completions client rather than the OpenAI Responses API.
Reranking additionally requires support for log probabilities; ordinary REST search
does not use the cross-encoder reranker.

When sharing a database with MCP, use the same embedding model and dimensions in
both services. Do not change them for an existing graph without regenerating its
embeddings. Keep credentials in a private runtime `.env` file outside the checkout.

To route extraction to a different OpenAI-compatible service while keeping embeddings
local, set `EMBEDDING_BASE_URL=http://host.containers.internal:11434/v1` and
`EMBEDDING_API_KEY=ollama`, then point `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and
`MODEL_NAME` at the extraction service. The embedding endpoint and key independently
fall back to their `OPENAI_*` counterparts when omitted, preserving single-provider
deployments. Sending extraction to a hosted provider sends episode text to that provider,
even when embeddings and graph storage stay local.
For compatible services that reject the native Pydantic schema, set
`LLM_STRUCTURED_OUTPUT_MODE=json_object`. This selects Graphiti's schema-in-prompt
JSON mode; the default remains `json_schema`.