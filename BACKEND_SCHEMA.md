# BACKEND_SCHEMA — the data layer

## 0. Ground rule before anything else

**`ground_truth_label` (defined in §1.4) must never be read by `rules_engine.py` or
`evidence_writer.py`. Only `metrics.py` may read it, and only after a decision has already been
recorded.** This is not a style preference — if the decision logic can see the answer key, every
precision/recall number this project reports is invalid, silently. This is the single easiest way
to accidentally fake a good-looking result without meaning to. Treat it as a hard boundary.

## 1. Tables

All tables live in `data/schema.sql` and get created fresh by `data/seed/generate_dataset.py`.
Field names marked **[real]** are copied from Razorpay's own public API/webhook documentation
(`https://razorpay.com/docs/api/disputes/` and `https://razorpay.com/docs/webhooks/disputes/`,
checked September 2026) so that this schema would map onto real webhook payloads with minimal
changes later. Fields marked **[ours]** are this project's own additions — the records Razorpay's
system doesn't have, because they describe what the *agent* did, not what a human did.

### 1.1 `mandates`

The consent a user gave an agent — this is our stand-in for what Razorpay/NPCI's UPI Reserve Pay
consent record would contain.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | e.g. `mandate_0001` |
| `user_id` | TEXT | synthetic, e.g. `user_014` |
| `agent_id` | TEXT | which agent this mandate authorizes, e.g. `claude_agent` |
| `merchant_id` | TEXT | the *only* merchant this mandate authorizes spend at |
| `spending_cap_amount` | INTEGER | in paise, matching Razorpay's amount convention **[real convention]** |
| `spending_cap_currency` | TEXT | `INR` |
| `valid_from` | INTEGER | unix timestamp |
| `valid_until` | INTEGER | unix timestamp |
| `status` | TEXT | `active` \| `revoked` \| `expired` **[ours]** |
| `created_at` | INTEGER | unix timestamp |

### 1.2 `agent_actions`

The structured trace of what the agent actually did — this is our answer to the "no click trail"
problem: it's not a device fingerprint, it's a log of agent decisions.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | e.g. `action_0001` |
| `mandate_id` | TEXT FK → mandates.id | |
| `action_type` | TEXT | `search` \| `select` \| `confirm` \| `pay` **[ours]** |
| `merchant_id` | TEXT | must be cross-checked against the mandate's merchant_id by the rule engine |
| `item_description` | TEXT | free text, e.g. "2x paneer tikka, 1x butter naan" |
| `amount` | INTEGER | paise |
| `currency` | TEXT | `INR` |
| `timestamp` | INTEGER | unix timestamp |
| `raw_payload` | TEXT (JSON) | the full structured record an agent orchestration layer would log |

### 1.3 `orders`

The commercial record connecting an agent's confirming action to an actual order.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | e.g. `order_0001` |
| `mandate_id` | TEXT FK → mandates.id | |
| `confirming_action_id` | TEXT FK → agent_actions.id | the `action_type = 'pay'` row that placed this order |
| `merchant_id` | TEXT | |
| `amount` | INTEGER | paise |
| `currency` | TEXT | `INR` |
| `status` | TEXT | `placed` \| `fulfilled` \| `cancelled` **[ours]** |
| `placed_at` | INTEGER | unix timestamp |
| `fulfilled_at` | INTEGER, nullable | unix timestamp, null if never fulfilled |

### 1.4 `disputes`

