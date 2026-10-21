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

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graph_service.dto import AddMessagesRequest
from graph_service.routers import ingest


@pytest.mark.asyncio
@pytest.mark.parametrize('fails', [False, True])
async def test_queued_ingestion_owns_client_until_job_finishes(monkeypatch, fails):
    queue = asyncio.Queue()
    monkeypatch.setattr(ingest.async_worker, 'queue', queue)
    client = MagicMock()
    client.close = AsyncMock()

    async def add_episode(**kwargs):
        client.close.assert_not_awaited()
        assert kwargs['group_id'] == 'synthetic-test'
        if fails:
            raise RuntimeError('Synthetic extraction failure')

    client.add_episode = AsyncMock(side_effect=add_episode)
    request = AddMessagesRequest.model_validate(
        {
            'group_id': 'synthetic-test',
            'messages': [{'content': 'Synthetic message', 'role_type': 'user', 'role': None}],
        }
    )
    with patch(
        'graph_service.zep_graphiti._create_graphiti_client', return_value=client
    ) as factory:
        result = await ingest.add_messages(request, settings=MagicMock())
        assert result.success
        factory.assert_not_called()

        job = queue.get_nowait()
        if fails:
            with pytest.raises(RuntimeError, match='Synthetic extraction failure'):
                await job()
        else:
            await job()

        factory.assert_called_once()
        client.add_episode.assert_awaited_once()
        client.close.assert_awaited_once()
