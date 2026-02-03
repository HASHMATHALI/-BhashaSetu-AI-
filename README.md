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

## Repository layout
- **/docs** → hackathon deliverables (requirements, design, PPT content)
- **/app** → Android app source
- **/dataset** → scheme packs, schemas, citations
- **/scripts** → dataset validation + pack building utilities

Start here if you’re a judge:
- [`docs/requirements.md`](docs/requirements.md)
- [`docs/design.md`](docs/design.md)
- [`docs/ppt_content.md`](docs/ppt_content.md)

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

---

## Dataset approach (why it’s separated from the app)
Schemes change frequently, and state variations are common. So we treat the scheme knowledge base as a versioned artifact:
- **dataset packs** can be updated without shipping a new app build
- packs are validated against a schema and include metadata + checksums
- the app shows “last updated” so users and field workers can trust freshness

See:
- [`dataset/packs/`](dataset/packs/)
- [`dataset/schema/`](dataset/schema/)
- [`dataset/sources/citations.md`](dataset/sources/citations.md)

---

## Getting started (for developers)
### 1) App
- Open `app/android/` in Android Studio
- Build and run on a budget Android device if possible (realistic performance)

Suggested test checklist:
- airplane mode tests (offline flows)
- low-RAM device behavior (search speed + stability)
- speech failure fallback (clarify / switch to browse)

### 2) Dataset (local)
We store schemes in a structured format and export to SQLite for fast offline lookup.

Typical workflow:
1. Put/modify scheme JSON inside `dataset/packs/sample_pack_v0.1/`
2. Run validation (schema + sanity checks)
3. Export SQLite database for the app
4. Generate checksum for the pack

Scripts live in `/scripts` (details in `scripts/README.md`).

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

Copy
Small add-on files (optional but useful)
If you want the repo to look “complete” on GitHub, add these lightw
