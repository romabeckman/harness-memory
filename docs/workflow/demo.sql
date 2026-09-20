-- E-commerce architecture fixture for Harness Memory.
-- Run after `docker compose up` has applied Alembic head:
-- docker compose exec -T postgres psql -U harness_memory -d harness_memory < docs/workflow/demo.sql
--
-- This example stores architecture knowledge, not transactional cart/order rows.
-- The three microservices are Products, Shopping Cart, and Checkout.
-- Tenant identity is the default Admin user's UUID from migration 006.

BEGIN;

INSERT INTO projects (id, tenant_id, key, name, metadata)
VALUES (
    'd0000000-0000-4000-8000-000000000001',
    '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
    'ecommerce-demo',
    'E-commerce Demo',
    '{"domain":"ecommerce","environment":"demo","fixture":true}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO snapshots (
    id,
    tenant_id,
    project_id,
    revision,
    schema_version,
    payload_hash,
    payload,
    metadata
)
VALUES (
    'd0000000-0000-4000-8000-000000000002',
    '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
    'd0000000-0000-4000-8000-000000000001',
    1,
    '1.0',
    '7b62dfeeaf55e74fbcf73c11ed920e7fc284086b0612f5b510dc02d49b8048fc',
    '{
      "schema_version": "1.0",
      "project": {
        "key": "ecommerce-demo",
        "name": "E-commerce Demo",
        "metadata": {"domain":"ecommerce","environment":"demo","fixture":true}
      },
      "revision": 1,
      "generated_at": "2026-09-20T12:00:00.000000Z",
      "entities": [
        {"key":"products-service","type":"service","name":"Products Service","canonical_key":null,"metadata":{"team":"catalog","runtime":"python"}},
        {"key":"products-api","type":"api","name":"GET /products/{sku}","canonical_key":null,"metadata":{"method":"GET","path":"/products/{sku}","sample_product":{"sku":"SKU-KEYBOARD-01","name":"Mechanical Keyboard","price":89.9,"currency":"USD"}}},
        {"key":"cart-service","type":"service","name":"Shopping Cart Service","canonical_key":null,"metadata":{"team":"commerce","runtime":"python"}},
        {"key":"cart-api","type":"api","name":"POST /cart/items","canonical_key":null,"metadata":{"method":"POST","path":"/cart/items","request_fields":["sku","quantity"]}},
        {"key":"checkout-service","type":"service","name":"Checkout Service","canonical_key":null,"metadata":{"team":"payments","runtime":"python"}},
        {"key":"checkout-api","type":"api","name":"POST /checkout","canonical_key":null,"metadata":{"method":"POST","path":"/checkout","request_fields":["cart_id","payment_method"]}},
        {"key":"order-confirmed","type":"event","name":"OrderConfirmed","canonical_key":null,"metadata":{"channel":"orders.events","version":"1"}}
      ],
      "relations": [
        {"ref":"products-exposes-api","source_entity_key":"products-service","type":"provides","target_entity_key":"products-api","provenance":"declared","metadata":{}},
        {"ref":"cart-reads-product","source_entity_key":"cart-service","type":"consumes","target_entity_key":"products-api","provenance":"declared","metadata":{"sync":true}},
        {"ref":"cart-exposes-api","source_entity_key":"cart-service","type":"provides","target_entity_key":"cart-api","provenance":"declared","metadata":{}},
        {"ref":"checkout-reads-cart","source_entity_key":"checkout-service","type":"consumes","target_entity_key":"cart-api","provenance":"declared","metadata":{"sync":true}},
        {"ref":"checkout-validates-price","source_entity_key":"checkout-service","type":"consumes","target_entity_key":"products-api","provenance":"inferred","metadata":{"purpose":"price revalidation"}},
        {"ref":"checkout-publishes-order","source_entity_key":"checkout-service","type":"publishes","target_entity_key":"order-confirmed","provenance":"declared","metadata":{}}
      ],
      "evidence": [
        {"source":"demo://ecommerce/products-service","excerpt":"Products Service exposes GET /products/{sku} for product lookup.","relation_ref":"products-exposes-api","metadata":{"synthetic":true}},
        {"source":"demo://ecommerce/cart-service","excerpt":"Shopping Cart Service reads product metadata before storing a cart item.","relation_ref":"cart-reads-product","metadata":{"synthetic":true}},
        {"source":"demo://ecommerce/checkout-service","excerpt":"Checkout Service revalidates the product price, reads the cart, then publishes OrderConfirmed.","relation_ref":"checkout-publishes-order","metadata":{"synthetic":true}}
      ]
    }'::jsonb,
    '{"domain":"ecommerce","environment":"demo","fixture":true}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO entities (
    id, tenant_id, identity_id, project_id, snapshot_id,
    entity_key, entity_type, name, metadata
)
VALUES
    (
        'd0000000-0000-4000-8000-000000000003',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        '5f9b90c1-5954-529c-a37c-e5aa9269f41f',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'products-service', 'service', 'Products Service',
        '{"team":"catalog","runtime":"python"}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000004',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        '7e16c497-415a-5d9a-a0c4-c397c1c9b0ff',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'products-api', 'api', 'GET /products/{sku}',
        '{"method":"GET","path":"/products/{sku}","sample_product":{"sku":"SKU-KEYBOARD-01","name":"Mechanical Keyboard","price":89.9,"currency":"USD"}}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000005',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'ce1e40d9-d530-58fa-9626-b11f5b4b4105',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'cart-service', 'service', 'Shopping Cart Service',
        '{"team":"commerce","runtime":"python"}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000006',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        '3fb6cdc0-16fa-5f05-b3e2-32e432cc1355',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'cart-api', 'api', 'POST /cart/items',
        '{"method":"POST","path":"/cart/items","request_fields":["sku","quantity"]}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000007',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'e0498e56-aa7e-5aa2-84e1-8fb041d9dbcf',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'checkout-service', 'service', 'Checkout Service',
        '{"team":"payments","runtime":"python"}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000008',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'e48f8030-0f6b-5274-a825-2f5b5cbda7c6',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'checkout-api', 'api', 'POST /checkout',
        '{"method":"POST","path":"/checkout","request_fields":["cart_id","payment_method"]}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000009',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        '5fc93540-f4a7-501b-8a38-13e4339a1351',
        'd0000000-0000-4000-8000-000000000001',
        'd0000000-0000-4000-8000-000000000002',
        'order-confirmed', 'event', 'OrderConfirmed',
        '{"channel":"orders.events","version":"1"}'::jsonb
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO relations (
    id, tenant_id, snapshot_id,
    source_entity_id, target_entity_id, source_identity_id, target_identity_id,
    relation_type, provenance_kind, metadata
)
VALUES
    (
        'd0000000-0000-4000-8000-000000000010',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000003',
        'd0000000-0000-4000-8000-000000000004',
        '5f9b90c1-5954-529c-a37c-e5aa9269f41f',
        '7e16c497-415a-5d9a-a0c4-c397c1c9b0ff',
        'provides', 'declared', '{}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000011',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000005',
        'd0000000-0000-4000-8000-000000000004',
        'ce1e40d9-d530-58fa-9626-b11f5b4b4105',
        '7e16c497-415a-5d9a-a0c4-c397c1c9b0ff',
        'consumes', 'declared', '{"sync":true}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000012',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000005',
        'd0000000-0000-4000-8000-000000000006',
        'ce1e40d9-d530-58fa-9626-b11f5b4b4105',
        '3fb6cdc0-16fa-5f05-b3e2-32e432cc1355',
        'provides', 'declared', '{}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000013',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000007',
        'd0000000-0000-4000-8000-000000000006',
        'e0498e56-aa7e-5aa2-84e1-8fb041d9dbcf',
        '3fb6cdc0-16fa-5f05-b3e2-32e432cc1355',
        'consumes', 'declared', '{"sync":true}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000014',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000007',
        'd0000000-0000-4000-8000-000000000004',
        'e0498e56-aa7e-5aa2-84e1-8fb041d9dbcf',
        '7e16c497-415a-5d9a-a0c4-c397c1c9b0ff',
        'consumes', 'inferred', '{"purpose":"price revalidation"}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000015',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000007',
        'd0000000-0000-4000-8000-000000000009',
        'e0498e56-aa7e-5aa2-84e1-8fb041d9dbcf',
        '5fc93540-f4a7-501b-8a38-13e4339a1351',
        'publishes', 'declared', '{}'::jsonb
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO evidence (
    id, tenant_id, snapshot_id, relation_id, source, excerpt, metadata
)
VALUES
    (
        'd0000000-0000-4000-8000-000000000016',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000010',
        'demo://ecommerce/products-service',
        'Products Service exposes GET /products/{sku} for product lookup.',
        '{"synthetic":true}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000017',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000011',
        'demo://ecommerce/cart-service',
        'Shopping Cart Service reads product metadata before storing a cart item.',
        '{"synthetic":true}'::jsonb
    ),
    (
        'd0000000-0000-4000-8000-000000000018',
        '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992',
        'd0000000-0000-4000-8000-000000000002',
        'd0000000-0000-4000-8000-000000000015',
        'demo://ecommerce/checkout-service',
        'Checkout Service revalidates the product price, reads the cart, then publishes OrderConfirmed.',
        '{"synthetic":true}'::jsonb
    )
ON CONFLICT (id) DO NOTHING;

-- Activate the fixture snapshot only if this project has no active snapshot already.
UPDATE projects
SET active_snapshot_id = 'd0000000-0000-4000-8000-000000000002'
WHERE id = 'd0000000-0000-4000-8000-000000000001'
  AND tenant_id = '6e5c445f-77c8-4ed7-bc9c-3c9942ba2992'
  AND active_snapshot_id IS NULL;

COMMIT;
