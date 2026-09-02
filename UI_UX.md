# UI_UX — how it looks and feels

## 1. The one-line philosophy

This should look like an internal tool a fraud-ops analyst actually uses, not a startup landing
page. That restraint *is* the aesthetic that signals trustworthiness to a judge — a polished
marketing-style UI on a risk tool reads as compensating for something. Resist the urge to make it
"look impressive." Legible and plain reads as more credible here, not less.

## 2. Hard rule: Streamlit-native components only

No custom CSS injection (`st.markdown(..., unsafe_allow_html=True)` for styling), no custom
fonts, no custom component libraries. Use `st.dataframe`, `st.metric`, `st.expander`, `st.tabs`,
`st.selectbox`, `st.columns` for layout — Streamlit's defaults are already clean, and every custom
CSS injection is one more place an AI coding tool can quietly break the layout without anyone
noticing until the demo. This isn't a taste preference, it's a risk-reduction rule, same spirit as
`AI_RULES.md`.

## 3. Status color semantics — consistent everywhere they appear

Since there's no custom CSS, convey status with a plain-text prefix, not a colored badge
component:

| Meaning | Prefix | Where it appears |
|---|---|---|
| High confidence / recommend contest | `🟢 Contest` | Queue table, Detail header |
| Low confidence / needs a human | `🟡 Escalate` | Queue table, Detail header |
| Dispute closed / not applicable | `⚪ Closed` / `⚪ Accepted` | Queue table, Detail header |
| Grounding check passed | `✓ Grounded` | Detail screen, evidence narrative section |
| Grounding check failed / rejected | `✗ Rejected — escalated instead` | Detail screen |

Keep this table itself as the single source of truth — if a new status is added, add it here
first, then use it in `app.py`, not the other way around.

## 4. Numbers over color, always

Every confidence score, precision, and recall value is shown as an actual number
(`0.83`, not just a green bar) next to whatever color or icon represents it. A technical judge
trusts a number they can double-check against the held-out table more than a color they have to
take on faith. This is the same instinct as `AI_RULES.md` §10 — legibility of evidence beats
polish, everywhere in this project.

## 5. Layout

- `st.columns` for side-by-side sections (e.g. Mandate / Agent Log / Fulfillment on the Detail
  screen) where it aids scanning — don't force everything into a single vertical scroll if a
  2- or 3-column layout genuinely reads faster.
- The raw audit log (`st.expander`, per `APP_FLOW.md`) stays collapsed by default everywhere. It
  should be present on every dispute, one click away, never hidden behind extra navigation.
- No hero section, no logo, no tagline banner. A one-line `st.title("Mandate Trail")` at the very
  top of the app is enough branding.

## 6. Explicit anti-goals

- No animations, no loading spinners beyond Streamlit's own defaults.
- No mobile responsiveness work — this is reviewed on a laptop, in a panel room or a screen
  recording. Time spent here is time not spent on the pipeline that's actually judged.
- No onboarding flow, tooltips, or first-run tutorial. A reviewer opens the Queue screen and
  understands it in five seconds, or the design has failed regardless of how it looks.
