# Audit & Analysis Log System — Design Spec
**Date:** 2026-06-04
**Project:** SinoMed — National AI Hackathon 2026
**Status:** Approved

---

## Overview

Separate AI analysis logging from security audit logging. All AI analyses are recorded in `AnalysisLog`. Doctor-flagged wrong results are automatically marked for retraining. University admins see their institution's logs; superusers see everything.

---

## Goals

1. Log every AI analysis with full output (confidence, diagnosis, raw JSON, errors)
2. Auto-flag analyses where a doctor marks the AI result as wrong (`flagged_for_training=True`)
3. University role can view and export their institution's flagged data
4. Superuser has full system-wide view, filter, and export
5. Export formats: JSON/CSV (metadata) + ZIP (images + annotations) — rarely used but available

**Out of scope:** Re-running AI on past analyses, real-time model retraining triggers.

---

## Data Architecture

### `AuditLog` (existing — minimal change)
Keep for security events only: `login`, `logout`, `register`, `payment`.
Remove `analyze` action — replaced by `AnalysisLog`.

### `AnalysisLog` (new model in `audit` app)

| Field | Type | Notes |
|-------|------|-------|
| `analysis` | FK(Analysis, CASCADE) | Link to the analysis |
| `ai_diagnosis` | CharField(255) | AI result label |
| `ai_confidence` | FloatField | 0–100 |
| `ai_raw_output` | JSONField | Full AI service response |
| `error_type` | CharField(null, blank) | `low_confidence` / `service_error` / `timeout` |
| `error_detail` | TextField(blank) | Human-readable error message |
| `doctor_verdict` | BooleanField(null) | True=confirmed, False=wrong, None=unreviewed |
| `doctor_note` | TextField(blank) | Doctor's comment |
| `flagged_for_training` | BooleanField(default=False) | Auto-True when doctor marks as wrong |
| `institution` | CharField(blank) | Denormalized from user.institution, for fast filtering |
| `created_at` | DateTimeField(auto_now_add) | |

**Business rule:** When `doctor_verdict=False` is saved → `flagged_for_training` is set to `True` automatically (in `AnalysisResult.save()` or in the view).

---

## Access Control

| Role | `AnalysisLog` | `AuditLog` | Export |
|------|--------------|-----------|--------|
| `superuser` | All records | All records | All |
| `university` | Own institution only (`institution=user.institution`) | — | Own institution |
| `doctor` | Own reviewed analyses only | — | — |
| `student` | No access | — | — |

---

## URL Architecture

Added to `config/urls.py`:
```python
path('audit/', include('audit.urls')),
```

### `audit/urls.py`

| URL | Name | View | Access |
|-----|------|------|--------|
| `/audit/` | `audit_log` | `audit_log_view` | superuser |
| `/audit/analyses/` | `analysis_log` | `analysis_log_view` | university, superuser |
| `/audit/analyses/<int:pk>/` | `analysis_log_detail` | `analysis_log_detail_view` | university (own), superuser |
| `/audit/export/json/` | `export_json` | `export_json_view` | university, superuser |
| `/audit/export/zip/` | `export_zip` | `export_zip_view` | university, superuser |

---

## Views

### `analysis_log_view`
- Filter by: `model_type`, `verdict` (`flagged`/`confirmed`/`unreviewed`), `date_from`, `date_to`
- Scope: superuser → all; university → `institution=user.institution`
- Pagination: 20 records per page
- Context: `logs`, `stats` (total, flagged count, avg confidence, this month), `filter_form`

### `analysis_log_detail_view`
- Shows: original image + Grad-CAM, AI raw JSON (collapsible), doctor verdict + note, flag status
- Also shows: related `AuditLog` events for this analysis (timeline)

### `audit_log_view`
- Superuser only — security events (login/logout/register/payment)
- Filter by: `user`, `action`, `date`
- Pagination: 50 per page

### `export_json_view`
- Query param: `?format=json` (default) or `?format=csv`
- Scope: same as `analysis_log_view` (university = own institution)
- Filters: `?flagged_only=true` (default), or all
- Returns `FileResponse` with appropriate content-type
- JSON schema per record:
  ```json
  {
    "id": 1,
    "analysis_id": 42,
    "model_type": "pneumonia",
    "image_path": "xrays/2026/06/image.jpg",
    "ai_diagnosis": "Patologiya",
    "ai_confidence": 87.3,
    "ai_raw_output": {...},
    "doctor_verdict": false,
    "doctor_note": "Yallig'lanish emas, soya artefakt",
    "institution": "Andijon DTI",
    "created_at": "2026-06-04T10:23:00Z"
  }
  ```

### `export_zip_view`
- Builds ZIP in-memory using `zipfile` + `StreamingHttpResponse`
- Contents: `images/<analysis_id>.<ext>` + `annotations.json` (all flagged records)
- Scope: same access rules
- Filename: `sinomed-export-<institution>-<date>.zip`

---

## Templates

### `audit/analysis_log.html`
- Header with title + export buttons (JSON/CSV | ZIP)
- Filter bar: model type dropdown, verdict dropdown, date range inputs, search button
- Stats strip (superuser only): total, flagged count, avg confidence, this month
- Table: Date | Model | AI result | Confidence | Doctor verdict | Flag | Detail link
- Pagination controls
- Color coding: flagged rows highlighted in red-tinted background

### `audit/analysis_log_detail.html`
- Two-column layout (matches `result.html` style)
- Left: X-ray image + Grad-CAM (if available)
- Right: AI output card (diagnosis badge, confidence bar, raw JSON collapsible), doctor verdict card, flag status badge
- Bottom: AuditLog timeline for this analysis

### `audit/audit_log.html`
- Superuser only
- Table: Timestamp | User | Action | IP | Details (JSON collapsible)
- Filter: user search, action type, date range

---

## Dashboard Integration

Add to `dashboard.html` for `university` and `superuser` roles:
- Quick-stat card: "🔴 N ta flagged tahlil" with link to `analysis_log?verdict=flagged`
- Shown below existing stats grid

---

## Implementation Notes

- `AnalysisLog` is created inside `api_analyze` view after successful AI response
- On error: `AnalysisLog` still created with `error_type` and `error_detail` populated
- `AnalysisLog.doctor_verdict` and `doctor_note` are updated in `result_detail` view when doctor submits — they mirror `AnalysisResult.doctor_confirmed` and `doctor_note` fields (single source of truth is `AnalysisResult`; `AnalysisLog` is the queryable log copy)
- `flagged_for_training` toggled in `result_detail` view when doctor submits `action=report`
- `institution` field is denormalized at creation time (`user.institution`) — no JOIN needed for filtering; empty string if user has no institution
- Export views respect the same institution-scoping as list views
- ZIP export uses Python stdlib `zipfile` — no extra dependencies
- `AuditLog.analyze` action removed from `AuditLog.Action` choices — replaced entirely by `AnalysisLog`

---

## Files to Create / Modify

| Action | File |
|--------|------|
| Modify | `audit/models.py` — add `AnalysisLog` model |
| Modify | `audit/admin.py` — register both models |
| Create | `audit/views.py` — 5 views |
| Create | `audit/urls.py` — 5 URL patterns |
| Modify | `config/urls.py` — include audit.urls |
| Modify | `analysis/views.py` — create AnalysisLog in api_analyze + result_detail |
| Create | `templates/audit/analysis_log.html` |
| Create | `templates/audit/analysis_log_detail.html` |
| Create | `templates/audit/audit_log.html` |
| Modify | `templates/dashboard/dashboard.html` — flagged stat card |
| Run | `makemigrations audit` + `migrate` |
