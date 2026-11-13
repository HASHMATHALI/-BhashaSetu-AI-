"""BhashaSetu matching engine: the offline core described in docs/design.md.

Implements, with the Python standard library only:

  3.3  scheme packs: JSON validated against a fixed schema, exported to SQLite
       with an FTS5 index, plus a SHA-256 checksum of the pack
  3.4  two-stage matching: keyword retrieval with category boosting (Stage A),
       then hard-filter and soft-hint eligibility rules (Stage B), each match
       carrying 2-3 plain reasons
  3.5  the answers it needs are coarse (age, state, occupation, income bracket,
       gender, category); no Aadhaar, bank or phone numbers are ever asked
  3.6  a document checklist for the chosen schemes, de-duplicated

Speech, translation and the Android UI are not part of this module.

    python engine/bhashasetu.py validate dataset/packs/sample_pack_v0.1
    python engine/bhashasetu.py export   dataset/packs/sample_pack_v0.1 out.sqlite
    python engine/bhashasetu.py match    out.sqlite --age 64 --state KA --occupation farmer --income below_1l --query "pension"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

INCOME_BRACKETS = ["below_1l", "1l_2.5l", "2.5l_5l", "above_5l"]  # annual household income, rupees
OCCUPATIONS = {"farmer", "agri_labourer", "construction_worker", "street_vendor", "student", "self_employed", "salaried", "unemployed", "homemaker", "other"}
GENDERS = {"female", "male", "other"}
SOCIAL_CATEGORIES = {"general", "obc", "sc", "st"}
MARITAL_STATUSES = {"single", "married", "widowed", "separated"}
CATEGORIES = {"pension", "agriculture", "health", "education", "housing", "livelihood", "women", "disability"}
HARD_FIELDS = {"min_age", "max_age", "states", "occupations", "max_income", "genders", "social_categories", "marital_statuses", "disability"}
SOFT_FIELDS = {"priority_genders", "priority_social_categories", "priority_occupations"}
REQUIRED = {"scheme_id", "scheme_name", "category", "state_applicability", "benefits_text", "eligibility_rules",
            "required_documents", "application_channels", "official_link", "last_updated", "source"}

# Words a user might say for a category ("budhapa" etc. would come from the speech/translation layer).
CATEGORY_WORDS = {
    "pension": {"pension", "old", "elderly", "retirement", "monthly"},
    "agriculture": {"farm", "farmer", "crop", "seed", "fertiliser", "fertilizer", "kisan", "land"},
    "health": {"health", "hospital", "treatment", "medicine", "insurance", "doctor"},
    "education": {"school", "college", "scholarship", "study", "fees", "student"},
    "housing": {"house", "home", "housing", "roof", "shelter"},
    "livelihood": {"job", "work", "loan", "business", "skill", "training", "vendor"},
    "women": {"women", "woman", "girl", "mother", "widow", "pregnant"},
    "disability": {"disability", "disabled", "handicap", "wheelchair"},
}

STATE_NAMES = {"KA": "Karnataka", "TN": "Tamil Nadu", "MH": "Maharashtra", "UP": "Uttar Pradesh", "BR": "Bihar", "TS": "Telangana"}


# ---------------------------------------------------------------- packs (3.3)
def validate_scheme(s: Dict[str, Any]) -> List[str]:
    """Problems with one scheme record; empty when it is valid."""
    errors = []
    missing = REQUIRED - set(s)
    if missing:
        return [f"missing fields: {', '.join(sorted(missing))}"]
    if s["category"] not in CATEGORIES:
        errors.append(f"unknown category {s['category']!r}")
    if not (s["state_applicability"] == "ALL" or (isinstance(s["state_applicability"], list) and s["state_applicability"])):
        errors.append("state_applicability must be 'ALL' or a non-empty list of state codes")
    rules = s["eligibility_rules"]
    if not isinstance(rules, dict):
        return errors + ["eligibility_rules must be an object"]
    unknown = set(rules) - HARD_FIELDS - SOFT_FIELDS
    if unknown:
        errors.append(f"unknown eligibility rule(s): {', '.join(sorted(unknown))}")
    if "max_income" in rules and rules["max_income"] not in INCOME_BRACKETS:
        errors.append(f"max_income must be one of {INCOME_BRACKETS}")
    for key, allowed in (("occupations", OCCUPATIONS), ("priority_occupations", OCCUPATIONS), ("genders", GENDERS),
                         ("priority_genders", GENDERS), ("social_categories", SOCIAL_CATEGORIES),
                         ("priority_social_categories", SOCIAL_CATEGORIES), ("marital_statuses", MARITAL_STATUSES)):
        bad = set(rules.get(key, [])) - allowed
        if bad:
            errors.append(f"{key} has unknown values: {', '.join(sorted(bad))}")
    if "min_age" in rules and "max_age" in rules and rules["min_age"] > rules["max_age"]:
        errors.append("min_age is greater than max_age")
    if not s["required_documents"]:
        errors.append("required_documents is empty")
    if not str(s["official_link"]).startswith("https://"):
        errors.append("official_link must be an https URL")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s["last_updated"])):
        errors.append("last_updated must be YYYY-MM-DD")
    return errors


def load_pack(pack_dir: Path) -> Dict[str, Any]:
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    schemes = json.loads((pack_dir / "schemes.json").read_text(encoding="utf-8"))
    return {"manifest": manifest, "schemes": schemes}


def validate_pack(pack_dir: Path) -> List[str]:
    pack = load_pack(pack_dir)
    errors = []
    seen = set()
    for i, s in enumerate(pack["schemes"]):
        sid = s.get("scheme_id", f"#{i}")
        if sid in seen:
            errors.append(f"{sid}: duplicate scheme_id")
        seen.add(sid)
        errors += [f"{sid}: {e}" for e in validate_scheme(s)]
    return errors


def pack_checksum(pack_dir: Path) -> str:
    """SHA-256 over schemes.json bytes; the app compares it with the manifest before importing (3.7)."""
    return hashlib.sha256((pack_dir / "schemes.json").read_bytes()).hexdigest()


def export_sqlite(pack_dir: Path, db_path: Path) -> int:
    errors = validate_pack(pack_dir)
    if errors:
        raise ValueError("pack is invalid:\n  " + "\n  ".join(errors))
    pack = load_pack(pack_dir)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE schemes (scheme_id TEXT PRIMARY KEY, scheme_name TEXT, category TEXT, state_applicability TEXT,
            benefits_text TEXT, eligibility_rules TEXT, required_documents TEXT, application_channels TEXT,
            official_link TEXT, last_updated TEXT, source TEXT, keywords TEXT);
        CREATE VIRTUAL TABLE schemes_fts USING fts5(scheme_id UNINDEXED, scheme_name, benefits_text, keywords);
    """)
    for s in pack["schemes"]:
        keywords = " ".join(s.get("keywords", []))
        con.execute("INSERT INTO schemes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            s["scheme_id"], s["scheme_name"], s["category"], json.dumps(s["state_applicability"]), s["benefits_text"],
            json.dumps(s["eligibility_rules"]), json.dumps(s["required_documents"]), json.dumps(s["application_channels"]),
            s["official_link"], s["last_updated"], s["source"], keywords))
        con.execute("INSERT INTO schemes_fts VALUES (?,?,?,?)", (s["scheme_id"], s["scheme_name"], s["benefits_text"], keywords))
    con.executemany("INSERT INTO meta VALUES (?,?)", [
        ("pack_version", pack["manifest"].get("version", "")), ("checksum", pack_checksum(pack_dir)),
        ("illustrative", json.dumps(pack["manifest"].get("illustrative", False)))])
    con.commit()
    con.close()
    return len(pack["schemes"])


