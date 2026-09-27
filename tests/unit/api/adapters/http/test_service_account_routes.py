from uuid import uuid4

from api.adapters.http.service_account_routes import create_service_account_router


class RecordingService:
    def __init__(self):
        self.calls = []

    def list(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return []


def test_service_account_list_route_forwards_search_and_pagination_to_service():
    service = RecordingService()
    router = create_service_account_router(service)
    endpoint = next(
        route.endpoint
        for route in router.routes
        if route.path == "/service-accounts" and "GET" in route.methods
    )

    tenant_id = uuid4()
    endpoint(
        tenant_id=tenant_id,
        name="release",
        q="agent",
        limit=20,
        offset=40,
    )

    assert service.calls == [
        (
            (),
            {
                "tenant_id": tenant_id,
                "name": "release",
                "q": "agent",
                "limit": 20,
                "offset": 40,
            },
        )
    ]
