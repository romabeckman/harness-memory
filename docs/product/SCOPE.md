Renew development from QA run harness-memory-mcp-plan-20260920164802573-3bv6p5.
Fix only the FAILED and BLOCKED scenarios listed below. Preserve unrelated behavior.

## FAILED: 001-search-exact-entity
Scenario: Search the active demo snapshot by exact entity key and verify products-service is returned.
Definition: {"id":"001-search-exact-entity","criterionIds":["criterion-1"],"required":true,"profile":"mcp","description":"Search the active demo snapshot by exact entity key and verify products-service is returned.","category":"functional","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"key":"products-service"}}},"expectedResultContains":"products-service","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\001-search-exact-entity\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\001-search-exact-entity\response.json

## FAILED: 002-search-prefix-boundary
Scenario: Search with a case-insensitive literal name prefix and maximum result limit; verify products-api is returned from the active snapshot.
Definition: {"id":"002-search-prefix-boundary","criterionIds":["criterion-1"],"required":true,"profile":"mcp","description":"Search with a case-insensitive literal name prefix and maximum result limit; verify products-api is returned from the active snapshot.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"name":"PRODUCTS","limit":100}}},"expectedResultContains":"products-api","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\002-search-prefix-boundary\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\002-search-prefix-boundary\response.json

## FAILED: 003-search-pagination
Scenario: Search active service entities with limit one and verify a next_cursor is returned for deterministic bounded pagination.
Definition: {"id":"003-search-pagination","criterionIds":["criterion-2"],"required":true,"profile":"mcp","description":"Search active service entities with limit one and verify a next_cursor is returned for deterministic bounded pagination.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"type":"service","limit":1}}},"expectedResultContains":"next_cursor","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\003-search-pagination\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\003-search-pagination\response.json

## FAILED: 004-search-literal-wildcard
Scenario: Search with a percent character in the name filter and verify wildcard syntax is treated as literal data with no matching fixture entity.
Definition: {"id":"004-search-literal-wildcard","criterionIds":["criterion-2"],"required":true,"profile":"mcp","description":"Search with a percent character in the name filter and verify wildcard syntax is treated as literal data with no matching fixture entity.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"name":"Order%"}}},"expectedResultContains":"\"count\":0","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\004-search-literal-wildcard\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\004-search-literal-wildcard\response.json

## FAILED: 005-search-invalid-cursor
Scenario: Supply a malformed search cursor and verify the service returns INVALID_SEARCH_CURSOR without leaking persistence details.
Definition: {"id":"005-search-invalid-cursor","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Supply a malformed search cursor and verify the service returns INVALID_SEARCH_CURSOR without leaking persistence details.","category":"negative","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"key":"products-api","cursor":"not-a-cursor"}}},"expectedResultContains":"INVALID_SEARCH_CURSOR","expectedState":"error","expectedReasonCode":"INVALID_SEARCH_CURSOR","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\005-search-invalid-cursor\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\005-search-invalid-cursor\response.json

## FAILED: 006-get-entity-context
Scenario: Read products-service context with default relation and evidence bounds; verify linked demo evidence is returned.
Definition: {"id":"006-get-entity-context","criterionIds":["criterion-3"],"required":true,"profile":"mcp","description":"Read products-service context with default relation and evidence bounds; verify linked demo evidence is returned.","category":"functional","mcp":{"method":"tools/call","params":{"name":"get_context","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000003","limit":25,"evidence_limit":5}},"expectedResultContains":"demo://ecommerce/products-service","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\006-get-entity-context\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\006-get-entity-context\response.json

## FAILED: 007-context-no-evidence
Scenario: Read products-api context with evidence_limit zero and verify relation topology remains available while evidence arrays are empty.
Definition: {"id":"007-context-no-evidence","criterionIds":["criterion-3"],"required":true,"profile":"mcp","description":"Read products-api context with evidence_limit zero and verify relation topology remains available while evidence arrays are empty.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"get_context","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000004","evidence_limit":0}},"expectedResultContains":"\"evidence\":[]","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\007-context-no-evidence\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\007-context-no-evidence\response.json

## FAILED: 008-dependencies-inbound
Scenario: Read products-api inbound dependencies and verify cart-service is returned as a consumer.
Definition: {"id":"008-dependencies-inbound","criterionIds":["criterion-3"],"required":true,"profile":"mcp","description":"Read products-api inbound dependencies and verify cart-service is returned as a consumer.","category":"functional","mcp":{"method":"tools/call","params":{"name":"get_dependencies","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000004","direction":"inbound"}},"expectedResultContains":"cart-service","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\008-dependencies-inbound\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\008-dependencies-inbound\response.json

## FAILED: 009-get-outbound-dependencies
Scenario: Read cart-service outbound dependencies with limit one and no evidence; verify products-api is the returned dependency and the call stays bounded.
Definition: {"id":"009-get-outbound-dependencies","criterionIds":["criterion-3"],"required":true,"profile":"mcp","description":"Read cart-service outbound dependencies with limit one and no evidence; verify products-api is the returned dependency and the call stays bounded.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"get_dependencies","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000005","direction":"outbound","limit":1,"evidence_limit":0}},"expectedResultContains":"products-api","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\009-get-outbound-dependencies\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\009-get-outbound-dependencies\response.json

## FAILED: 010-path-direct
Scenario: Find the direct products-service to products-api path with max_depth one and verify a termination field is returned.
Definition: {"id":"010-path-direct","criterionIds":["criterion-4"],"required":true,"profile":"mcp","description":"Find the direct products-service to products-api path with max_depth one and verify a termination field is returned.","category":"functional","mcp":{"method":"tools/call","params":{"name":"find_integration_paths","arguments":{"source_entity_id":"d0000000-0000-4000-8000-000000000003","target_entity_id":"d0000000-0000-4000-8000-000000000004","max_depth":1}},"expectedResultContains":"termination_reason","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\010-path-direct\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\010-path-direct\response.json

## FAILED: 011-path-zero-hop
Scenario: Find a path from products-api to itself and verify the zero-hop path is represented deterministically.
Definition: {"id":"011-path-zero-hop","criterionIds":["criterion-4"],"required":true,"profile":"mcp","description":"Find a path from products-api to itself and verify the zero-hop path is represented deterministically.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"find_integration_paths","arguments":{"source_entity_id":"d0000000-0000-4000-8000-000000000004","target_entity_id":"d0000000-0000-4000-8000-000000000004"}},"expectedResultContains":"hop_count","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\011-path-zero-hop\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\011-path-zero-hop\response.json

## FAILED: 012-find-known-integration-path
Scenario: Find paths from checkout-service to products-api within default traversal bounds and verify a known path is returned.
Definition: {"id":"012-find-known-integration-path","criterionIds":["criterion-4"],"required":true,"profile":"mcp","description":"Find paths from checkout-service to products-api within default traversal bounds and verify a known path is returned.","category":"functional","mcp":{"method":"tools/call","params":{"name":"find_integration_paths","arguments":{"source_entity_id":"d0000000-0000-4000-8000-000000000007","target_entity_id":"d0000000-0000-4000-8000-000000000004","max_depth":4,"max_paths":10,"evidence_limit":5,"owner_limit":5}},"expectedResultContains":"products-api","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\012-find-known-integration-path\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\012-find-known-integration-path\response.json

## FAILED: 013-path-unknown-endpoint
Scenario: Use an unknown source UUID for path lookup and verify the stable endpoint-not-found response does not disclose tenant data.
Definition: {"id":"013-path-unknown-endpoint","criterionIds":["criterion-8"],"required":true,"profile":"mcp","description":"Use an unknown source UUID for path lookup and verify the stable endpoint-not-found response does not disclose tenant data.","category":"security","mcp":{"method":"tools/call","params":{"name":"find_integration_paths","arguments":{"source_entity_id":"00000000-0000-0000-0000-000000000000","target_entity_id":"d0000000-0000-4000-8000-000000000007"}},"expectedResultContains":"INTEGRATION_PATH_ENDPOINT_NOT_FOUND","expectedState":"error","expectedReasonCode":"INTEGRATION_PATH_ENDPOINT_NOT_FOUND","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\013-path-unknown-endpoint\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\013-path-unknown-endpoint\response.json

## FAILED: 014-path-invalid-depth
Scenario: Call find_integration_paths with max_depth zero and verify strict traversal-bound validation rejects the request.
Definition: {"id":"014-path-invalid-depth","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Call find_integration_paths with max_depth zero and verify strict traversal-bound validation rejects the request.","category":"negative","mcp":{"method":"tools/call","params":{"name":"find_integration_paths","arguments":{"source_entity_id":"d0000000-0000-4000-8000-000000000003","target_entity_id":"d0000000-0000-4000-8000-000000000004","max_depth":0}},"expectedResultContains":"max_depth","expectedState":"error","expectedReasonCode":"INVALID_ARGUMENT","expectedIsError":true}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\014-path-invalid-depth\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\014-path-invalid-depth\response.json

## FAILED: 015-impact-bounded
Scenario: Analyze products-api impact with max_depth one and max_consumers one and verify the bounded response marks truncation.
Definition: {"id":"015-impact-bounded","criterionIds":["criterion-5"],"required":true,"profile":"mcp","description":"Analyze products-api impact with max_depth one and max_consumers one and verify the bounded response marks truncation.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"analyze_impact","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000004","change_type":"contract","description":"API contract review","max_depth":1,"max_consumers":1}},"expectedResultContains":"\"truncated\":true","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\015-impact-bounded\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\015-impact-bounded\response.json

## FAILED: 016-analyze-products-impact
Scenario: Analyze a contract change on products-api and verify cart-service is classified as a known consumer.
Definition: {"id":"016-analyze-products-impact","criterionIds":["criterion-5"],"required":true,"profile":"mcp","description":"Analyze a contract change on products-api and verify cart-service is classified as a known consumer.","category":"functional","mcp":{"method":"tools/call","params":{"name":"analyze_impact","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000004","change_type":"contract","description":"price response contract changes","changed_fields":["price"],"max_depth":4,"max_consumers":100,"max_paths":25,"evidence_limit":5,"owner_limit":5,"max_result_bytes":1048576}},"expectedResultContains":"cart-service","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\016-analyze-products-impact\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\016-analyze-products-impact\response.json

## FAILED: 017-impact-missing-target
Scenario: Call analyze_impact without any change target and verify the stable invalid impact contract response is returned.
Definition: {"id":"017-impact-missing-target","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Call analyze_impact without any change target and verify the stable invalid impact contract response is returned.","category":"negative","mcp":{"method":"tools/call","params":{"name":"analyze_impact","arguments":{"change_type":"contract"}},"expectedResultContains":"INVALID_IMPACT_CONTRACT","expectedState":"error","expectedReasonCode":"INVALID_IMPACT_CONTRACT","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\017-impact-missing-target\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\017-impact-missing-target\response.json

## FAILED: 018-impact-invalid-byte-bound
Scenario: Call analyze_impact with a result budget below 64 KiB and verify strict byte-bound validation rejects the request.
Definition: {"id":"018-impact-invalid-byte-bound","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Call analyze_impact with a result budget below 64 KiB and verify strict byte-bound validation rejects the request.","category":"negative","mcp":{"method":"tools/call","params":{"name":"analyze_impact","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000004","max_result_bytes":1024}},"expectedResultContains":"max_result_bytes","expectedState":"error","expectedReasonCode":"INVALID_ARGUMENT","expectedIsError":true}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\018-impact-invalid-byte-bound\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\018-impact-invalid-byte-bound\response.json

## FAILED: 019-idempotent-demo-publication
Scenario: Submit the exact demo snapshot at its existing revision and verify the retry is reported as ALREADY_PUBLISHED without replacing the active snapshot.
Definition: {"id":"019-idempotent-demo-publication","criterionIds":["criterion-6","criterion-9"],"required":true,"profile":"mcp","description":"Submit the exact demo snapshot at its existing revision and verify the retry is reported as ALREADY_PUBLISHED without replacing the active snapshot.","category":"resilience","mcp":{"method":"tools/call","params":{"name":"publish_project_snapshot","arguments":{"request":{"schema_version":"1.0","project":{"key":"ecommerce-demo","name":"E-commerce Demo","metadata":{"domain":"ecommerce","environment":"demo","fixture":true}},"revision":1,"generated_at":"2026-09-20T12:00:00.000000Z","entities":[{"key":"products-service","type":"service","name":"Products Service","canonical_key":null,"metadata":{"team":"catalog","runtime":"python"}},{"key":"products-api","type":"api","name":"GET /products/{sku}","canonical_key":null,"metadata":{"method":"GET","path":"/products/{sku}","sample_product":{"sku":"SKU-KEYBOARD-01","name":"Mechanical Keyboard","price":89.9,"currency":"USD"}}},{"key":"cart-service","type":"service","name":"Shopping Cart Service","canonical_key":null,"metadata":{"team":"commerce","runtime":"python"}},{"key":"cart-api","type":"api","name":"POST /cart/items","canonical_key":null,"metadata":{"method":"POST","path":"/cart/items","request_fields":["sku","quantity"]}},{"key":"checkout-service","type":"service","name":"Checkout Service","canonical_key":null,"metadata":{"team":"payments","runtime":"python"}},{"key":"checkout-api","type":"api","name":"POST /checkout","canonical_key":null,"metadata":{"method":"POST","path":"/checkout","request_fields":["cart_id","payment_method"]}},{"key":"order-confirmed","type":"event","name":"OrderConfirmed","canonical_key":null,"metadata":{"channel":"orders.events","version":"1"}}],"relations":[{"ref":"products-exposes-api","source_entity_key":"products-service","type":"provides","target_entity_key":"products-api","provenance":"declared","metadata":{}},{"ref":"cart-reads-product","source_entity_key":"cart-service","type":"consumes","target_entity_key":"products-api","provenance":"declared","metadata":{"sync":true}},{"ref":"cart-exposes-api","source_entity_key":"cart-service","type":"provides","target_entity_key":"cart-api","provenance":"declared","metadata":{}},{"ref":"checkout-reads-cart","source_entity_key":"checkout-service","type":"consumes","target_entity_key":"cart-api","provenance":"declared","metadata":{"sync":true}},{"ref":"checkout-validates-price","source_entity_key":"checkout-service","type":"consumes","target_entity_key":"products-api","provenance":"inferred","metadata":{"purpose":"price revalidation"}},{"ref":"checkout-publishes-order","source_entity_key":"checkout-service","type":"publishes","target_entity_key":"order-confirmed","provenance":"declared","metadata":{}}],"evidence":[{"source":"demo://ecommerce/products-service","excerpt":"Products Service exposes GET /products/{sku} for product lookup.","relation_ref":"products-exposes-api","metadata":{"synthetic":true}},{"source":"demo://ecommerce/cart-service","excerpt":"Shopping Cart Service reads product metadata before storing a cart item.","relation_ref":"cart-reads-product","metadata":{"synthetic":true}},{"source":"demo://ecommerce/checkout-service","excerpt":"Checkout Service revalidates the product price, reads the cart, then publishes OrderConfirmed.","relation_ref":"checkout-publishes-order","metadata":{"synthetic":true}}]}}},"expectedResultContains":"ALREADY_PUBLISHED","expectedState":"success","expectedReasonCode":"already_published","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\019-idempotent-demo-publication\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\019-idempotent-demo-publication\response.json

## FAILED: 020-publish-invalid-graph
Scenario: Publish a schema-valid snapshot with a relation endpoint absent from its entity set and verify domain invariant validation rejects it without persistence.
Definition: {"id":"020-publish-invalid-graph","criterionIds":["criterion-6","criterion-7"],"required":true,"profile":"mcp","description":"Publish a schema-valid snapshot with a relation endpoint absent from its entity set and verify domain invariant validation rejects it without persistence.","category":"negative","mcp":{"method":"tools/call","params":{"name":"publish_project_snapshot","arguments":{"request":{"schema_version":"1.0","project":{"key":"qa-mcp-invalid-graph"},"revision":1,"generated_at":"2026-09-20T12:00:00Z","entities":[{"key":"orphan-service","type":"service"}],"relations":[{"ref":"bad-rel","source_entity_key":"orphan-service","type":"provides","target_entity_key":"missing-api","provenance":"declared"}],"evidence":[]}}},"expectedResultContains":"DOMAIN_INVARIANT_VIOLATION","expectedState":"error","expectedReasonCode":"DOMAIN_INVARIANT_VIOLATION","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\020-publish-invalid-graph\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\020-publish-invalid-graph\response.json

## FAILED: 021-invalid-search-without-filter
Scenario: Call search_entities without any discovery filter and verify strict validation rejects the request before a broad unbounded search.
Definition: {"id":"021-invalid-search-without-filter","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Call search_entities without any discovery filter and verify strict validation rejects the request before a broad unbounded search.","category":"negative","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"limit":25}}},"expectedResultContains":"at least one discovery filter","expectedState":"error","expectedReasonCode":"INVALID_ARGUMENT","expectedIsError":true}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\021-invalid-search-without-filter\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\021-invalid-search-without-filter\response.json

## FAILED: 022-context-invalid-limit
Scenario: Call get_context with limit zero and verify strict lower-bound validation rejects the request.
Definition: {"id":"022-context-invalid-limit","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Call get_context with limit zero and verify strict lower-bound validation rejects the request.","category":"negative","mcp":{"method":"tools/call","params":{"name":"get_context","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000004","limit":0}},"expectedResultContains":"limit","expectedState":"error","expectedReasonCode":"INVALID_ARGUMENT","expectedIsError":true}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\022-context-invalid-limit\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\022-context-invalid-limit\response.json

## FAILED: 023-invalid-direction-bound
Scenario: Call get_dependencies with an unsupported direction and verify enum validation rejects the call.
Definition: {"id":"023-invalid-direction-bound","criterionIds":["criterion-7"],"required":true,"profile":"mcp","description":"Call get_dependencies with an unsupported direction and verify enum validation rejects the call.","category":"boundary","mcp":{"method":"tools/call","params":{"name":"get_dependencies","arguments":{"entity_id":"d0000000-0000-4000-8000-000000000005","direction":"sideways","limit":25,"evidence_limit":5}},"expectedResultContains":"direction","expectedState":"error","expectedReasonCode":"INVALID_ARGUMENT","expectedIsError":true}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\023-invalid-direction-bound\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\023-invalid-direction-bound\response.json

## FAILED: 024-reject-untrusted-tenant-field
Scenario: Add an untrusted tenant_id field to a search request and verify the strict public schema rejects it instead of changing tenant scope.
Definition: {"id":"024-reject-untrusted-tenant-field","criterionIds":["criterion-8"],"required":true,"profile":"mcp","description":"Add an untrusted tenant_id field to a search request and verify the strict public schema rejects it instead of changing tenant scope.","category":"security","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"key":"products-service","tenant_id":"other-tenant"}}},"expectedResultContains":"tenant_id","expectedState":"error","expectedReasonCode":"INVALID_ARGUMENT","expectedIsError":true}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\024-reject-untrusted-tenant-field\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\024-reject-untrusted-tenant-field\response.json

## FAILED: 025-unknown-entity-safe-error
Scenario: Request context for an unknown UUID and verify the response is a stable ENTITY_NOT_FOUND result without identifier disclosure.
Definition: {"id":"025-unknown-entity-safe-error","criterionIds":["criterion-8"],"required":true,"profile":"mcp","description":"Request context for an unknown UUID and verify the response is a stable ENTITY_NOT_FOUND result without identifier disclosure.","category":"negative","mcp":{"method":"tools/call","params":{"name":"get_context","arguments":{"entity_id":"d0000000-0000-4000-8000-000000009999","limit":25,"evidence_limit":5}},"expectedResultContains":"ENTITY_NOT_FOUND","expectedState":"error","expectedReasonCode":"ENTITY_NOT_FOUND","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\025-unknown-entity-safe-error\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\025-unknown-entity-safe-error\response.json

## FAILED: 026-unauthenticated-tool-denied
Scenario: Call a read tool without a bearer token and verify authentication is required before tool execution.
Definition: {"id":"026-unauthenticated-tool-denied","criterionIds":["criterion-8"],"required":true,"profile":"mcp","description":"Call a read tool without a bearer token and verify authentication is required before tool execution.","category":"security","authProfile":"none","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"key":"products-service"}}},"expectedResultContains":"authentication required","expectedState":"error","expectedReasonCode":"invalid_token","expectedIsError":true}}
Observed: MCP HTTP 401
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\026-unauthenticated-tool-denied\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\026-unauthenticated-tool-denied\response.json

## FAILED: 027-recoverable-read-after-negative
Scenario: Repeat a valid exact-key search after a prior rejected request and verify the service still returns products-service deterministically.
Definition: {"id":"027-recoverable-read-after-negative","criterionIds":["criterion-9"],"required":true,"profile":"mcp","description":"Repeat a valid exact-key search after a prior rejected request and verify the service still returns products-service deterministically.","category":"resilience","mcp":{"method":"tools/call","params":{"name":"search_entities","arguments":{"request":{"key":" products-service ","project":"ecommerce-demo","limit":1}}},"expectedResultContains":"products-service","expectedState":"success","expectedReasonCode":"ready","expectedIsError":false}}
Observed: MCP HTTP 400
Evidence: C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\027-recoverable-read-after-negative\request.json, C:\Users\romab\Codigo\harness-memory\docs\qa\runs\harness-memory-mcp-plan-20260920164802573-3bv6p5\evidence\027-recoverable-read-after-negative\response.json