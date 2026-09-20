from collections.abc import Iterable

from core.domain.snapshot_publication.types.relation_type import RelationType

from ..contracts.integration_path_view import IntegrationPathView


class PathTraversalPolicy:
    _ELIGIBLE_TYPES = frozenset(
        {
            RelationType.PROVIDES,
            RelationType.CONSUMES,
            RelationType.DEPENDS_ON,
            RelationType.PUBLISHES,
            RelationType.SUBSCRIBES_TO,
            RelationType.IMPLEMENTS,
        }
    )
    MAX_EXPANSIONS = 10_000

    @property
    def max_expansions(self) -> int:
        return self.MAX_EXPANSIONS

    @property
    def expansion_ceiling(self) -> int:
        return self.MAX_EXPANSIONS

    @property
    def eligible_types(self) -> frozenset[RelationType]:
        return self._ELIGIBLE_TYPES

    @classmethod
    def eligible(cls, relation_type: RelationType | str) -> bool:
        try:
            relation_type = RelationType(relation_type)
        except ValueError:
            return False
        return relation_type in cls._ELIGIBLE_TYPES

    @staticmethod
    def path_key(path: IntegrationPathView | Iterable) -> tuple:
        hops = path.hops if isinstance(path, IntegrationPathView) else tuple(path)
        return tuple(hop.relation_id for hop in hops)

    @staticmethod
    def ordering_key(path: IntegrationPathView) -> tuple:
        return (
            path.hop_count,
            tuple(item.entity.key for item in path.entities),
            tuple(str(hop.relation_id) for hop in path.hops),
        )

    @classmethod
    def order_paths(cls, paths: Iterable[IntegrationPathView]) -> tuple[IntegrationPathView, ...]:
        unique = {cls.path_key(path): path for path in paths}
        return tuple(sorted(unique.values(), key=cls.ordering_key))
