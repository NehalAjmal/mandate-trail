# PLAN — phase-gated roadmap

## How to use this file

- **Work exactly one phase at a time.** Do not start Phase N+1 until Phase N's exit criteria are
  all checked off and you've explicitly said "proceed to Phase N+1."
- **Re-read `PRD.md`, `ARCHITECTURE.md`, and `AI_RULES.md` before starting each phase**, not just
  once at the beginning — this is what keeps a multi-day, multi-session AI-assisted build from
  drifting.
- Dates below assume you're starting **today, Tuesday September 1, 2026**, against the
  **September 5 close**. If you're reading this later than Sep 1, shift every date forward by the
  same amount — but don't compress phases into fewer days. Cutting phases under deadline pressure
  is exactly how bugs and scope creep happen; better to cut a nice-to-have from `PRD.md` §4 than
  to skip a phase's testing.
- Submitting close to but before the deadline, rather than exactly at it, is worth the discipline
  — programs like this often work through submissions as they arrive rather than waiting for the
  close.

---

### Phase 0 — Prove the plumbing works (Tue Sep 1, morning)

The single most common way solo AI-assisted builds lose a day: discovering on Day 3 that the LLM
API key, SDK version, or SQLite setup was broken from the start. Prove all of it works, in
isolation, before building anything real on top of it.

**Tasks:**
- `git init`, create the repo structure from `ARCHITECTURE.md` §2 (empty files are fine for now).
- `venv` + `pip install -r requirements.txt` (from `TRD.md` §5).
- Get a Gemini API key (and a Groq key as backup) per `TRD.md` §4. Put both in `.env`.
- Write and run a throwaway script that makes exactly one real call to the LLM and prints the
  response — nothing fancy, just proof the key and SDK work.
- Write and run a throwaway script that creates a SQLite file, writes one row, reads it back.

**Exit criteria (all must be true before moving on):**
- [x] The one-off LLM call script runs and prints a real response, no errors.
- [x] The one-off SQLite script successfully writes and reads a row.
- [x] `.env` exists, has real keys, and `git status` does NOT show it as staged.

**STOP here. Confirm all three before starting Phase 1.**

---

### Phase 1 — Schema + synthetic dataset (Tue Sep 1 afternoon → Wed Sep 2 morning)

**Tasks:**
- Write `data/schema.sql` exactly matching `BACKEND_SCHEMA.md` §1 (all 7 tables).
- Write `src/models.py` — typed dataclasses for each table's rows.
- Write `src/db.py` — connection handling, and one function per table for insert/read.
- Write `data/seed/generate_dataset.py` implementing the 8 archetypes from `BACKEND_SCHEMA.md` §5,
  fixed random seed, ~60 total records, 20 tagged as held-out.
- Run it. Load the resulting `data/mandate_trail.db`.

**Exit criteria:**
- [x] Running the seed script twice in a row produces byte-identical row counts and identical
      sampled records (proves the seed is actually fixed).
- [x] Querying the DB directly (e.g. via the `sqlite3` CLI) shows the expected ~60 disputes, with
      roughly even distribution across the 8 archetypes.
- [x] Hand-check at least 3 records across different archetypes against `BACKEND_SCHEMA.md` §5's
      table — do they actually match what that archetype is supposed to look like?

**STOP here. Confirm before starting Phase 2.**

---

### Phase 2 — Rule engine (Wed Sep 2)

**Tasks:**
- Write `src/rules_engine.py`: the 5 checks from `BACKEND_SCHEMA.md` §3, each as its own small
  function, plus a function that combines them into a confidence score.
- Write `tests/test_rules_engine.py`: at least one test per individual check (both pass and fail
  cases), plus a handful of full-record tests using known archetypes with known expected scores.
- Run the rule engine over all 60 synthetic records (no LLM involved yet) and print each dispute's
  confidence score and which checks failed.

**Exit criteria:**
- [ ] `pytest tests/test_rules_engine.py` passes, no skipped tests.
- [ ] Running the rule engine over the full 60-record set produces a score for every single record
      with zero crashes.
- [ ] Spot-check: archetype 1 (clean legitimate) scores high, archetype 2-4 and 6-7 score lower —
      does the output actually match intuition for each archetype?

**STOP here. Confirm before starting Phase 3.**

---

### Phase 3 — Evidence writer, grounding check, decision orchestration (Wed Sep 2 evening → Thu Sep 3)