Shaped directly off Razorpay's real dispute object, as seen in their public webhook samples.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | e.g. `disp_0001`, mirroring Razorpay's `disp_...` ID prefix **[real convention]** |
| `order_id` | TEXT FK → orders.id | |
| `payment_id` | TEXT | synthetic, `pay_...` prefix **[real convention]** |
| `amount` | INTEGER | paise **[real field]** |
| `currency` | TEXT | `INR` **[real field]** |
| `amount_deducted` | INTEGER | **[real field]** — 0 until a dispute is lost |
| `reason_code` | TEXT | **[real field]**. Confirmed real values seen in Razorpay's docs: `goods_or_services_not_received_or_partially_received`, `non_matching_account_number`, `processed_invalid_expired_card`. Razorpay's full reason-code list is longer — check `https://razorpay.com/docs/payments/disputes/` before assuming these 3 are exhaustive; v1 only needs to cover the archetypes in §5. |
| `phase` | TEXT | **[real field]** — confirmed values: `chargeback`, `fraud` |
| `status` | TEXT | **[real field]** — confirmed values: `open`, `under_review`, `action_required`, `won`, `lost`, `closed`. This describes the *card network's* view of the case lifecycle — it is NOT the same thing as our own recommended action, which lives in `decisions.recommended_action` below. Don't conflate the two. |
| `respond_by` | INTEGER | **[real field]** unix timestamp |
| `raised_at` | INTEGER | (`created_at` in Razorpay's real payload — renamed here for clarity against our other `created_at` columns) |
| `ground_truth_label` | TEXT | **[ours, evaluation-only — see §0]** `contest` \| `escalate` \| `accept`. Set once, at generation time, by the archetype definition in §5. |
| `is_held_out` | BOOLEAN | **[ours]** 1 if this record is in the 20-record held-out evaluation set, 0 otherwise. Set at generation time. Only `metrics.py` should filter on this. |

### 1.5 `evidence_packets`

Only created for disputes the rule engine marked high-confidence.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | |
| `dispute_id` | TEXT FK → disputes.id | |
| `narrative_text` | TEXT | the LLM-drafted explanation — maps to Razorpay's real `evidence.explanation_letter` / `evidence.summary` fields **[real field mapping]** |
| `grounding_check_passed` | BOOLEAN | see `AI_RULES.md` §1-2 for what this checks |
| `mapped_evidence_fields` | TEXT (JSON) | which of Razorpay's real evidence sub-fields this maps to — see §2 below |
| `generated_at` | INTEGER | unix timestamp |

### 1.6 `decisions`

The system's actual output. This is the ONLY table `metrics.py` compares against
`disputes.ground_truth_label`.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | |
| `dispute_id` | TEXT FK → disputes.id | |
| `confidence_score` | REAL | 0.0-1.0, from `rules_engine.py` |
| `checks_passed` | TEXT (JSON) | e.g. `{"within_cap": true, "mandate_active": true, "merchant_matches": true, "fulfilled": true, "timestamps_consistent": true}` |
| `recommended_action` | TEXT | `contest` \| `escalate` \| `accept` — our system's output |
| `decided_at` | INTEGER | unix timestamp |
| `decided_by` | TEXT | `system` \| `human` — set to `human` once a reviewer approves/overrides in the dashboard |

### 1.7 `audit_log`

Append-only. Never updated, never deleted. This table IS the audit trail the pitch depends on.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `dispute_id` | TEXT FK → disputes.id | |
| `event_type` | TEXT | e.g. `dispute_ingested`, `rule_check_run`, `narrative_generated`, `grounding_check_failed`, `decision_recorded`, `human_override` |
| `event_payload` | TEXT (JSON) | full detail of what happened |
| `created_at` | INTEGER | unix timestamp |

## 2. How our records map to Razorpay's real evidence submission fields

Razorpay's real dispute `evidence` object (from their public webhook docs) has named sub-fields
including `summary`, `shipping_proof`, `billing_proof`, `customer_communication`,
`proof_of_service`, `explanation_letter`, `access_activity_log`, `term_and_conditions`, and
`submitted_at`, among others. This project's records map onto those as follows — worth stating
explicitly in the pitch, since it shows the evidence design isn't invented, it's grounded in what
a real submission would actually need:

- `agent_actions` (our structured action trace) → `access_activity_log`
- `mandates` (the consent record) → `customer_communication` and/or `term_and_conditions`
- `orders.fulfilled_at` (fulfillment confirmation) → `proof_of_service`
- `evidence_packets.narrative_text` (LLM-drafted, grounded) → `explanation_letter` / `summary`

## 3. Confidence scoring — the actual rule set (deterministic, no LLM)

Each check is independent and boolean. Suggested weights below are a starting point, not gospel —
tune during Phase 2 of `PLAN.md`, but keep the check *logic* deterministic no matter what weights
you land on:

1. `within_cap` — order amount ≤ mandate's `spending_cap_amount`
2. `mandate_active` — order `placed_at` falls between the mandate's `valid_from` and `valid_until`,
   and mandate `status = 'active'`
3. `merchant_matches` — the order's `merchant_id` equals the mandate's `merchant_id`
4. `fulfilled` — order `status = 'fulfilled'` and `fulfilled_at` is not null
5. `timestamps_consistent` — no impossible ordering (e.g. `fulfilled_at` before `placed_at`;
   confirming action's timestamp after the order's `placed_at`)

`confidence_score` = fraction of checks passed (0.0-1.0). Suggested threshold: **all 5 checks
pass → high confidence → contest path. Any single check fails → escalate, no narrative
generated.** This is intentionally strict — a system that "mostly" trusts a shaky case is worse
than one that escalates too often. Tune with real numbers from the held-out set in Phase 4, not
by feel.

## 4. False-positive cost — defined concretely, not just "accuracy"

Report these three numbers separately, computed against the 20-record held-out set, never
hardcoded:

- **Precision** = of the cases the system recommended `contest`, what fraction had
  `ground_truth_label = contest`.
- **Recall** = of the cases with `ground_truth_label = contest`, what fraction the system actually
  caught and recommended `contest` on.
- **False-positive cost** = cases where the system recommended `contest` but
  `ground_truth_label` was NOT `contest`. Report this as a count and name the real-world cost:
  card-network penalty risk plus wasted ops time on a case that shouldn't have been fought. Keep
  this distinct from a wrongly-escalated case (which only costs review time, not a fight) — don't
  collapse both into one "error rate" number, since they have different real costs.

## 5. Synthetic dataset — 60 records, 8 archetypes, 20 held out

Generated once by `data/seed/generate_dataset.py` with a **fixed random seed** (so re-running it
produces the identical dataset every time — precision/recall must be reproducible, not different
on every demo run). ~7-8 records per archetype, distributed roughly evenly. Hold out 20 records
total (2-3 per archetype, chosen at generation time and tagged) — the other 40 are for
development/tuning and must never be reported as "the" evaluation numbers.

| # | Archetype | `ground_truth_label` | What makes it that label |
|---|---|---|---|
| 1 | Clean legitimate | `contest` | Within cap, mandate active, merchant matches, fulfilled, timestamps consistent |
| 2 | Cap exceeded | `escalate` | Order amount > mandate's spending cap — arguably not properly authorized |
| 3 | Expired/revoked mandate | `escalate` | Order placed outside the mandate's valid window, or mandate status ≠ active |
| 4 | Wrong merchant | `escalate` | Order merchant doesn't match what the mandate authorized |
| 5 | Not fulfilled | `accept` | No fulfillment confirmation — `goods_or_services_not_received` is often a legitimate dispute |
| 6 | Timestamp inconsistency | `escalate` | e.g. fulfillment logged before the order was even placed — a data-integrity red flag, needs a human |
| 7 | Duplicate transaction | `escalate` | Two near-identical agent actions close in time — ambiguous, could be a legitimate re-order or a glitch |
| 8 | Clean legitimate, mislabeled reason code | `contest` | All checks pass, but the customer's claimed reason code doesn't match the records — tests that the system isn't fooled by the claimed reason alone |

This taxonomy is the actual failure-recovery test bed too: archetype 6 or 7 (sparse/conflicting
evidence) is the deliberate case to feed the evidence writer early, specifically to trigger and
document the grounding-check catching a hallucinated claim — see `PLAN.md` Phase 3.
