# Visa & Passport Features Design

## Overview

Add two new transactional modules — Visa and Passport — each mirroring the existing Ticket feature end-to-end: backend Django app, REST API, and frontend page with stats, filtered list, add/edit/delete, ledger export/email, and per-record PDF invoice download/email.

Both modules support PKR/SAR dual-currency with runtime conversion identical to the existing ticket and hotel pattern.

---

## Backend

### Architecture

Two fully independent Django apps, matching the established pattern of `apps/tickets` and `apps/hotels`:

```
backend-mtt/apps/visas/
backend-mtt/apps/passports/
```

Each app contains: `__init__.py`, `apps.py`, `admin.py`, `models.py`, `serializers.py`, `filters.py`, `views.py`, `urls.py`, `exports.py`, `email_report.py`, `invoice.py`, `migrations/`.

Both are added to `LOCAL_APPS` in `config/settings/base.py` and wired into `config/urls.py`.

---

### Models

#### Visa

| Field | Type | Constraints |
|---|---|---|
| `vendor` | FK → Vendor | `on_delete=PROTECT`, `related_name='visas'` |
| `created_by` | FK → AUTH_USER_MODEL | `on_delete=PROTECT`, `related_name='visas'` |
| `invoice_no` | CharField(50) | unique |
| `client_name` | CharField(200) | |
| `issued_date` | DateField | db_index=True |
| `visa_number` | CharField(100) | blank=True |
| `description` | TextField | blank=True |
| `amount` | DecimalField(12,2) | stored in record currency |
| `payment_type` | CharField(10) | choices: Credit / Debit |
| `currency` | CharField(5) | choices: PKR / SAR, default PKR |
| `exchange_rate` | DecimalField(8,4) | default 1 |
| `total_amount` | DecimalField(14,2) | auto = `amount` (computed in `save()`) |
| `pkr_amount` | DecimalField(14,2) | auto-computed in `save()` |
| `created_at`, `updated_at` | auto | from TimeStampedModel |

`save()` logic:
```python
self.total_amount = self.amount
if self.currency == 'PKR':
    self.pkr_amount = self.amount
else:
    self.pkr_amount = self.amount * self.exchange_rate
```

Default ordering: `['-issued_date']`

#### Passport

Identical to Visa except:
- `visa_number` → `passport_number` (CharField(100), blank=True)
- `related_name` values use `'passports'`

---

### Serializers

`VisaSerializer` (and `PassportSerializer`) extend `ModelSerializer` with:
- `vendor_name` (read-only CharField from `vendor.name`)
- `created_by_email` (read-only EmailField from `created_by.email`)
- `exchange_rate` (DecimalField, required=True)
- `to_representation()` — reads `?currency=` from `request.query_params`, converts `amount` and `total_amount` using `get_display_amount()` from `apps/tickets/utils.py` when `display_currency != record_currency`

Read-only fields: `id`, `created_by`, `created_by_email`, `total_amount`, `pkr_amount`, `created_at`, `updated_at`.

---

### Filters

`VisaFilter` / `PassportFilter` using `django_filters`:
- `issued_date_from` → `issued_date__gte`
- `issued_date_to` → `issued_date__lte`
- `payment_type` exact
- `vendor` exact

---

### Views

Each app exposes the same seven views as tickets:

| View class | Method | URL |
|---|---|---|
| `VisaListCreateView` | GET, POST | `/api/visas/` |
| `VisaStatsView` | GET | `/api/visas/stats/` |
| `VisaExportView` | GET | `/api/visas/export/` |
| `VisaEmailView` | GET | `/api/visas/email/` |
| `VisaDetailView` | GET, PUT, PATCH, DELETE | `/api/visas/<pk>/` |
| `VisaInvoiceView` | GET | `/api/visas/<pk>/invoice/` |
| `VisaInvoiceEmailView` | GET | `/api/visas/<pk>/invoice/email/` |

- `perform_create` sets `created_by=request.user`
- DELETE requires `IsAdminRole` permission (same as tickets/hotels)
- `VisaStatsView` aggregates: `totalCount`, `totalAmount` (PKR), `creditCount`, `creditAmount`, `debitCount`, `debitAmount`, `thisMonthCount`
- `VisaExportView` supports `?file_format=excel|pdf` and `?currency=PKR|SAR`
- `VisaEmailView` requires `?email=` param with validation
- Invoice views support `?currency=` and `?optional=` (set of optional fields to include in PDF)

Passport views are identical with `Passport` prefix and `/api/passports/` URL prefix.

---

### Exports & Invoice (PDF/Excel)

`exports.py`: Excel via `openpyxl`, PDF via ReportLab — same column layout as ticket exports but with Visa/Passport-specific columns (visa_number or passport_number instead of departure_date/pax breakdown).

`invoice.py`: ReportLab PDF invoice — same visual style as ticket invoice (COMPANY header, navy/blue palette). Shows: invoice_no, client_name, issued_date, vendor, visa_number (or passport_number), amount, payment_type, currency, exchange_rate (if SAR), pkr_amount.

`email_report.py`: sends export PDF/Excel as email attachment, same pattern as `apps/tickets/email_report.py`.

---

### Settings changes

**`config/settings/base.py`** — add to `LOCAL_APPS`:
```python
'apps.visas',
'apps.passports',
```

**`config/urls.py`** — add:
```python
path('api/visas/', include('apps.visas.urls')),
path('api/passports/', include('apps.passports.urls')),
```

