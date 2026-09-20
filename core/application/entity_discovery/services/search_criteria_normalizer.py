from collections.abc import Mapping

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.use_cases.search_entities.inbound import (
    SearchEntitiesInput,
)


class NormalizeEntitySearch:
    def execute(self, request: SearchEntitiesInput | Mapping[str, object]) -> EntitySearchCriteria:
        input_model = (
            request
            if isinstance(request, SearchEntitiesInput)
            else SearchEntitiesInput.model_validate(request)
        )
        return EntitySearchCriteria(
            key=input_model.key,
            name=input_model.name,
            type=input_model.type,
            project=input_model.project,
        )


SearchCriteriaNormalizer = NormalizeEntitySearch
