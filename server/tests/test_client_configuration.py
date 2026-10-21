"""
Copyright 2026, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from unittest.mock import patch

import pytest
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

from graph_service.config import Settings
from graph_service.zep_graphiti import _create_graphiti_client


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    monkeypatch.setitem(Settings.model_config, 'env_file', None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.mark.parametrize('backend', ['neo4j', 'falkordb'])
def test_configured_clients_use_local_models(backend):
    settings = Settings.model_validate(
        {
            'openai_api_key': 'ollama',
            'openai_base_url': 'http://localhost:11434/v1',
            'model_name': 'qwen3:8b',
            'llm_temperature': 0,
            'llm_max_tokens': 8192,
            'embedding_model_name': 'nomic-embed-text:v1.5',
            'embedding_dim': 768,
            'db_backend': backend,
            'neo4j_uri': 'bolt://localhost:7687',
            'neo4j_user': 'neo4j',
            'neo4j_password': 'test-only',
        }
    )
    with (
        patch('graph_service.zep_graphiti.ZepGraphiti') as graphiti,
        patch('graphiti_core.driver.falkordb_driver.FalkorDriver'),
    ):
        _create_graphiti_client(settings)

    clients = graphiti.call_args.kwargs
    llm = clients['llm_client']
    assert isinstance(llm, OpenAIGenericClient)
    assert llm.model == 'qwen3:8b'
    assert llm.small_model == 'qwen3:8b'
    assert llm.temperature == 0
    assert llm.max_tokens == 8192
    assert llm.structured_output_mode == 'json_schema'
    assert str(llm.client.base_url) == 'http://localhost:11434/v1/'
    assert llm.client.api_key == 'ollama'

    embedder = clients['embedder']
    assert embedder.config.embedding_model == 'nomic-embed-text:v1.5'
    assert embedder.config.embedding_dim == 768
    assert str(embedder.client.base_url) == 'http://localhost:11434/v1/'
    assert embedder.client.api_key == 'ollama'

    reranker = clients['cross_encoder']
    assert str(reranker.client.base_url) == 'http://localhost:11434/v1/'
    assert reranker.config.model == 'qwen3:8b'
    assert reranker.client.api_key == 'ollama'


def test_default_clients_keep_hosted_openai_behavior(monkeypatch):
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    settings = Settings.model_validate(
        {
            'openai_api_key': 'test-only',
            'neo4j_uri': 'bolt://localhost:7687',
            'neo4j_user': 'neo4j',
            'neo4j_password': 'test-only',
        }
    )
    with patch('graph_service.zep_graphiti.ZepGraphiti') as graphiti:
        _create_graphiti_client(settings)

    clients = graphiti.call_args.kwargs
    assert isinstance(clients['llm_client'], OpenAIClient)
    assert clients['llm_client'].model is None
    assert clients['embedder'].config.embedding_model == 'text-embedding-3-small'
    assert str(clients['embedder'].client.base_url) == 'https://api.openai.com/v1/'
    assert clients['cross_encoder'].config.model is None


def test_embedding_endpoint_is_independent_of_extraction():
    settings = Settings.model_validate(
        {
            'openai_api_key': 'extraction-test',
            'openai_base_url': 'http://localhost:1337/v1',
            'model_name': 'extraction-model',
            'llm_structured_output_mode': 'json_object',
            'embedding_api_key': 'ollama',
            'embedding_base_url': 'http://localhost:11434/v1',
            'embedding_model_name': 'nomic-embed-text:v1.5',
            'embedding_dim': 768,
            'neo4j_uri': 'bolt://localhost:7687',
            'neo4j_user': 'neo4j',
            'neo4j_password': 'test-only',
        }
    )
    with patch('graph_service.zep_graphiti.ZepGraphiti') as graphiti:
        _create_graphiti_client(settings)

    clients = graphiti.call_args.kwargs
    assert str(clients['llm_client'].client.base_url) == 'http://localhost:1337/v1/'
    assert clients['llm_client'].client.api_key == 'extraction-test'
    assert clients['llm_client'].structured_output_mode == 'json_object'
    assert str(clients['embedder'].client.base_url) == 'http://localhost:11434/v1/'
    assert clients['embedder'].client.api_key == 'ollama'
    assert clients['embedder'].config.embedding_model == 'nomic-embed-text:v1.5'
    assert clients['embedder'].config.embedding_dim == 768
