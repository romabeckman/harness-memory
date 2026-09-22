from core.application.knowledge_publication.use_cases.publish_knowledge.handler import PublishKnowledgeHandler
from core.application.knowledge_publication.use_cases.publish_knowledge.inbound import PublishKnowledgeInput
from core.application.snapshot_publication.services.snapshot_payload import snapshot_payload


def test_document_content_and_rules_are_normal_graph_facts():
    handler = PublishKnowledgeHandler(None, None)
    snapshot = handler._build_snapshot(PublishKnowledgeInput(
        "demo", "production", "release-1", "1",
        entities=(
            {"key": "feature:orders", "type": "feature", "metadata": {"content": "# Orders\nREQUIRED: Reject empty orders.", "path": "docs/feature/orders.md"}},
            {"key": "rule:orders:empty", "type": "rule", "metadata": {"statement": "Reject empty orders.", "modality": "REQUIRED"}},
        ),
        relations=({"ref": "defines-rule", "source_entity_key": "feature:orders", "target_entity_key": "rule:orders:empty", "type": "defines", "provenance": "declared"},),
    ))
    payload = snapshot_payload(snapshot)
    assert payload["entities"][0]["metadata"]["content"].endswith("Reject empty orders.")
    assert payload["relations"][0]["type"] == "defines"
    assert "project_memory" not in payload
