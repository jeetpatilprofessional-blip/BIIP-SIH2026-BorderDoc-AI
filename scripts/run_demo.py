#!/usr/bin/env python3
"""
BIIP-SIH2026 Demo Runner
Runs all 7 mandated demo scenarios and verifies results
"""
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Any

API_BASE = "http://localhost:8000/api"
SCENARIOS = [
    "scenario_1", "scenario_2", "scenario_3", "scenario_4",
    "scenario_5", "scenario_6", "scenario_7"
]

EXPECTED_RESULTS = {
    "scenario_1": {"recommendation": "LOW_CONCERN", "min_confidence": 0.8, "min_net_score": 0.7},
    "scenario_2": {"recommendation": "HIGH_CONCERN", "min_confidence": 0.9, "max_net_score": -0.5, "critical_flags": ["DOCUMENT_EXPIRED"]},
    "scenario_3": {"recommendation": "HIGH_CONCERN", "min_confidence": 0.8, "max_net_score": -0.3, "critical_flags": ["FACE_MISMATCH"]},
    "scenario_4": {"recommendation": "HIGH_CONCERN", "min_confidence": 0.95, "max_net_score": -1.0, "critical_flags": ["WATCHLIST_HIT", "PASSPORT_REVOKED"]},
    "scenario_5": {"recommendation": "HIGH_CONCERN", "min_confidence": 0.9, "max_net_score": -1.0, "critical_flags": ["DOCUMENT_TAMPER_PHOTO", "FACE_MISMATCH"]},
    "scenario_6": {"recommendation": "SECONDARY_INSPECTION", "min_confidence": 0.7, "critical_flags": ["CROSS_FIELD_CONFLICT_DOB", "IDENTITY_FRAGMENTATION"]},
    "scenario_7": {"recommendation": "INSUFFICIENT_EVIDENCE", "max_confidence": 0.5, "unavailable_count": 3},
}

SCENARIO_NAMES = {
    "scenario_1": "Clean Traveler",
    "scenario_2": "Expired Passport",
    "scenario_3": "Face Mismatch",
    "scenario_4": "Watchlist Hit",
    "scenario_5": "Document Tampering",
    "scenario_6": "Identity Fragmentation",
    "scenario_7": "Offline Mode",
}


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_result(success: bool, message: str):
    icon = "[OK]" if success else "[FAIL]"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"  {color}{icon}{reset} {message}")


def run_scenario(scenario_id: str) -> Dict[str, Any]:
    """Run a single demo scenario"""
    print(f"\nRunning {SCENARIO_NAMES[scenario_id]} ({scenario_id})...")

    # Run scenario
    resp = requests.post(f"{API_BASE}/demo/scenarios/{scenario_id}/run", timeout=30)
    resp.raise_for_status()
    result = resp.json()

    case_id = result["case_id"]
    print(f"  Case created: {case_id} ({result['case_number']})")

    # Wait for processing
    time.sleep(3)

    # Get fusion result (recommendation)
    fusion_resp = requests.get(f"{API_BASE}/cases/{case_id}/recommendation/detail", timeout=10)
    fusion_resp.raise_for_status()
    fusion = fusion_resp.json()

    # Get evidence atoms
    evidence_resp = requests.get(f"{API_BASE}/cases/{case_id}/evidence", timeout=10)
    evidence_resp.raise_for_status()
    evidence_atoms = evidence_resp.json()

    # Get evidence summary
    summary_resp = requests.get(f"{API_BASE}/cases/{case_id}/evidence/summary", timeout=10)
    summary_resp.raise_for_status()
    evidence_summary = summary_resp.json()

    # Combine evidence data
    evidence = {
        "atoms": evidence_atoms,
        "summary": evidence_summary,
    }

    # Get identity graph
    graph_resp = requests.get(f"{API_BASE}/identity-graph/{case_id}", timeout=10)
    graph_resp.raise_for_status()
    graph = graph_resp.json()

    # Get audit
    audit_resp = requests.get(f"{API_BASE}/audit/{case_id}", timeout=10)
    audit_resp.raise_for_status()
    audit = audit_resp.json()

    return {
        "case_id": case_id,
        "case_number": result["case_number"],
        "fusion": fusion,
        "evidence": evidence,
        "graph": graph,
        "audit": audit,
    }


