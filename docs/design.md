# BhashaSetu AI — design.md

## 1. System Overview
BhashaSetu AI is an offline-first Android application that provides multilingual voice-based guidance for government welfare schemes. It works primarily from a **local knowledge base** (scheme dataset) and uses an **on-device speech pipeline** to avoid dependency on internet.

Core idea:
- Store schemes + eligibility rules locally
- Ask short guided questions
- Match schemes using a lightweight rule + retrieval layer
- Speak back results clearly in the user’s language
- Sync dataset updates when connectivity appears

---

## 2. High-Level Architecture (Explanation)
The system is divided into 5 main layers:

1. **UI + Voice UX Layer**
   - microphone input, language selection, large-button navigation
   - voice prompts and “repeat” controls

2. **Speech Layer (On-device)**
   - Speech-to-Text (STT): converts spoken query to text
   - Text-to-Speech (TTS): reads answers in local language
   - Lightweight language detection (or user-selected language override)

3. **Scheme Intelligence Layer**
   - Query understanding (intent: discover scheme / eligibility / documents / where to apply)
   - Retrieval from local dataset (keyword + category + tags)
   - Eligibility evaluator (rule-based scoring based on questionnaire answers)
   - Response composer (simple explainable output)

4. **Local Data Layer**
   - scheme dataset stored in local DB (SQLite)
   - offline search index for fast lookup
   - local history (optional)

5. **Sync + Update Layer**
   - dataset pack downloader (only when online)
   - pack verification (checksum/signature)
   - atomic DB refresh + rollback
   - optional lightweight analytics counters (non-personal, opt-in)

---

## 3. Component-wise Design

### 3.1 Mobile App UI Module
Responsibilities:
- Provide “Press to speak” interaction
- Display scheme cards with:
  - scheme name
  - benefits summary
  - eligibility highlights
  - documents list
  - where to apply
- Support low literacy:
  - icons + minimal text
  - voice playback button per section

Key screens:
- Language selection / change
- Home (Speak / Browse categories)
- Eligibility wizard
- Scheme details
- Checklist export/share

---

### 3.2 Speech Module (Offline)
**STT (Speech-to-Text)**
- On-device recognition for supported languages.
- Confidence score used to trigger clarifying questions.

**TTS (Text-to-Speech)**
- Uses offline voices where available.
- “Slow mode” option for clarity.

Fallbacks:
- If STT fails repeatedly, switch to:
  - simple tap-based category browsing
  - short multiple-choice questions

---

### 3.3 Scheme Dataset Module
Storage format:
- SQLite tables with normalized scheme fields + tags.
- Optional FTS (full-text search) index for scheme name/benefits/keywords.

Proposed core fields:
- scheme_id (unique)
- scheme_name
- category
- state_applicability (ALL / state list)
- benefits_text
- eligibility_rules (structured JSON)
- required_documents (list)
- application_channels (portal/CSC/office)
- official_link
- last_updated

Reason:
- SQLite is stable, fast, and works well offline on Android.

---

### 3.4 Retrieval + Matching Engine
Two-stage approach (kept simple for reliability):

**Stage A: Candidate Retrieval**
- From user query text:
  - keyword match against name/benefits/tags
  - category boosting (health/agri/education/etc.)
- Output: top N candidate schemes.

**Stage B: Eligibility Scoring**
- Use questionnaire answers.
- Evaluate structured eligibility rules:
  - hard filters (e.g., age must be ≥ 60)
  - soft hints (e.g., “priority for women”)
- Output: ranked list with “why it matches” explanation.

Explainability:
- The response composer attaches 2–3 short reasons:
  - “You said you are a farmer”
  - “Age group matches”
  - “Available in your state”

This makes field validation easier and avoids black-box behavior.

---

### 3.5 Eligibility Wizard Module
Design:
- Short flow: 6–10 questions max.
- Uses voice prompts + quick answer chips.
- Stores answers locally in a temporary session object.

Important choice:
- We avoid collecting sensitive identifiers (Aadhaar/bank numbers).
- Only coarse ranges (income bracket) are asked.

---

### 3.6 Checklist Export Module
Outputs:
- Simple checklist in local language + optional bilingual (local + English) for CSC help.
- Save locally and share via WhatsApp/Bluetooth when needed.

This is practical because many beneficiaries still depend on a local operator for final submission.

---

### 3.7 Sync + Update Module (Offline-first Strategy)
Update design:
- Dataset distributed as versioned “packs” (compressed JSON/SQLite dump).
- App checks for updates only when:
  - user allows updates, AND
  - connectivity is available, AND
  - battery is above a threshold (configurable)

Safety:
- Download pack -> verify checksum/signature -> import to new DB -> swap pointer -> delete old DB after success.
- Rollback if import fails.

---

## 4. Data Flow (End-to-End)
1. User presses mic and asks question in their language.
2. STT converts speech to text + provides confidence.
3. Intent is detected:
   - “find schemes” OR “check eligibility” OR “documents needed” OR “where to apply”
4. Retrieval engine fetches candidate schemes from SQLite/FTS.
5. If eligibility is requested and user profile is missing:
   - Eligibility wizard runs and captures coarse details.
6. Matching engine ranks schemes and generates reasons + checklist.
7. Response is shown in UI and spoken via TTS.
8. If online, user can open the official link; otherwise it remains available for later.

---

## 5. Model/Method Selection Reasoning (Practical Student Choice)
We kept the intelligence layer intentionally lightweight:
- On-device STT/TTS because connectivity is unreliable.
- Retrieval + rule-based scoring because:
  - welfare eligibility conditions are mostly explicit
  - rules are auditable and easy to debug during field tests
  - it avoids unpredictable answers in government-sensitive use cases

Where we can extend later:
- Add semantic search embeddings for better discovery (optional, if device allows).
- Add summarization templates per scheme for cleaner speech output.

---

## 6. Offline-First Design Strategy
Offline-first decisions:
- All critical information stored locally: scheme summaries, eligibility rules, documents.
- No dependence on cloud calls for core flow.
- Background sync is opportunistic and safe (atomic update + rollback).
- UI always provides a “Browse offline categories” path even if voice fails.

---

## 7. Security & Privacy Considerations
Privacy:
- No Aadhaar/bank/account numbers needed.
- User answers stored locally; history can be cleared.
- Optional analytics only as aggregate counters, opt-in.

Security:
- Dataset packs verified before import (checksum/signature).
- Official links opened as read-only guidance (no credential storage).
- Prevent “tampered dataset” issue by refusing unsigned packs.

Threats considered:
- Misinformation from outdated data -> handled via visible “last updated”
- Device sharing -> provide “guest mode” and quick clear-history option

---

## 8. Scalability Approach
Scalability here means scaling across:
- languages
- states
- number of schemes

Approach:
- Modular language packs (STT/TTS + UI strings)
- Dataset packs per state + national schemes
- Incremental updates (diff packs) to reduce download size
- Indexing (FTS) for fast search even with large datasets

Deployment model:
- Start with 1–2 states in pilot, then expand state-by-state as dataset quality improves
