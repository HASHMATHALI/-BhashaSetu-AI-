# BhashaSetu AI
**Offline-first multilingual voice assistant for accessing government welfare schemes.**

BhashaSetu AI is a practical Android-first system built for rural and low-connectivity regions. It helps users discover relevant government welfare schemes, understand benefits and eligibility, and generate a document checklist using a voice-first interface in local languages.

This project is designed for deployments where internet is unreliable, literacy levels vary, and citizens often depend on intermediaries for basic scheme guidance.

---

## What problem are we solving?
Even when schemes exist, many eligible citizens don’t access them because:
- scheme details are scattered and hard to navigate
- portals are text-heavy and not friendly for local languages
- eligibility conditions are confusing and vary by scheme/state
- internet and device constraints break “online-only” approaches
- misinformation spreads through intermediaries

BhashaSetu AI focuses on **guided scheme discovery + eligibility help + document readiness**, without requiring constant connectivity.

---

## What the system does (MVP scope)
- **Voice query in local language** (speech-to-text)
- **Voice response in the same language** (text-to-speech)
- **Offline scheme search** using a local scheme dataset
- **Eligibility wizard** (short questionnaire, 6–10 questions)
- **Explainable matching** (“why this scheme fits you” in 2–3 reasons)
- **Document checklist generator** (scheme-wise)
- **Optional online handoff**: opens official links when connectivity is available

**Important:** The app does **not** submit applications automatically. It prepares users and guides them to official channels (portal/CSC/office).

---


---

## Architecture summary (high level)
BhashaSetu AI is split into:
- **UI + Voice UX Layer**: mic-first flows + low-literacy screens
- **Speech Layer**: on-device STT and TTS for selected languages
- **Scheme Intelligence Layer**:
  - intent detection (discover / eligibility / documents / where-to-apply)
  - retrieval from offline DB (SQLite + optional FTS)
  - eligibility scoring using structured rules
  - response composer with short explainable reasons
- **Local Data Layer**: scheme DB + optional local history
- **Sync Layer**: opportunistic dataset pack updates with integrity checks

More details: [`docs/design.md`](docs/design.md)

---

## Offline-first design (how it behaves without internet)
When offline, the user can still:
- search/browse schemes
- run eligibility wizard
- get matched schemes + reasons
- generate a document checklist

When online, the app can:
- fetch newer dataset packs
- verify checksum/signature
- atomically swap the DB (rollback on failure)
- open official scheme links


## What is built so far

This repository holds the design and the **offline matching engine**. The
Android app, speech layer and translation are not built yet.

| Part | Status | Where |
|---|---|---|
| System design | Written | [`docs/design.md`](docs/design.md) |
| Scheme pack format, validator, SQLite + FTS5 export, SHA-256 checksum (design 3.3, 3.7) | Working | `engine/bhashasetu.py` |
| Two-stage matching with 2-3 reasons per match (design 3.4) | Working | `engine/bhashasetu.py` |
| Eligibility answers: coarse, no identifiers (design 3.5) | Working | `engine/bhashasetu.py` |
| Document checklist, de-duplicated across schemes (design 3.6) | Working | `engine/bhashasetu.py` |
| Real scheme data | **Not started** | `dataset/packs/` |
| Android app, on-device speech, translation | Not started | |

**The sample pack is fictional.** Every scheme in
`dataset/packs/sample_pack_v0.1` is a placeholder named "Sample ...", with
`example.gov.in` links, so the engine can be tested without inventing facts
about real schemes. A real pack must take each scheme's rules from its official
notification and record that source in the `source` field.

### Try it

Python 3.9+ and nothing else.

```bash
python engine/bhashasetu.py validate dataset/packs/sample_pack_v0.1
```

```bash
python engine/bhashasetu.py export dataset/packs/sample_pack_v0.1 schemes.sqlite
```

```bash
python engine/bhashasetu.py match schemes.sqlite --query "pension for old age" --age 64 --state KA --income below_1l --gender female --checklist
```

```text
Sample Old-Age Pension  [Likely eligible]
  - Your age group fits
  - Your income is within the limit
  - You are in a priority group
Sample Widow Support Pension  [Check: marital_status]
```

How it decides:

- **Hard rules** (age range, state, occupation, income bracket, gender, social
  category, marital status, disability) exclude a scheme when an answer fails them.
- **A missing answer never excludes.** The scheme is shown as "Check" with the
  question still to ask, so the wizard knows what to ask next.
- **Soft rules** (priority groups) only move a scheme up the list.
- The checklist covers only the schemes marked "Likely eligible".

### Tests

```bash
pip install pytest
```

```bash
pytest
```

13 tests cover pack validation, the checksum, retrieval, every rule type,
"ask instead of guess", the checklist and the command line.

---

## Security & privacy notes
- No Aadhaar number, bank account number, or sensitive identifiers are required for recommendations.
- Eligibility answers are stored locally by default and can be cleared.
- Dataset packs are verified (checksum/signature) before import to avoid tampering.
- The app only links out to official portals; it does not store user credentials.

---

## Success metrics (what we measure in field testing)
- users can find at least one relevant scheme quickly (time-to-first-match)
- eligibility wizard completion rate in offline mode
- checklist usefulness (reduced missing-document cases)
- update success rate for dataset packs when connectivity is available
- crash-free sessions during pilot use

---

## Roadmap (realistic next steps)
- Expand languages and tune voice UX for noisy rural environments
- Add more state-specific schemes with proper citations
- Improve search quality (optional semantic layer on devices that can handle it)
- Add nearest CSC/office discovery (if location permission is allowed and useful)
- Field testing with VLEs/ASHA workers and iterate question flow

---

## Team
THIRD-year engineering student team — built for the AI For Bharat hackathon.
