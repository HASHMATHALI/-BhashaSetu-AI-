"""Tests for the offline matching engine. Standard library + pytest only:  pytest"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import bhashasetu as bs  # noqa: E402

PACK = ROOT / "dataset" / "packs" / "sample_pack_v0.1"


@pytest.fixture(scope="module")
def schemes(tmp_path_factory):
    db = tmp_path_factory.mktemp("db") / "pack.sqlite"
    assert bs.export_sqlite(PACK, db) == 8
    return bs.load_db(db)


def names(results):
    return [r["scheme_name"] for r in results]


def test_sample_pack_is_valid_and_marked_fictional():
    assert bs.validate_pack(PACK) == []
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["illustrative"] is True
    for s in json.loads((PACK / "schemes.json").read_text(encoding="utf-8")):
        assert s["scheme_name"].startswith("Sample ") and "example.gov.in" in s["official_link"]


def test_validator_catches_bad_records(tmp_path):
    shutil.copytree(PACK, tmp_path / "pack")
    data = json.loads((tmp_path / "pack" / "schemes.json").read_text(encoding="utf-8"))
    data[0]["eligibility_rules"] = {"min_age": 70, "max_age": 60, "max_income": "lots", "aadhaar": True}
    data[1]["official_link"] = "http://insecure.example"
    data[2]["scheme_id"] = data[3]["scheme_id"]
    del data[4]["required_documents"]
    (tmp_path / "pack" / "schemes.json").write_text(json.dumps(data), encoding="utf-8")
    errors = "\n".join(bs.validate_pack(tmp_path / "pack"))
    for expected in ("min_age is greater", "max_income must be", "unknown eligibility rule(s): aadhaar",
                     "https URL", "duplicate scheme_id", "missing fields: required_documents"):
        assert expected in errors
    with pytest.raises(ValueError):
        bs.export_sqlite(tmp_path / "pack", tmp_path / "x.sqlite")


def test_checksum_changes_when_the_pack_changes(tmp_path):
    shutil.copytree(PACK, tmp_path / "pack")
    before = bs.pack_checksum(tmp_path / "pack")
    f = tmp_path / "pack" / "schemes.json"
    f.write_text(f.read_text(encoding="utf-8").replace("Monthly pension", "Monthly pensions"), encoding="utf-8")
    assert bs.pack_checksum(tmp_path / "pack") != before


def test_stop_words_do_not_pull_in_unrelated_schemes(schemes):
    results = bs.retrieve(schemes, "pension for old age")
    assert "Sample Farmer Income Support" not in names(results)
    assert names(results)[0] == "Sample Old-Age Pension"


def test_category_word_boosts_retrieval(schemes):
    assert names(bs.retrieve(schemes, "hospital"))[0] == "Sample Family Health Cover"
    assert bs.retrieve(schemes, "") == schemes  # no query: browse everything


def test_hard_filters_exclude_and_reasons_explain(schemes):
    elderly = {"age": 64, "state": "KA", "income": "below_1l", "gender": "female"}
    results = bs.match(schemes, elderly, "pension")
    pension = results[0]
    assert pension["scheme_name"] == "Sample Old-Age Pension" and pension["status"] == "eligible"
    assert "Your age group fits" in pension["reasons"] and len(pension["reasons"]) <= 3
    # too young for the pension
    assert "Sample Old-Age Pension" not in names(bs.match(schemes, {**elderly, "age": 40}, "pension"))
    # income above the limit
    assert "Sample Old-Age Pension" not in names(bs.match(schemes, {**elderly, "income": "above_5l"}, "pension"))


def test_unknown_answers_ask_instead_of_guessing(schemes):
    results = bs.match(schemes, {"age": 64, "state": "KA", "income": "below_1l", "gender": "female"}, "pension")
    widow = next(r for r in results if r["scheme_name"] == "Sample Widow Support Pension")
    assert widow["status"] == "check" and widow["to_confirm"] == ["marital_status"]
    assert results[0]["status"] == "eligible"  # confirmed matches come first


def test_state_restriction(schemes):
    farmer = {"occupation": "farmer", "income": "1l_2.5l"}
    assert "Sample Karnataka Drip Irrigation Subsidy" in names(bs.match(schemes, {**farmer, "state": "KA"}, "irrigation"))
    assert "Sample Karnataka Drip Irrigation Subsidy" not in names(bs.match(schemes, {**farmer, "state": "BR"}, "irrigation"))


def test_priority_group_ranks_higher_but_does_not_exclude(schemes):
    base = {"age": 20, "occupation": "student", "income": "below_1l"}
    woman = bs.match(schemes, {**base, "gender": "female"}, "scholarship")[0]
    man = bs.match(schemes, {**base, "gender": "male"}, "scholarship")[0]
    assert woman["scheme_name"] == man["scheme_name"] == "Sample Post-School Scholarship"
    assert woman["bonus"] == 1 and man["bonus"] == 0


def test_disability_rule(schemes):
    assert names(bs.match(schemes, {"disability": True, "income": "below_1l"}, "wheelchair")) == ["Sample Assistive Device Grant"]
    assert bs.match(schemes, {"disability": False, "income": "below_1l"}, "wheelchair") == []


def test_checklist_lists_each_document_once(schemes):
    items = bs.checklist(schemes, ["SAMPLE-PEN-01", "SAMPLE-WMN-01"])
    docs = [i["document"] for i in items]
    assert len(docs) == len(set(docs))
    residence = next(i for i in items if i["document"] == "Residence proof")
    assert residence["needed_for"] == ["Sample Old-Age Pension", "Sample Widow Support Pension"]
    with pytest.raises(KeyError):
        bs.checklist(schemes, ["NOPE"])


def test_no_sensitive_identifier_is_ever_an_answer():
    answer_keys = set(bs.check_eligibility({"eligibility_rules": {}, "state_applicability": "ALL"}, {}).keys())
    assert answer_keys == {"status", "reasons", "fails", "to_confirm", "bonus"}
    for forbidden in ("aadhaar", "bank_account", "phone"):
        assert forbidden not in bs.HARD_FIELDS | bs.SOFT_FIELDS


def test_cli_runs_end_to_end(tmp_path, capsys):
    db = tmp_path / "p.sqlite"
    assert bs.main(["export", str(PACK), str(db)]) == 0
    assert bs.main(["match", str(db), "--query", "loan for my vegetable cart", "--age", "30",
                    "--occupation", "street_vendor", "--checklist"]) == 0
    out = capsys.readouterr().out
    assert "Sample Street Vendor Micro-Loan  [Likely eligible]" in out and "Documents to carry" in out
