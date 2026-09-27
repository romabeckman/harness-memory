from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping

from core.domain.tenant_security.types.memory_scope import MemoryScope
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal

logger = logging.getLogger(__name__)


class ComponentKind(StrEnum):
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"


@dataclass(frozen=True, slots=True)
class Component:
    kind: str
    name: str


class ComponentScopePolicy:
    _MATRIX = {
        ("tool", "analyze_impact"): MemoryScope.IMPACT.value,
        ("tool", "search_entities"): MemoryScope.READ.value,
        ("tool", "search_projects"): MemoryScope.READ.value,
        ("tool", "get_context"): MemoryScope.READ.value,
        ("tool", "get_dependencies"): MemoryScope.READ.value,
        ("tool", "find_integration_paths"): MemoryScope.READ.value,
        ("tool", "get_environment"): MemoryScope.READ.value,
        ("tool", "compare_environments"): MemoryScope.READ.value,
        ("resource", "memory://entities/{entity_id}"): MemoryScope.READ.value,
        ("resource", "memory://projects/{project_key}"): MemoryScope.READ.value,
        ("resource", "memory://snapshots/{snapshot_id}"): MemoryScope.READ.value,
        ("resource", "entity_memory"): MemoryScope.READ.value,
        ("resource", "project_memory"): MemoryScope.READ.value,
        ("resource", "snapshot_memory"): MemoryScope.READ.value,
        ("prompt", "load_corporate_context"): MemoryScope.READ.value,
        ("prompt", "analyze_integration"): MemoryScope.READ.value,
        ("prompt", "review_change_impact"): MemoryScope.IMPACT.value,
    }

    def __init__(self, mappings: dict[tuple[str, str], str] | None = None):
        self._mappings = dict(self._MATRIX)
        if mappings:
            self._mappings.update(mappings)

    def required_scope(self, component_kind: str | object, name: str | None = None) -> str | None:
        if name is None:
            if isinstance(component_kind, Component):
                component_kind, name = component_kind.kind, component_kind.name
            elif isinstance(component_kind, tuple):
                component_kind, name = component_kind
            else:
                raise ValueError("component name is required")
        key = (str(component_kind), str(name))
        if key in self._mappings:
            return self._mappings[key]
        if key[0] == "resource" and key[1].startswith("memory://"):
            # FastMCP lists concrete URI templates; normalize to tactical templates.
            for template, scope in self._mappings.items():
                if template[0] == "resource" and self._matches_uri_template(template[1], key[1]):
                    return scope
        return None

    def authorize(self, principal: AuthenticatedPrincipal, component_kind: str, name: str) -> str:
        required = self.required_scope(component_kind, name)
        if required is None:
            raise PermissionError("unmapped MCP component")
        if required not in principal.scopes:
            raise PermissionError(f"insufficient_scope:{required}")
        return required

    def can_access(self, principal: AuthenticatedPrincipal, component_kind: str, name: str) -> bool:
        required = self.required_scope(component_kind, name)
        return required is not None and required in principal.scopes

    def filter_components(
        self, principal: AuthenticatedPrincipal, component_kind: str, components: Iterable[object]
    ) -> list[object]:
        result = []
        for component in components:
            name = (
                getattr(component, "uri_template", None)
                or getattr(component, "uriTemplate", None)
                or getattr(component, "name", None)
                or getattr(component, "uri", None)
                or str(component)
            )
            if self.can_access(principal, component_kind, name):
                result.append(component)
        return result

    @staticmethod
    def _matches_uri_template(template: str, value: str) -> bool:
        prefix, marker, remainder = template.partition("{")
        if not marker:
            return value == template
        variable, marker, suffix = remainder.partition("}")
        if not marker or not value.startswith(prefix) or not value.endswith(suffix):
            return False
        if value == template:
            return True
        end = len(value) - len(suffix) if suffix else len(value)
        bound_value = value[len(prefix) : end]
        return bool(variable and bound_value and "/" not in bound_value)


def component_scope_auth(policy: ComponentScopePolicy, audit_handler=None, principal_factory=None):
    """FastMCP auth check enforcing policy for catalog and direct access."""

    def check(auth_context) -> bool:
        token = auth_context.token
        component = auth_context.component
        if token is None:
            return False
        if hasattr(component, "uri_template") or hasattr(component, "uriTemplate"):
            kind, name = (
                "resource",
                getattr(component, "uri_template", None) or component.uriTemplate,
            )
        elif hasattr(component, "uri"):
            kind, name = "resource", str(component.uri)
        elif component.__class__.__name__.lower().endswith("prompt"):
            kind, name = "prompt", component.name
        else:
            kind, name = "tool", component.name
        required = policy.required_scope(kind, name)
        allowed = required is not None and required in token.scopes
        if not allowed and audit_handler is not None:
            from uuid import uuid4

            from core.application.tenant_security.use_cases.record_security_audit.inbound import (
                SecurityAuditCommand,
            )
            from core.domain.tenant_security.types.audit_event_type import AuditEventType
            from core.domain.tenant_security.types.audit_outcome import AuditOutcome
            from core.domain.tenant_security.types.audit_phase import AuditPhase

            claims = token.claims if isinstance(token.claims, Mapping) else {}
            try:
                principal = (
                    principal_factory.from_verified_claims(claims)
                    if principal_factory is not None
                    else None
                )
            except ValueError:
                principal = None
            try:
                audit_handler.execute(
                    SecurityAuditCommand(
                        request_id=uuid4(),
                        event_type=AuditEventType.AUTHORIZATION_FAILURE,
                        phase=AuditPhase.COMPLETED,
                        outcome=AuditOutcome.DENIED,
                        component_kind=kind,
                        component_name=str(name),
                        required_scope=required,
                        tenant_id=getattr(principal, "tenant_id", None),
                        subject=getattr(principal, "subject", None),
                        reason_code="insufficient_scope",
                    )
                )
            except Exception:
                # Authorization remains denied when audit storage is unavailable.
                logger.error("security audit persistence failed for authorization denial")
        return allowed

    return check