if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def verify_scenario(scenario_id: str, result: Dict) -> List[str]:
    """Verify scenario results against expectations"""
    errors = []
    expected = EXPECTED_RESULTS[scenario_id]
    fusion = result["fusion"]
    evidence = result["evidence"]
    graph = result["graph"]
    audit = result["audit"]

    # Check recommendation
    actual_rec = fusion.get("recommendation")
    if isinstance(actual_rec, dict):
        actual_rec = actual_rec.get("recommendation")
    expected_rec = expected["recommendation"]
    if actual_rec != expected_rec:
        errors.append(f"Recommendation: expected {expected_rec}, got {actual_rec}")
    else:
        print_result(True, f"Recommendation: {actual_rec}")


    # Check confidence
    confidence = fusion.get("confidence", 0)
    if "min_confidence" in expected:
        if confidence < expected["min_confidence"]:
            errors.append(f"Confidence {confidence:.2f} < min {expected['min_confidence']}")
        else:
            print_result(True, f"Confidence: {confidence:.2f} >= {expected['min_confidence']}")
    if "max_confidence" in expected:
        if confidence > expected["max_confidence"]:
            errors.append(f"Confidence {confidence:.2f} > max {expected['max_confidence']}")
        else:
            print_result(True, f"Confidence: {confidence:.2f} <= {expected['max_confidence']}")

    # Check net score
    net_score = fusion.get("net_score", 0)
    if "min_net_score" in expected:
        if net_score < expected["min_net_score"]:
            errors.append(f"Net score {net_score:.2f} < min {expected['min_net_score']}")
        else:
            print_result(True, f"Net score: {net_score:.2f} >= {expected['min_net_score']}")
    if "max_net_score" in expected:
        if net_score > expected["max_net_score"]:
            errors.append(f"Net score {net_score:.2f} > max {expected['max_net_score']}")
        else:
            print_result(True, f"Net score: {net_score:.2f} <= {expected['max_net_score']}")

    # Check critical flags
    if "critical_flags" in expected:
        critical_flags = fusion.get("critical_flags", [])
        for flag in expected["critical_flags"]:
            if flag not in critical_flags:
                errors.append(f"Missing critical flag: {flag}")
            else:
                print_result(True, f"Critical flag present: {flag}")

    # Check freshness (scenario 7)
    if "unavailable_count" in expected:
        freshness = fusion.get("freshness_breakdown", {})
        unavailable = freshness.get("UNAVAILABLE", 0)
        if unavailable < expected["unavailable_count"]:
            errors.append(f"UNAVAILABLE count {unavailable} < expected {expected['unavailable_count']}")
        else:
            print_result(True, f"UNAVAILABLE freshness count: {unavailable}")

        # Verify NO WATCHLIST_CLEAN (UNAVAILABLE ≠ CLEAR)
        atoms = evidence.get("atoms", [])
        watchlist_clean = [a for a in atoms if a["evidence_type"] == "WATCHLIST_CLEAN" and a["freshness"] == "VERIFIED_FRESH"]
        if watchlist_clean:
            errors.append("Found WATCHLIST_CLEAN with VERIFIED_FRESH - should be UNAVAILABLE!")
        else:
            print_result(True, "No WATCHLIST_CLEAN with VERIFIED_FRESH (UNAVAILABLE ≠ CLEAR verified)")

    # Check identity graph conflicts (scenario 6)
    if scenario_id == "scenario_6":
        conflicts = graph.get("conflicts", [])
        if not conflicts:
            errors.append("Expected identity graph conflicts (CONFLICTS_WITH edges)")
        else:
            print_result(True, f"Identity graph conflicts found: {len(conflicts)}")
            for c in conflicts:
                if c.get("field") == "birth_date":
                    print_result(True, f"  Conflict field: birth_date")

    # Check audit chain integrity
    if not audit.get("chain_verified", False):
        errors.append("Audit chain verification failed!")
    else:
        print_result(True, "Audit hash chain verified")

    # Check evidence counts
    atoms = evidence.get("atoms", [])
    # Map from summary fields - critical/high = negative (concern), info/low = positive (reassurance)
    critical = evidence.get("summary", {}).get("critical_count", 0)
    high = evidence.get("summary", {}).get("high_count", 0)
    negative = critical + high
    positive = len(atoms) - negative

    if "positive_count_min" in expected:
        if positive < expected["positive_count_min"]:
            errors.append(f"Positive evidence count {positive} < min {expected['positive_count_min']}")

    if "negative_count_min" in expected:
        if negative < expected["negative_count_min"]:
            errors.append(f"Negative evidence count {negative} < min {expected['negative_count_min']}")

    return errors


def main():
    print_header("BIIP-SIH2026 Demo Runner")

    # Check API health
    try:
        resp = requests.get(f"{API_BASE.replace('/api', '')}/health", timeout=5)
        if resp.status_code != 200:
            print("API not healthy")
            return 1
    except Exception as e:
        print(f"Cannot connect to API: {e}")
        print("Make sure backend is running on http://localhost:8000")
        return 1

    # Load test data
    print("Loading test data...")
    resp = requests.post(f"{API_BASE}/demo/load-test-data", timeout=30)
    if resp.status_code != 200:
        print("Failed to load test data")
        return 1
    print("Test data loaded")

    # Run all scenarios
    all_results = {}
    all_errors = []

    for scenario_id in SCENARIOS:
        print_header(f"Scenario: {SCENARIO_NAMES[scenario_id]}")

        try:
            result = run_scenario(scenario_id)
            all_results[scenario_id] = result

            errors = verify_scenario(scenario_id, result)
            if errors:
                all_errors.extend([f"{scenario_id}: {e}" for e in errors])
                for e in errors:
                    print_result(False, e)
            else:
                print_result(True, "All checks passed")

        except Exception as e:
            all_errors.append(f"{scenario_id}: {str(e)}")
            print_result(False, f"Error: {e}")

    # Summary
    print_header("SUMMARY")

    passed = len(SCENARIOS) - len(set(e.split(":")[0] for e in all_errors))
    failed = len(SCENARIOS) - passed

    print(f"Scenarios run: {len(SCENARIOS)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if all_errors:
        print("\nFailures:")
        for error in all_errors:
            print(f"  ✗ {error}")
        return 1
    else:
        print("\n✓ All 7 demo scenarios passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())