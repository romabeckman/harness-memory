from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from api.application.services.project_link_management_service import (
    ProjectLinkManagementService,
)
from core.domain.project_link.dtos.linked_project_summary import LinkedProjectSummary
from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


def _setup_service():
    link_repo = Mock()
    project_repo = Mock()
    service = ProjectLinkManagementService(link_repo, project_repo)
    return service, link_repo, project_repo


def test_create_link_successfully():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    t2_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()

    project_repo.get_project.side_effect = lambda tenant_id, key: {
        (t1_id, "alpha"): {
            "id": str(p1_id),
            "tenant_id": str(t1_id),
            "key": "alpha",
            "name": "Alpha",
        },
        (t2_id, "beta"): {"id": str(p2_id), "tenant_id": str(t2_id), "key": "beta", "name": "Beta"},
    }.get((tenant_id, key))

    link_repo.get_link.return_value = None
    expected_pair = CanonicalProjectPair(p1_id, p2_id)
    expected_link = ProjectLink(pair=expected_pair)
    link_repo.create_link.return_value = expected_link

    result = service.create_link(t1_id, "alpha", "beta", t2_id)

    assert result == expected_link
    link_repo.create_link.assert_called_once_with(expected_pair, None)


def test_create_link_origin_project_not_found():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    project_repo.get_project.return_value = None

    with pytest.raises(LookupError, match="project not found"):
        service.create_link(t1_id, "nonexistent", "beta", t1_id)


def test_create_link_target_project_not_found():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    p1_id = uuid4()
    project_repo.get_project.side_effect = lambda tenant_id, key: {
        (t1_id, "alpha"): {
            "id": str(p1_id),
            "tenant_id": str(t1_id),
            "key": "alpha",
            "name": "Alpha",
        },
    }.get((tenant_id, key))

    with pytest.raises(LookupError, match="project not found"):
        service.create_link(t1_id, "alpha", "nonexistent", t1_id)


def test_create_link_self_referential_rejected():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    p1_id = uuid4()
    project_repo.get_project.return_value = {
        "id": str(p1_id),
        "tenant_id": str(t1_id),
        "key": "alpha",
        "name": "Alpha",
    }

    with pytest.raises(ValueError, match="cannot link project to itself"):
        service.create_link(t1_id, "alpha", "alpha", t1_id)


def test_create_link_already_exists():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()

    project_repo.get_project.side_effect = lambda tenant_id, key: {
        (t1_id, "alpha"): {
            "id": str(p1_id),
            "tenant_id": str(t1_id),
            "key": "alpha",
            "name": "Alpha",
        },
        (t1_id, "beta"): {"id": str(p2_id), "tenant_id": str(t1_id), "key": "beta", "name": "Beta"},
    }.get((tenant_id, key))

    expected_pair = CanonicalProjectPair(p1_id, p2_id)
    link_repo.get_link.return_value = ProjectLink(pair=expected_pair)

    with pytest.raises(ValueError, match="project link already exists"):
        service.create_link(t1_id, "alpha", "beta", t1_id)


def test_delete_link_successfully():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()

    project_repo.get_project.side_effect = lambda tenant_id, key: {
        (t1_id, "alpha"): {
            "id": str(p1_id),
            "tenant_id": str(t1_id),
            "key": "alpha",
            "name": "Alpha",
        },
        (t1_id, "beta"): {"id": str(p2_id), "tenant_id": str(t1_id), "key": "beta", "name": "Beta"},
    }.get((tenant_id, key))

    link_repo.delete_link.return_value = True

    service.delete_link(t1_id, "alpha", "beta", t1_id)
    link_repo.delete_link.assert_called_once_with(CanonicalProjectPair(p1_id, p2_id))


def test_delete_link_not_found():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()

    project_repo.get_project.side_effect = lambda tenant_id, key: {
        (t1_id, "alpha"): {
            "id": str(p1_id),
            "tenant_id": str(t1_id),
            "key": "alpha",
            "name": "Alpha",
        },
        (t1_id, "beta"): {"id": str(p2_id), "tenant_id": str(t1_id), "key": "beta", "name": "Beta"},
    }.get((tenant_id, key))

    link_repo.delete_link.return_value = False

    with pytest.raises(LookupError, match="project link not found"):
        service.delete_link(t1_id, "alpha", "beta", t1_id)


def test_list_links_for_project():
    service, link_repo, project_repo = _setup_service()
    t1_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()

    project_repo.get_project.return_value = {
        "id": str(p1_id),
        "tenant_id": str(t1_id),
        "key": "alpha",
        "name": "Alpha",
    }

    expected_summaries = [
        LinkedProjectSummary(project_id=p2_id, key="beta", name="Beta", tenant_id=t1_id)
    ]
    link_repo.list_links_for_project.return_value = expected_summaries

    summaries = service.list_links(t1_id, "alpha")
    assert summaries == expected_summaries
    link_repo.list_links_for_project.assert_called_once_with(p1_id)
