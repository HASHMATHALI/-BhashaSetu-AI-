# BhashaSetu AI — requirements.md

## 1. Project Overview
**BhashaSetu AI** is an offline-first multilingual voice assistant that helps rural citizens discover and understand government welfare schemes, check eligibility, and prepare a basic application checklist using simple voice-based interaction. The system is designed for low-connectivity areas and supports local languages with speech input/output.

**Tagline:** Offline-first multilingual voice assistant for accessing government welfare schemes.

The goal is not to “replace” existing portals, but to make them accessible through voice + local language + guided flow.

---

## 2. Problem Statement
Many welfare schemes exist, but rural citizens often fail to access them due to:
- lack of awareness of scheme names/benefits
- language barriers (English/Hindi-only interfaces)
- difficulty reading long documents or portals
- poor internet connectivity and low-end devices
- dependency on intermediaries (leading to misinformation or extra costs)

A citizen needs a simple way to ask: *“What schemes can help me?”* and get a reliable, step-by-step response in their own language, even without internet.

---

## 3. Objectives
1. Provide voice-first access to scheme information in multiple Indian languages.
2. Enable offline usage for key flows: scheme discovery, basic eligibility check, and document checklist.
3. Reduce misinformation by using curated government scheme datasets with citations/traceability.
4. Keep user data minimal and private by design.
5. Make the system deployable on low-cost Android devices used in rural areas.

---

## 4. Target Users
Primary:
- Rural citizens (low literacy / semi-literate users)
- Elderly citizens who struggle with apps/forms
- Women in SHGs needing scheme guidance

Secondary:
- Village Level Entrepreneurs (VLEs) / CSC operators
- ASHA/Anganwadi workers helping beneficiaries
- Panchayat office assistants

---

## 5. Functional Requirements

### FR-1: Multilingual Voice Interaction
- The system shall accept user queries via microphone (speech-to-text).
- The system shall respond in the same language as the user (text-to-speech).
- The system shall support at least **3 languages** in MVP (example: Hindi, Marathi, Tamil) and be extendable.

### FR-2: Offline-First Operation
- The system shall function without internet for:
  - scheme browsing/search
  - FAQ-style questions answered from the local dataset
  - eligibility Q&A flow for common schemes
  - generating a document checklist
- The system shall queue sync tasks (dataset updates, telemetry if enabled) and execute only when connectivity is available.

### FR-3: Scheme Dataset Access (Local Knowledge Base)
- The system shall store a local dataset of schemes with fields:
  - scheme name
  - department / category (health, education, agriculture, women welfare, pensions)
  - benefits
  - eligibility rules (age/income/occupation/caste/residency where applicable)
  - required documents
  - application channels (portal/CSC/office)
  - last updated date
- The system shall support keyword search and category browsing.
- The system shall show a “source note” indicating dataset origin (e.g., official portal snapshot).

### FR-4: Eligibility Guidance (Questionnaire)
- The system shall guide the user through a short spoken questionnaire:
  - age bracket
  - state/district
  - occupation (farmer/labour/student/etc.)
  - approximate income range
  - gender (optional)
  - specific conditions (disability, widow, senior citizen, etc.) if relevant
- The system shall suggest matching schemes and explain *why* they match using simple reasoning text.

### FR-5: Document Checklist Generator
- The system shall generate a checklist for selected scheme(s), including:
  - ID proof options (Aadhaar/Voter ID)
  - address proof options
  - bank details requirement
  - scheme-specific documents (income certificate, caste certificate, land records, disability certificate, etc.)
- The checklist shall be viewable in-app and playable via voice.
- The checklist shall be savable locally as a small shareable file (text/PDF) for CSC/VLE help.

### FR-6: Assisted Form Preparation (Non-submission)
- The system shall NOT submit applications automatically.
- The system shall help users prepare:
  - what fields will be asked
  - common mistakes
  - where to apply (portal/CSC/office)
- If online, the system shall open the official link inside a browser view.

### FR-7: Local Conversation History (Optional)
- The system shall store recent interactions locally for user convenience.
- The system shall allow clearing history anytime.

### FR-8: Update Mechanism
- When internet is available, the system shall:
  - fetch updated scheme dataset packs
  - verify integrity via checksum/signature
  - replace older dataset safely with rollback on failure

### FR-9: Error Handling and Fallbacks
- If speech recognition confidence is low, the system shall ask a simple clarification question.
- If language detection fails, the system shall prompt for language selection.
- If a scheme is not found, the system shall suggest related categories or ask rephrasing.

---

## 6. Non-Functional Requirements

### NFR-1: Performance
- Offline response time for dataset lookup should be under **2 seconds** on typical budget Android devices.
- Voice interaction should feel continuous (no long blocking screens).

### NFR-2: Reliability
- App should not crash on intermittent connectivity.
- Dataset update process must be atomic (no partial corrupted state).

### NFR-3: Usability
- Interface must work for low literacy:
  - large buttons
  - minimal text
  - voice prompts for next actions
- The app should support “repeat” and “slow speech” modes.

### NFR-4: Privacy
- All eligibility answers remain on-device by default.
- No Aadhaar number, bank account number, or sensitive identifiers are required for recommendations.

### NFR-5: Security
- Dataset packs must be signed/verified.
- Local storage should use OS-level secure storage where possible for settings/history.

### NFR-6: Maintainability
- Scheme dataset should be updateable without full app update.
- Language modules should be plug-in style.

### NFR-7: Accessibility
- Support for users with limited reading ability through voice-first flows.
- Contrast and font size settings.

---

## 7. Assumptions
- Users have access to an Android smartphone (shared devices possible).
- A curated scheme dataset is prepared from official sources and periodically updated.
- MVP focuses on a limited set of high-impact schemes and expands later.
- Speech models for selected languages can run on-device with acceptable accuracy.

---

## 8. Constraints
- Low RAM/CPU devices (budget phones).
- Unreliable or no internet in target regions.
- Schemes change frequently; dataset freshness is a continuous challenge.
- Many schemes have state-specific variations; MVP must clearly indicate state applicability.

---

## 9. Success Metrics
- ≥ 80% of test users can find at least one relevant scheme within 2 minutes.
- ≥ 70% eligibility flow completion rate in offline mode.
- Reduced dependence on intermediaries (self-reported) in pilot villages.
- Dataset update success rate ≥ 95% when connectivity is available.
- App crash-free sessions ≥ 99% during field testing.
