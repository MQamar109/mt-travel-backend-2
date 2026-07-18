# Listing API Currency Conversion (Ticket & Hotel)

## Context

Records can be created in either PKR or SAR, each storing its own
`exchange_rate`. The listing APIs must return **every** record in the currency
requested via the `?currency=` query param, with all monetary values converted
at runtime and totals recomputed for consistency.

Two problems motivated this change:

1. **Hotel list never converted.** The hotel serializer read a custom
   `self.context['display_currency']` key. In DRF list serialization that custom
   key did not reliably reach the child serializer, so it defaulted to `'PKR'`
   and PKR records requested as SAR were returned unconverted. Multiple attempts
   to patch this via custom `ListSerializer` / `get_serializer` overrides failed.
2. **Ticket list only converted the total.** The ticket serializer exposed a
   converted `display_amount` but left the per-line rates (`adt_rate`,
   `chd_rate`, `inf_rate`) in the stored currency, so line items and total were
   in different currencies.

A compounding factor: the backend runs in Docker with a **named volume**
(`app_data:/app`) that shadows the image code, so host edits never reached the
running container. Updates require `docker compose cp` + `restart web` (or
removing the volume), not just a rebuild.

## Approach

Runtime-only conversion in each serializer's `to_representation()` — **nothing is
written to the DB**.

- Read the requested currency from `self.context['request'].query_params['currency']`.
  `request` is always present in serializer context (including inside list
  serializers), which is why the existing ticket `display_amount` already worked.
  This replaces the unreliable custom context key.
- Convert each unit rate with the existing
  `apps/tickets/utils.py::get_display_amount(value, record_currency, exchange_rate, display_currency)`:
  - `display=PKR`: PKR record as-is; SAR record × exchange_rate
  - `display=SAR`: SAR record as-is; PKR record ÷ exchange_rate (2dp, ROUND_HALF_UP)
- Recompute totals from the **converted** rates, mirroring each model's `save()`,
  so displayed line items always sum to the displayed total.
- Records already in the requested currency return untouched (early return).

### Files

- `apps/hotels/serializers.py` — `to_representation` converts
  `single/double/triple/quad_rate`, `bf/lu/di_rate`; recomputes
  `total_room_amount = Σ(qty×rate)×nights`,
  `total_meal_amount = (bf+lu+di)×total_guests×nights`,
  `total_amount = room + meal`.
- `apps/tickets/serializers.py` — `to_representation` converts
  `adt/chd/inf_rate`; recomputes `total_amount = Σ(qty×rate)`; sets
  `display_amount` equal to the recomputed total.
- `apps/hotels/views.py` — removed the failed scaffolding (custom
  `HotelListSerializer`, `get_serializer`/`get_serializer_context`/`list`
  overrides, view-level post-processing). Plain `ListCreateAPIView` again.

### Out of scope

No frontend changes, no stats endpoint, no detail (single-GET) endpoint.
Note: the ticket table still labels the converted total with the record's
original-currency symbol on mixed-currency rows (pre-existing, numbers correct).

## Verification

Verified in-container via Django shell and live HTTP (token minted with
`AccessToken.for_user`):

- Hotel id=2 (PKR, rate 40) `?currency=SAR` → `single_rate=0.50`, `total=0.50`
  (was `20.00`) — the original bug.
- Hotel id=1 (SAR, rate 50) `?currency=PKR` → `total=20250.00` = stored `pkr_amount`.
- Ticket id=26 (SAR, rate 0.1263) `?currency=PKR` → `adt_rate=107.99`,
  `total=283.54` = stored `pkr_amount`.
- Same-currency requests return stored values unchanged.
- `/api/hotels/stats/` still returns HTTP 200.

To redeploy after host edits: `docker compose cp <file> web:/app/<path>` then
`docker compose restart web`.
