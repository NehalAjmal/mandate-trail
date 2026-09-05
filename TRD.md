# TRD — Technical Requirements

Every choice below optimizes for one thing: lowest chance of something breaking in a 5-day solo
build, at $0 cost. Not for looking impressive. If you want to swap something, update this file
first so `ARCHITECTURE.md` stays in sync with it.

## 1. Stack at a glance

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.9+ (built and tested on 3.9.6 — note this is past end-of-life; 3.11+ recommended for a fresh start) | One language, no build step, huge ecosystem for data + rules + LLM calls. Removes an entire class of "frontend can't talk to backend" bugs by not having a separate frontend. |
| App / UI | Streamlit | The dashboard *is* the app — no separate API layer, no CORS, no JS build tooling. Renders tables/metrics cleanly with zero custom CSS. |
| Database | SQLite (Python's built-in `sqlite3`) | Zero setup, zero external account, zero cost, trivially portable. Entirely appropriate at ~60-row scale — a hosted DB here would be pure risk for no benefit. |
| LLM | Google Gemini API (Flash / Flash-Lite tier) — primary. Groq (Llama/GPT-OSS class models) — fallback. | Both have genuine no-credit-card free tiers today. Narrative generation runs at temperature=0.0 for reproducibility and to minimize hallucination variance. Claude API does **not** have a free tier (see §2) — a small unpublished signup credit only, then paid per token, so it's excluded by the "totally free" requirement. |
| Testing | `pytest` | Standard, free, no config needed to get started. |
| Dependency mgmt | `venv` + `requirements.txt` | Simplest, most universal option — skip Poetry/Pipenv, they add friction for no benefit at this scale. |
| Version control | Git + GitHub | Free, and required anyway — the buildathon asks for a public repo. |
| Hosting | None required. Optional: Streamlit Community Cloud (free) if you want a live link later. | The brief asks for a repo + pitch video + architecture, not a live URL. Every hour spent on deployment is an hour not spent on the pipeline that's actually judged. |

## 2. The free-tier facts, verified (don't take these on faith either — re-check before you build)

**Claude API:** No free tier. New accounts get a small, unpublished one-time credit; after that,
every call is billed per token. Confirmed against multiple independent 2026 pricing trackers.
Excluded from this build for that reason — not a knock on it, just doesn't fit "totally free."

**Google Gemini API (via Google AI Studio):** Real, ongoing, no-credit-card free tier on Flash and
Flash-Lite class models. Rate limits are enforced per Google Cloud project across three
dimensions — requests/minute, tokens/minute, requests/day — and the exact numbers have shifted a
few times through 2026 as Google adjusted quotas. **Do not hardcode a specific model name or
number into your code as gospel** — check `https://ai.google.dev/gemini-api/docs/pricing` the day
you set this up and use whichever Flash/Flash-Lite model is currently marked free. As of the most
recent data found, expect roughly 10-15 requests/minute and low-hundreds-to-low-thousands of
requests/day on the free tier — comfortably enough for this project (see §3 arithmetic). The Pro
tier is much more restricted (as low as ~50 requests/day) — don't use Pro models for this build.
One privacy note: free-tier prompts/responses may be used by Google to improve their models. Since
every record in this project is synthetic, that's a non-issue here — just don't reuse this same
free-tier setup later for anything with real user data.

**Groq API:** Also a real, no-credit-card free tier, hosting open models (Llama 3.3 70B, GPT-OSS
120B, Llama 3.1 8B, Qwen3, and others) behind an OpenAI-compatible endpoint. Typical published
limits: ~30 requests/minute, ~6,000 tokens/minute, and a daily cap in the hundreds to low
thousands depending on model — again, verify current numbers at `console.groq.com` before relying
on a specific figure. Its OpenAI-compatible API shape means the same client code pattern (the
`openai` Python package pointed at Groq's base URL) works with minimal changes if you swap
providers.

**Streamlit Community Cloud:** Still free in 2026 if you want a hosted link. ~1GB RAM per app,
apps sleep after ~12 hours of no traffic, requires a public GitHub repo (which you'll already
have). Not required for this build — mentioned only as a zero-cost option if you want one later.

**GitHub Student Developer Pack:** Optional, not required for this build (we don't need any of its
cloud credits since nothing here needs hosting). Worth claiming anyway since it's free and you're
a student, but verification can take time — don't let it block the build. Note as of mid-2026,
new Copilot Pro sign-ups through the pack were reported paused; don't plan around getting it.

## 3. Does the free tier actually cover this project? The arithmetic.

- 60 synthetic disputes total.
- Roughly half (the archetypes designed to be clean/high-confidence — see `BACKEND_SCHEMA.md` §5)
  actually trigger an LLM call for narrative generation. Call it **35-40 LLM calls per full
  pipeline run.**
- Expect to re-run the full pipeline maybe 10-15 times over 5 days while debugging (that's
  generous).
- Total: **roughly 400-600 LLM calls across the entire build**, spread over 5 days, naturally
  paced by the fact you're not running them all in the same 60 seconds.
- Against a free-tier floor of even the most conservative number found in research (~100
  requests/day on a restricted model), this fits with room to spare — and Flash/Flash-Lite specifically
  report limits several times higher than that floor. You will not hit a paywall building this.

If you do somehow hit a rate limit mid-session: that's what the Groq fallback is for. Don't burn
time debugging a 429 — swap the provider and keep moving (the code is structured to make
this a one-line change, not a rewrite).

## 4. Accounts you actually need to create

1. GitHub account (you need this anyway for the public repo requirement).
2. Google AI Studio account, for a Gemini API key — no credit card. `https://aistudio.google.com`
3. Groq account, for a fallback API key — no credit card. `https://console.groq.com`

That's it. No Razorpay account, no AWS/GCP/Azure account, no database provider account.

## 5. `requirements.txt` (starting point — add to this only with a one-line reason)

```
streamlit
pytest
python-dotenv
google-generativeai
openai          # used for Groq calls via its OpenAI-compatible endpoint, not for OpenAI itself
pandas
```

## 6. `.env.example`

```
# Copy this file to .env and fill in real values. .env is gitignored — never commit real keys.
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
LLM_PROVIDER=gemini   # or "groq" — controls which one src/evidence_writer.py calls
```

## 7. What we're deliberately NOT using, and why

- **No Docker.** Adds a real learning-curve tax for zero benefit at this scale — `venv` is enough.
- **No cloud database (Supabase/Postgres/etc.).** SQLite is free, zero-setup, and this is a
  60-row dataset — a hosted DB is pure added risk here.
- **No separate frontend framework (React/Next.js/etc.).** Streamlit removes an entire category
  of integration bugs (API contracts, CORS, build tooling) that cost time without improving the
  thing judges are actually scoring.
- **No real Razorpay API keys or live account.** Not needed — the whole point of the synthetic
  dataset is to avoid depending on Razorpay's live systems (which can't even generate test
  disputes programmatically — see `BACKEND_SCHEMA.md` §1).
- **No authentication/login system.** Single implicit user, no accounts needed for a judged demo.