def load_db(db_path: Path) -> List[Dict[str, Any]]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = []
    for r in con.execute("SELECT * FROM schemes"):
        d = dict(r)
        for key in ("state_applicability", "eligibility_rules", "required_documents", "application_channels"):
            d[key] = json.loads(d[key])
        d["keywords"] = d["keywords"].split()
        rows.append(d)
    con.close()
    return rows


# ------------------------------------------------------------ matching (3.4)
STOPWORDS = {"a", "an", "the", "for", "of", "to", "in", "on", "and", "or", "is", "are", "i", "me", "my", "we", "our",
             "you", "your", "what", "which", "how", "can", "get", "any", "there", "scheme", "schemes", "yojana",
             "with", "from", "by", "at", "be", "do", "does", "want", "need", "about", "some", "people"}


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in STOPWORDS and len(w) > 1}


def query_categories(query: str) -> set:
    words = _tokens(query)
    return {cat for cat, vocab in CATEGORY_WORDS.items() if words & vocab}


def retrieve(schemes: List[Dict[str, Any]], query: str, n: int = 20) -> List[Dict[str, Any]]:
    """Stage A: keyword overlap with name/benefits/keywords, boosted when the category is mentioned.
    An empty query returns every scheme (the user is browsing or only answered the wizard)."""
    words = _tokens(query)
    if not words:
        return list(schemes)
    wanted = query_categories(query)
    scored = []
    for s in schemes:
        text = _tokens(" ".join([s["scheme_name"], s["benefits_text"], " ".join(s.get("keywords", []))]))
        score = len(words & text) + (2 if s["category"] in wanted else 0)
        if score > 0:
            scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1]["scheme_name"]))
    return [s for _, s in scored[:n]]


