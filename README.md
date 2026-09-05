<h1 align="center">Mandate Trail</h1>

<p align="center">
  <strong>Evidence and dispute-response engine for agent-initiated transactions.</strong><br>
  Chargeback defense built for the case where an AI agent made the purchase, not a human.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white" alt="Google Gemini">
</p>

<p align="center">
  <em>Built for the Razorpay AI Buildathon, Track 02 (AI Risk Manager).</em>
</p>

---

## Why this exists

Razorpay's own live pilot lets Claude complete purchases on Zomato, Swiggy, and Zepto through
UPI Reserve Pay, on a user's consent. When one of those transactions gets disputed, the evidence
a merchant normally uses to fight back — device fingerprint, click trail, session behavior —
doesn't exist in the usual form, because there was no human clicking. What exists instead is a
consent mandate, an agent's action log, and a fulfillment record. Nothing off-the-shelf assembles
those into a defensible case yet. This does.

Full reasoning, market check, and why this beats the obvious "build a chargeback bot" idea: see
`PRD.md`.

## Project Summary

If you don't have time to read the full documentation suite below, here is how the system works at a high level.

### 1. The Architecture
Mandate Trail uses a strict **bipartite architecture** designed for risk and compliance. It explicitly forbids LLMs from making final risk decisions.
Instead, it uses a **deterministic, zero-AI rules engine** to mathematically evaluate the confidence of a dispute based on structured inputs. Only if a dispute achieves 100% confidence (all 6 strict checks pass) is an LLM invoked to programmatically draft the merchant defense letter.

### 2. How it works
1. **Ingest & Link:** The engine pulls together the initial consent **mandate**, the structured **agent action log**, and the **fulfillment record**.
2. **Rule Engine:** It runs 6 deterministic checks (e.g., verifying the order amount is within the mandate's cap, matching merchant IDs, catching duplicate transactions).
3. **LLM Generation:** For 6/6 confidence cases, an LLM drafts an evidence explanation letter based *only* on the structured facts.
4. **Grounding Check:** A secondary, purely deterministic regex-based "grounding check" scans the generated text. If the LLM hallucinated any human interaction (e.g., mentioning "IP address", "clicked", or "browser"), the check fails and the case is safely escalated to a human.
5. **Audit Trail:** Every single input, check, generation, and decision is written to an append-only `audit_log` (SQLite).

### 3. Technical Obstacles & Failure Recovery
Generative models (both Gemini and Groq 120B) would occasionally hallucinate standard chargeback evidence that didn't exist (like inventing an IP address for an AI agent). We initially tried wrapping the LLM in a "retry loop" to brute-force a passing grounding check, but realized this masked the underlying unreliability and violated strict risk engineering principles. 

**The fix:** We removed the retry loop entirely, enforced `temperature=0.0` for deterministic outputs, and used a strict negative-constraint prompt. On the rare occasion a hallucination still occurs, the deterministic grounding check catches it and safely escalates the dispute, proving the safety net functions flawlessly on real failures.

### 4. Metrics
Evaluated on a strictly held-out set of 20 synthetic records:
- **Precision:** 100% (Zero valid transactions were incorrectly escalated)
- **Recall:** 100% (Every valid, defensible transaction was successfully identified)
- **False-Positive Cost:** $0

## Read these in order

1. **`PRD.md`** — what this is, and just as important, what it is *not*.
2. **`TRD.md`** — the exact stack, every account you need to create, and why each choice was made.
3. **`BACKEND_SCHEMA.md`** — the data layer. Every table, every field, the synthetic dataset design.
4. **`ARCHITECTURE.md`** — folder structure, module boundaries, where new code is allowed to go.
5. **`APP_FLOW.md`** — every screen, every state, every button.
6. **`UI_UX.md`** — how it should look and feel.
7. **`PLAN.md`** — the day-by-day, phase-gated build order this was actually built with.

## Quickstart

```bash
git clone <your-repo-url> mandate-trail
cd mandate-trail
python3 -m venv .venv
source .venv/bin/activate               # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                    # then paste your free Gemini (recommended) or Groq key into .env
python data/seed/generate_dataset.py    # builds data/mandate_trail.db from scratch
python run_pipeline.py                  # runs the full decision pipeline over all 60 records
pytest                                  # all tests should pass before you run the app
streamlit run app.py                    # opens the dashboard at localhost:8502
```

## Repo layout

```
mandate-trail/
├── README.md, PRD.md, ARCHITECTURE.md, PLAN.md,
│   TRD.md, APP_FLOW.md, UI_UX.md, BACKEND_SCHEMA.md
├── .streamlit/
│   └── config.toml     ← theme only, no custom CSS
├── data/                schema.sql, the synthetic data generator, the generated .db file
├── src/                 rules_engine.py, evidence_writer.py, decision.py, metrics.py, db.py, models.py
├── app.py               the Streamlit dashboard, the only UI code in the repo
├── run_pipeline.py      runs the full decision pipeline end to end over all 60 records
├── verify_app.py        automated check of all 3 dashboard screens via Streamlit's AppTest
├── tests/
├── requirements.txt
├── .env.example
└── .gitignore
```