---

## Frontend

### Routing & Navigation

**`src/routes/Routes.js`** — add:
```js
VISA: '/visa',
PASSPORT: '/passport',
```

**`src/routes/createBrowserRouter.jsx`** — import `Visa` and `Passport` pages, add two `<Route>` entries wrapped in `PR()`.

**`src/common/components/layout/Sidebar.jsx`** — add to `navItems` (after Hotels):
```js
{ label: 'Visas',     icon: CreditCard, path: ROUTES.VISA      },
{ label: 'Passports', icon: BookOpen,   path: ROUTES.PASSPORT  },
```
Import `CreditCard` and `BookOpen` from `lucide-react`.

---

### API Endpoints

**`src/services/apiEndpoints.js`** — add two new sections:
```js
visas: {
  list: 'visas/',
  create: 'visas/',
  detail: (id) => `visas/${id}/`,
  update: (id) => `visas/${id}/`,
  delete: (id) => `visas/${id}/`,
  stats: 'visas/stats/',
  export: 'visas/export/',
  email: 'visas/email/',
  invoice: (id) => `visas/${id}/invoice/`,
  invoiceEmail: (id) => `visas/${id}/invoice/email/`,
},
passports: {
  // same shape, 'passports/' prefix
},
```

---

### Hooks

New files in `src/hooks/` — each mirrors the equivalent ticket hook:

| Hook file | Mirrors |
|---|---|
| `useVisaStats.js` | `useTicketStats.js` |
| `useVisaList.js` | `useTicketList.js` |
| `useCreateVisa.js` | `useCreateTicket.js` |
| `useUpdateVisa.js` | `useUpdateTicket.js` |
| `useDeleteVisa.js` | `useDeleteTicket.js` |
| `useVisaLedger.js` | `useTicketLedger.js` |
| `useVisaEmail.js` | `useLedgerEmail.js` (ticket variant) |
| `useVisaInvoice.js` | `useTicketInvoice.js` |
| `useVisaInvoiceEmail.js` | `useInvoiceEmail.js` (ticket variant) |

Same set with `Passport` prefix for passports.

All hooks call `apiEndpoints.visas.*` (or `apiEndpoints.passports.*`).

`src/hooks/index.js` is updated to export all new hooks.

---

### Pages & Components

#### `src/pages/visa/Visa.jsx`

Mirrors `src/pages/ticket/Ticket.jsx` exactly — same state shape, same handler pattern, same modal orchestration. Uses `useSettings` for persisting section open/close state under `settings.tabs.visa`.

#### `src/pages/visa/components/`

| Component | Mirrors | Notes |
|---|---|---|
| `VisaStats.jsx` | `TicketStats.jsx` | Same 4-card layout (total, credit, debit, this month) |
| `VisaFilters.jsx` | `TicketFilters.jsx` | Search, date range, vendor select, Add + Ledger buttons |
| `VisaTable.jsx` | `TicketTable.jsx` | Columns: No, Invoice No, Client Name, Vendor, Visa No, Issued Date, Amount, Payment Type, Actions |
| `VisaModal.jsx` | `TicketModal.jsx` | Fields: invoice_no, client_name, issued_date, vendor (select), visa_number (optional), description (optional), amount, payment_type, currency, exchange_rate |
| `LedgerModal.jsx` | Own copy | Ticket's version has ticket-specific optional columns (`dep_date`, `no_of_tickets`). Visa version uses: `vendor`, `visa_number`, `description`. |
| `InvoiceModal.jsx` | Own copy | Ticket's version references `ticket?.invoiceNo`. Visa version references `visa?.invoiceNo`, same optional fields: `issued_date`, `payment_type`, `description`. |

#### `src/pages/passport/` — identical structure

`PassportTable.jsx` shows "Passport No" column instead of "Visa No". `PassportModal.jsx` has `passport_number` field instead of `visa_number`. `LedgerModal.jsx` uses optional columns: `vendor`, `passport_number`, `description`. `InvoiceModal.jsx` references `passport?.invoiceNo`. All other components identical in shape.

---

### SettingsContext

The settings backend already stores arbitrary tab section state. No backend settings schema change is needed — the frontend just reads/writes `settings.tabs.visa.sections` and `settings.tabs.passport.sections` via the existing `updateTabSections(tabName, sections)` call, same as the ticket tab does today.

---

## Currency Conversion

Both Visa and Passport use the same runtime-conversion pattern as tickets:

- `amount` and `total_amount` are stored in `record.currency` (PKR or SAR)
- On list/detail GET, `to_representation()` reads `?currency=` and converts via `get_display_amount()` from `apps/tickets/utils.py`
- `pkr_amount` is always stored in PKR (used for stats aggregation)
- Stats endpoints always aggregate on `pkr_amount` / `total_amount` in PKR (no runtime conversion needed for totals)

---

## Deployment Note

Backend runs in Docker with a named volume (`app_data:/app`). After editing host files, deploy with:
```
docker compose cp <file> web:/app/<path>
docker compose restart web
```
Migrations must be run inside the container:
```
docker compose exec web python manage.py makemigrations visas passports
docker compose exec web python manage.py migrate
```

---

## Out of Scope

- No changes to the dashboard API or dashboard charts for visa/passport data (can be added later)
- No data isolation changes (addressed separately)
- No bulk import/export beyond the existing ledger export pattern
