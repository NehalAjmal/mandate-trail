# PRD — Mandate Trail

## 1. One-paragraph pitch

When an AI agent completes a purchase on someone's behalf — the exact pattern Razorpay's live
NPCI/Claude pilot enables on Zomato, Swiggy, and Zepto — and that purchase gets disputed, the
usual chargeback evidence (device fingerprint, click trail, human session behavior) doesn't exist.
What exists instead is a consent mandate, a structured agent action log, and a fulfillment record.
Mandate Trail ingests a dispute, pulls those three records together, runs them through a
deterministic rule engine to score confidence, and only for high-confidence, clean cases drafts a
grounded evidence narrative for a human to approve. Everything else gets escalated to a human,
never guessed at. Every decision is logged and traceable.

## 2. Who this is for

One user type: a merchant risk-ops reviewer looking at a queue of disputes. No end customers, no
multi-tenant accounts, no login. This is an internal tool, not a consumer product.

## 3. Why this problem, specifically

- Razorpay's CEO has publicly framed the hard problem in AI-led commerce as trust, not model
  intelligence — this project is a concrete answer to that framing, not a generic fraud tool.
- A company that builds AI chargeback-defense tools for a living published research in mid-2026
  making the exact point above: agent-initiated disputes lack the evidence trail the whole
  industry is built around, and card-network infrastructure for it (Visa agent tokens, Mastercard
  Agent Pay) is still maturing, not shipped.
- Generic versions of the adjacent ideas are already saturated markets: RBI runs its own live
  mule-account detector across 26+ banks; Chargeflow and Justt have raised a combined ~$150M doing
  generic chargeback bots; Goldman Sachs already runs Claude-based reconciliation at trillion-
  dollar scale. This project is deliberately *not* any of those.

(Full market research behind this is in the buildathon strategy conversation this repo came out
of — not reproduced here to keep this file focused on scope, not justification.)

## 4. In scope (v1 — what actually gets built)

- Ingesting a dispute record shaped like Razorpay's real dispute object (see `BACKEND_SCHEMA.md`
  for the verified field names and status values).
- Pulling together three linked records per dispute: the consent **mandate**, the **agent action
  log**, and the **fulfillment record**.
- A deterministic rule engine that checks: spending cap respected, mandate active at time of
  purchase, merchant matches what was authorized, fulfillment confirmed, timestamps internally
  consistent. Output: a confidence score plus the individual pass/fail per check.
- A branch: high confidence + all checks clean → LLM drafts a grounded evidence narrative,
  system recommends "contest." Anything else → escalate to human, no narrative generated, no
  auto-anything.
- A grounding check on every LLM-generated narrative: any factual claim not traceable to a
  structured field is rejected, and the case is forced to escalation instead of being shown.
- An append-only audit log: every input, every rule outcome, every decision, timestamped.
- A synthetic dataset (60 records across 8 defined archetypes, `BACKEND_SCHEMA.md` §5) with a
  held-out split, used to compute and report precision, recall, and false-positive cost.
- A three-screen local dashboard (queue, detail/audit view, metrics) — see `APP_FLOW.md`.

## 5. Explicitly out of scope (v1) — read this before adding anything

If it's not in section 4, it doesn't get built without updating this file first. In particular:

- **No real payment gateway integration.** No live Razorpay account, no real API keys beyond
  reading their public docs for schema shape. No real money moves, ever.
- **No consumer-facing anything.** No shopper UI, no login/signup, no multi-tenant accounts.
- **Not a general chargeback bot.** Deliberately scoped only to agent-initiated transactions —
  that scoping *is* the differentiation. Don't widen it to "handle all disputes."
- **No real card-network submission.** "Contest" writes an evidence packet to the audit log. It
  does not call any external representment/submission API — none exists that's free or
  sandboxable for this, and the brief doesn't require real submission, only measured precision
  and recall on a held-out set.
- **Not a pre-transaction fraud blocker.** Purely reactive, post-dispute. This keeps it cleanly
  inside "strictly defense-only" — the track's explicit disqualifying rule.
- **No open-ended reason-code coverage.** v1 covers a defined, closed set of reason codes tied to
  the 8 archetypes, not Razorpay's full reason-code list.
- **No production-polish UI.** No custom CSS, no branding, no mobile responsiveness. It should
  look like an internal ops tool, not a startup landing page — see `UI_UX.md`.
- **No paid anything.** No paid API, no paid hosting, no paid database, no credit card anywhere.
- **No deployment requirement.** Local run + a recorded demo for the pitch video satisfies the
  brief. A hosted link is a nice-to-have add later, never a blocker.

If a build session produces code that falls outside section 4, that's scope creep — stop, and
either update this file first or cut the code.

## 6. Success criteria (how we'll know it's done)

Mapped directly to what the judges said they check:

| Judged on | What "done" looks like here |
|---|---|
| Problem taste | This section (§3) can be said out loud in under 30 seconds and it's obviously specific, not generic. |
| Build quality | Full pipeline runs end-to-end on all 60 synthetic records with zero crashes; `pytest` passes; a stranger can clone the repo and get it running from `README.md` alone. |
| AI judgment | The LLM never touches the contest/escalate/accept decision — that's provably true by reading `rules_engine.py` and finding zero LLM/network calls in it. |
| Failure recovery | A specific, engineered failure (LLM hallucinating a claim not in the structured data) is caught by the grounding check, documented, and shown in the demo. |

Plus, concretely: precision, recall, and false-positive cost reported on the 20-record held-out
set, computed live from stored predictions vs. stored ground truth — never hardcoded.

## 7. Open assumptions

- Solo builder, ~5 calendar days.
- No team-based folder/branch strategy needed (see `ARCHITECTURE.md` if this assumption is wrong
  — a team needs a different git workflow note added).
- Python is the implementation language (see `TRD.md` for why).
