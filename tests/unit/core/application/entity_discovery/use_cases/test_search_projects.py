from unittest.mock import Mock

import pytest

from core.application.entity_discovery.contracts.project_search_item import ProjectSearchItem
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.errors.project_search_failure import ProjectSearchFailure
from core.application.entity_discovery.use_cases.search_projects.handler import (
    SearchProjectsHandler,
)


def test_handler_normalizes_input_and_bounds_project_results():
    repository = Mock()
    repository.search_projects.return_value = [
        ProjectSearchItem(key="send", name="Send", has_active_snapshot=True),
        ProjectSearchItem(key="sender", name="Sender", has_active_snapshot=False),
    ]

    result = SearchProjectsHandler(repository).execute(
        {"query": " Send ", "limit": 1, "offset": 2}, TenantScope("tenant-a")
    )

    assert result.model_dump(mode="json", exclude_none=True) == {
        "items": [{"key": "send", "name": "Send", "has_active_snapshot": True}],
        "count": 1,
        "limit": 1,
        "offset": 2,
        "has_more": True,
    }
    repository.search_projects.assert_called_once_with(
        TenantScope("tenant-a"), key=None, query="Send", limit=2, offset=2
    )


def test_handler_lists_projects_without_filters():
    repository = Mock()
    repository.search_projects.return_value = []

    result = SearchProjectsHandler(repository).execute({}, TenantScope("tenant-a"))

    assert result.count == 0
    repository.search_projects.assert_called_once_with(
        TenantScope("tenant-a"), key=None, query=None, limit=101, offset=0
    )


def test_handler_returns_500_projects_and_reports_next_page():
    repository = Mock()
    repository.search_projects.return_value = [
        ProjectSearchItem(
            key=f"project-{index}", name=f"Project {index}", has_active_snapshot=False,
        )
        for index in range(501)
    ]

    result = SearchProjectsHandler(repository).execute(
        {"limit": 500}, TenantScope("tenant-a")
    )

    assert result.count == 500
    assert len(result.items) == 500
    assert result.has_more is True
    assert repository.search_projects.call_args.kwargs["limit"] == 501


def test_handler_rejects_missing_scope_without_repository_call():
    repository = Mock()
    handler = SearchProjectsHandler(repository)

    with pytest.raises(RuntimeError, match="tenant context"):
        handler.execute({}, None)

    repository.search_projects.assert_not_called()


def test_handler_sanitizes_repository_failures():
    repository = Mock()
    repository.search_projects.side_effect = RuntimeError("tenant-a password=secret")

    with pytest.raises(ProjectSearchFailure, match="project search failed") as error:
        SearchProjectsHandler(repository).execute({"key": "send"}, TenantScope("tenant-a"))

    assert "secret" not in str(error.value)


def test_handler_maps_invalid_repository_output_to_search_failure():
    repository = Mock()
    repository.search_projects.return_value = [
        {"key": "send", "name": "Send", "active_snapshot_id": "snapshot-a"}
    ]

    with pytest.raises(ProjectSearchFailure):
        SearchProjectsHandler(repository).execute(
            {"key": "send"}, TenantScope("tenant-a")
        )