This phase includes deliberately manufacturing the project's failure-recovery story — do this on
purpose, don't wait to stumble into it.

**Tasks:**
- Write `src/evidence_writer.py`: given a high-confidence record's structured data, call the LLM
  to draft a narrative. Implement the grounding check (per `AI_RULES.md` §2) — at minimum, verify
  every number, date, and named entity in the generated text also appears in the structured input
  it was given.
- Write `src/decision.py`: orchestrates `rules_engine` → branch → `evidence_writer` (if
  high-confidence) → records the final `recommended_action` via `db.py`, and writes an
  `audit_log` entry at every step.
- **Deliberately** feed the evidence writer a sparse or conflicting record (archetype 6 or 7 from
  `BACKEND_SCHEMA.md` §5) and observe what happens. If the LLM invents a plausible-but-false claim
  (e.g. references a device fingerprint that doesn't exist in agent transactions), confirm the
  grounding check catches it and forces escalation. **Write down exactly what you saw** — this is
  the real failure-recovery story for the pitch, not a hypothetical one.
- Run `decision.py` over the full 60-record set end to end.

**Exit criteria:**
- [ ] `pytest tests/test_evidence_writer.py` passes, including a test that a deliberately-bad
      narrative gets rejected by the grounding check.
- [ ] For a high-confidence sample: a narrative is generated and passes grounding.
- [ ] For a low-confidence sample: no narrative is generated at all, correctly escalated.
- [ ] The deliberate failure case is documented — what broke, what the grounding check did about
      it — in a few sentences, saved somewhere you'll find it again for the pitch video.
- [ ] Full 60-record run completes with zero crashes.

**STOP here. Confirm before starting Phase 4.**

---

### Phase 4 — Metrics + dashboard (Thu Sep 3 afternoon → Fri Sep 4)

**Tasks:**
- Write `src/metrics.py`: precision, recall, false-positive cost (per `BACKEND_SCHEMA.md` §4),
  computed only against the 20 held-out records, reading `disputes.ground_truth_label` — the only
  module allowed to.
- Write `app.py`: the 3 screens from `APP_FLOW.md` (Queue, Detail, Metrics), Streamlit-native
  components only, per `UI_UX.md`.
- Run `streamlit run app.py` and click through all 3 screens end to end.

**Exit criteria:**
- [ ] `pytest tests/test_metrics.py` passes.
- [ ] Dashboard runs locally with zero errors; all 3 screens load and show real data.
- [ ] The Metrics screen's numbers match a hand-count you do separately (pick 5 held-out records,
      manually check the system's decision against `ground_truth_label`, confirm the dashboard
      agrees).

**STOP here. Confirm before starting Phase 5.**

---

### Phase 5 — Polish + audit trail completeness (Fri Sep 4)

**Tasks:**
- Pick 2-3 disputes at random in the dashboard and manually trace every field shown back to
  `audit_log` — is the trail actually complete, or are there gaps?
- Re-read `README.md`'s quickstart from a clean perspective (or better: have someone else, or a
  fresh AI session with no prior context, try to follow it) — does it actually work end to end?
- Clean up any dead code, unused imports, leftover print-debugging.
- Fix `README.md`'s "Current status" line to reflect reality.

**Exit criteria:**
- [ ] Every value shown in the Detail screen can be traced to a specific `audit_log` row.
- [ ] A completely clean clone + the README's quickstart commands work with no undocumented steps.

**STOP here. Confirm before starting Phase 6.**

---

### Phase 6 — Pitch video + submit (Fri Sep 4 evening → Sat Sep 5 morning)

**Tasks:**
- Record the 5-minute pitch: the problem (why agent-initiated disputes are different — `PRD.md`
  §3), a live walkthrough of the 3 screens, the metrics screen's real numbers, and — explicitly —
  the Phase 3 failure-recovery story (what broke, what you did about it). This last part is one of
  the four things they said they grade; don't leave it as an afterthought at minute 4:50.
- Push the final repo, confirm it's public, confirm `.env` never got committed at any point in
  history (check `git log -- .env`, not just the current state).
- Fill out the application form (`PRD.md` §1's pitch line works well for "what it solves").
- Submit — aim for Friday night or early Saturday, not the last hour of Sep 5.

**Exit criteria:**
- [ ] Video recorded, uploaded (unlisted is fine), under or around 5 minutes.
- [ ] Repo is public, `.env` was never committed, README quickstart verified one more time.
- [ ] Form submitted.

**Done.**
