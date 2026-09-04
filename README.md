# Mandate Trail

Evidence and dispute-response engine for **agent-initiated transactions** — chargeback defense
built for the case where an AI agent made the purchase, not a human clicking checkout.

Built for the Razorpay AI Buildathon, Track 02 (AI Risk Manager).

## Why this exists

Razorpay's own live pilot lets Claude complete purchases on Zomato, Swiggy, and Zepto through
UPI Reserve Pay, on a user's consent. When one of those transactions gets disputed, the evidence
a merchant normally uses to fight back — device fingerprint, click trail, session behavior —
doesn't exist in the usual form, because there was no human clicking. What exists instead is a
consent mandate, an agent's action log, and a fulfillment record. Nothing off-the-shelf assembles
those into a defensible case yet. This does.

Full reasoning, market check, and why this beats the obvious "build a chargeback bot" idea: see
`PRD.md`.

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
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then paste your free Gemini or Groq key into .env
python data/seed/generate_dataset.py   # builds data/mandate_trail.db from scratch
python run_pipeline.py             # runs the full decision pipeline over all 60 records
pytest                             # all tests should pass before you run the app
streamlit run app.py               # opens the dashboard at localhost:8501
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