def check_eligibility(s: Dict[str, Any], a: Dict[str, Any]) -> Dict[str, Any]:
    """Stage B for one scheme. Unknown answers never disqualify; they become 'to confirm' items."""
    rules = s["eligibility_rules"]
    reasons, fails, unknown, bonus = [], [], [], 0
    age = a.get("age")

    if "min_age" in rules or "max_age" in rules:
        lo, hi = rules.get("min_age"), rules.get("max_age")
        if age is None:
            unknown.append("age")
        elif (lo is not None and age < lo) or (hi is not None and age > hi):
            fails.append(f"age must be {lo if lo is not None else 0}" + (f" to {hi}" if hi is not None else " or more"))
        else:
            reasons.append("Your age group fits")

    states = s["state_applicability"]
    if states != "ALL":
        if not a.get("state"):
            unknown.append("state")
        elif a["state"] not in states:
            fails.append("not offered in your state")
        else:
            reasons.append(f"Available in {STATE_NAMES.get(a['state'], a['state'])}")

    for key, answer_key, label in (("occupations", "occupation", "work"), ("genders", "gender", "gender"),
                                   ("social_categories", "social_category", "category"),
                                   ("marital_statuses", "marital_status", "marital status")):
        if key in rules:
            if not a.get(answer_key):
                unknown.append(answer_key)
            elif a[answer_key] not in rules[key]:
                fails.append(f"meant for a different {label}")
            elif key == "occupations":
                reasons.append(f"You said you are a {a[answer_key].replace('_', ' ')}")

    if "max_income" in rules:
        if not a.get("income"):
            unknown.append("income")
        elif INCOME_BRACKETS.index(a["income"]) > INCOME_BRACKETS.index(rules["max_income"]):
            fails.append("household income is above the limit")
        else:
            reasons.append("Your income is within the limit")

    if rules.get("disability"):
        if a.get("disability") is None:
            unknown.append("disability")
        elif not a["disability"]:
            fails.append("for people with a disability")
        else:
            reasons.append("Meant for people with a disability")

    for key, answer_key in (("priority_genders", "gender"), ("priority_social_categories", "social_category"),
                            ("priority_occupations", "occupation")):
        if a.get(answer_key) and a[answer_key] in rules.get(key, []):
            bonus += 1
            reasons.append("You are in a priority group")

    status = "not_eligible" if fails else ("check" if unknown else "eligible")
    return {"status": status, "reasons": reasons[:3], "fails": fails, "to_confirm": sorted(set(unknown)), "bonus": bonus}


