# Parcelly Shipping API Reference
> API version 2026-06-01. Parcelly is a fictional shipping platform; this reference is sample content for testing.

## 1. Overview

The Parcelly API lets you compare shipping rates across carriers, buy labels, track parcels and schedule pickups. It is a REST API that accepts and returns JSON over HTTPS.

- Base URL (production): https://api.parcelly.example/v2
- Base URL (sandbox): https://sandbox.api.parcelly.example/v2

Sandbox requests never create real shipments or charges. Sandbox tracking numbers always start with "PCTEST".

## 2. Authentication

Every request must include an API key in the Authorization header:

Authorization: Bearer pk_live_xxxxxxxxxxxxxxxx

Live keys start with **pk_live_** and sandbox keys with **pk_test_**. Keys are created in the dashboard under Settings > Developers. Each account can have up to 10 active keys. Keys can be restricted to read-only access. Never put API keys in client-side code or public repositories; a key that is found in a public GitHub repository is revoked automatically within minutes.

## 3. Versioning

Specify the API version with the Parcelly-Version header, for example Parcelly-Version: 2026-06-01. Requests without the header use the version pinned to your account when it was created. Breaking changes are only introduced in new dated versions; older versions are supported for at least 18 months after a newer version is released.

## 4. Rate Limits

| Plan | Requests per second | Requests per day |
|---|---|---|
| Free | 5 | 1,000 |
| Growth | 25 | 100,000 |
| Scale | 100 | 2,000,000 |
| Enterprise | Custom | Custom |

When you exceed a limit the API returns HTTP 429 with a Retry-After header giving the number of seconds to wait. Rate limit status is returned on every response in the headers X-RateLimit-Limit, X-RateLimit-Remaining and X-RateLimit-Reset.

<!-- pagebreak -->

## 5. Endpoints

### 5.1 Create a shipment and get rates

POST /shipments

Creates a shipment from an origin address, destination address and one or more parcels, and returns available rates from all enabled carriers.

| Field | Type | Required | Description |
|---|---|---|---|
| from_address | object | Yes | Sender name, street, city, postal_code, country (ISO 3166-1 alpha-2) |
| to_address | object | Yes | Recipient address, same structure |
| parcels | array | Yes | Up to 50 parcels; each has length, width, height (cm) and weight (g) |
| carriers | array | No | Limit rates to these carriers, for example ["ups", "canada_post"] |
| reference | string | No | Your own order number, up to 64 characters |
| customs | object | International only | Contents type, items, HS codes and declared values |

Response: a Shipment object with an id starting with "shp_" and a rates array. Each rate has an id starting with "rate_", carrier, service, amount, currency and estimated delivery days. **Rates expire 24 hours** after the shipment is created.

### 5.2 Buy a label

POST /shipments/{shipment_id}/buy

Body: rate_id (required), label_format ("PDF", "PNG" or "ZPL"; default "PDF") and insurance_amount (optional, in the rate currency).

Returns the shipment with a tracking_number and a label_url. Label URLs are valid for 90 days. Insurance costs 1% of the insured value with a minimum of $1.00, up to a maximum insured value of $5,000.

### 5.3 Void a label

POST /shipments/{shipment_id}/void

Labels can be voided for a full refund if they have not been scanned by the carrier. USPS labels must be voided within 30 days of purchase; other carriers within 14 days. Refunds are credited to your Parcelly balance within 3 to 5 business days.

### 5.4 Track a parcel

GET /trackers/{tracking_number}

Returns the current status and a list of tracking events. Possible status values: pre_transit, in_transit, out_for_delivery, delivered, available_for_pickup, return_to_sender, failure, unknown.

### 5.5 Schedule a pickup

POST /pickups

Body: shipment_ids (array), pickup_date (YYYY-MM-DD), earliest_time and latest_time (HH:MM, local time) and instructions (optional, up to 200 characters). The pickup window must be at least **2 hours** long. Same-day pickups must be requested before 12:00 local time.

<!-- pagebreak -->

## 6. Webhooks

Configure a webhook URL in the dashboard to receive events instead of polling.

| Event | Sent when |
|---|---|
| tracker.updated | A parcel's tracking status changes |
| shipment.label_created | A label is purchased |
| shipment.voided | A void request is approved or rejected |
| pickup.confirmed | The carrier confirms a scheduled pickup |
| balance.low | Your prepaid balance drops below the threshold you set |

Each webhook request contains a Parcelly-Signature header: an HMAC-SHA256 of the raw request body using your webhook secret (starts with "whsec_"). Verify the signature before trusting the payload. Your endpoint must respond with a 2xx status within **10 seconds**. Failed deliveries are retried with exponential backoff for up to **3 days** (a maximum of 12 attempts), after which the event is dropped and shown as failed in the dashboard.

## 7. Errors

Errors return a JSON body with code, message and, where relevant, field.

| HTTP status | Error code | Meaning |
|---|---|---|
| 400 | invalid_request | The request body is malformed or a field has the wrong type |
| 401 | authentication_failed | Missing or invalid API key |
| 402 | insufficient_balance | Prepaid balance too low to buy the label |
| 403 | permission_denied | The key is read-only or restricted |
| 404 | not_found | The shipment, tracker or pickup does not exist |
| 409 | rate_expired | The selected rate is older than 24 hours; create the shipment again |
| 409 | label_already_purchased | A label already exists for this shipment |
| 422 | address_invalid | The carrier could not validate an address |
| 429 | rate_limited | Too many requests; see Retry-After |
| 500 | internal_error | Unexpected error on Parcelly's side; safe to retry |
| 503 | carrier_unavailable | The carrier's system is down; try another carrier or retry later |

## 8. Idempotency

POST requests accept an Idempotency-Key header (any unique string up to 255 characters, a UUID is recommended). If a request with the same key is repeated within 24 hours, Parcelly returns the original response instead of performing the action again. Use this when buying labels so that network retries never buy two labels.

## 9. Pagination

List endpoints (GET /shipments, GET /trackers, GET /pickups) return up to 20 items by default and accept a limit parameter of up to 100. Use the next_cursor value from the response as the cursor parameter to get the next page.
