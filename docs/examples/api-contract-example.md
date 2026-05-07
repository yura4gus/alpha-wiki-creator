# API Contract Example

Purpose: show the expected Alpha-Wiki summary shape for an API contract. This is not an OpenAPI replacement; it points to the source of truth.

```yaml
title: Create Checkout Session API
slug: create-checkout-session-api
transport: rest
service: "[[checkout-service]]"
consumers:
  - "[[web-checkout-flow]]"
version: v1
status: stable
source_file: openapi/checkout.yaml#/paths/~1checkout~1sessions/post
breaking_changes:
  - Removing `session_id` breaks [[web-checkout-flow]].
date_updated: 2026-05-07
```

## Contract

- Endpoint: `/checkout/sessions`
- Method: `POST`
- Auth: user bearer token required.
- Request shape: `{ "cart_id": "string", "return_url": "string" }`
- Response shape: `{ "session_id": "string", "redirect_url": "string", "expires_at": "ISO-8601" }`
- Side effects: creates a payment-provider checkout session.
- Consumers: [[web-checkout-flow]]
- Compatibility warning: do not rename `session_id` or change redirect semantics without a migration note.

## Source Of Truth

- `openapi/checkout.yaml`