def match(schemes: List[Dict[str, Any]], answers: Dict[str, Any], query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """Ranked schemes for one user. Eligible first, then 'check' (some answers missing); never the ineligible."""
    candidates = retrieve(schemes, query)
    order = {"eligible": 0, "check": 1}
    results = []
    for rank, s in enumerate(candidates):
        verdict = check_eligibility(s, answers)
        if verdict["status"] == "not_eligible":
            continue
        results.append({"scheme_id": s["scheme_id"], "scheme_name": s["scheme_name"], "category": s["category"],
                        "benefits": s["benefits_text"], "official_link": s["official_link"],
                        "channels": s["application_channels"], **verdict, "_rank": rank})
    results.sort(key=lambda r: (order[r["status"]], -r["bonus"], r["_rank"]))
    for r in results:
        r.pop("_rank")
    return results[:limit]


# ----------------------------------------------------------- checklist (3.6)
def checklist(schemes: List[Dict[str, Any]], scheme_ids: Iterable[str]) -> List[Dict[str, Any]]:
    """Documents needed for the chosen schemes, each listed once with the schemes that need it."""
    by_id = {s["scheme_id"]: s for s in schemes}
    docs: Dict[str, List[str]] = {}
    for sid in scheme_ids:
        if sid not in by_id:
            raise KeyError(f"unknown scheme {sid}")
        for d in by_id[sid]["required_documents"]:
            docs.setdefault(d, []).append(by_id[sid]["scheme_name"])
    return [{"document": d, "needed_for": names} for d, names in docs.items()]


# ------------------------------------------------------------------- CLI
def _answers(args) -> Dict[str, Any]:
    return {"age": args.age, "state": args.state, "occupation": args.occupation, "income": args.income,
            "gender": args.gender, "social_category": args.social_category, "marital_status": args.marital_status,
            "disability": None if args.disability is None else args.disability == "yes"}


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="BhashaSetu offline matching engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("pack", type=Path)
    e = sub.add_parser("export"); e.add_argument("pack", type=Path); e.add_argument("db", type=Path)
    m = sub.add_parser("match"); m.add_argument("db", type=Path)
    m.add_argument("--query", default=""); m.add_argument("--age", type=int); m.add_argument("--state")
    m.add_argument("--occupation", choices=sorted(OCCUPATIONS)); m.add_argument("--income", choices=INCOME_BRACKETS)
    m.add_argument("--gender", choices=sorted(GENDERS)); m.add_argument("--social-category", choices=sorted(SOCIAL_CATEGORIES))
    m.add_argument("--marital-status", choices=sorted(MARITAL_STATUSES))
    m.add_argument("--disability", choices=["yes", "no"]); m.add_argument("--checklist", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "validate":
        errors = validate_pack(args.pack)
        print("\n".join(errors) if errors else f"valid; sha256 {pack_checksum(args.pack)}")
        return 1 if errors else 0
    if args.cmd == "export":
        print(f"exported {export_sqlite(args.pack, args.db)} schemes to {args.db}")
        return 0

    schemes = load_db(args.db)
    results = match(schemes, _answers(args), args.query)
    if not results:
        print("No matching scheme in this pack.")
    for r in results:
        tag = "Likely eligible" if r["status"] == "eligible" else "Check: " + ", ".join(r["to_confirm"])
        print(f"\n{r['scheme_name']}  [{tag}]\n  {r['benefits']}")
        for reason in r["reasons"]:
            print(f"  - {reason}")
        print(f"  Apply: {', '.join(r['channels'])} | {r['official_link']}")
    confirmed = [r["scheme_id"] for r in results if r["status"] == "eligible"]
    if args.checklist and confirmed:
        print("\nDocuments to carry (for the schemes marked 'Likely eligible'):")
        for item in checklist(schemes, confirmed):
            print(f"  [ ] {item['document']}  ({', '.join(item['needed_for'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
