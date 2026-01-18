#!/usr/bin/env python3
"""
Real E2E Test - No Mocking
Tests the complete compatibility flow using real Docker services and real OpenAI API.

Usage:
    1. Start services: docker-compose up -d
    2. Run test: python scripts/test_real_e2e.py
"""

import json
import sys
import time
from pathlib import Path

import requests


def log(message: str, color: str = ""):
    """Print colored log message."""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
    }
    end = "\033[0m"
    prefix = colors.get(color, "")
    print(f"{prefix}{message}{end}")


def main():
    """Run real end-to-end test."""
    coordinator_url = "http://localhost:8000"
    enclave_url = "http://localhost:8001"

    log("\n" + "=" * 80, "cyan")
    log("REAL E2E TEST - NO MOCKING", "bold")
    log("=" * 80 + "\n", "cyan")

    # Wait for services.
    log("[Setup] Waiting for services...", "cyan")
    health_endpoints = [
        ("Coordinator", f"{coordinator_url}/room/health"),
        ("Enclave", f"{enclave_url}/health")
    ]
    for service, health_url in health_endpoints:
        for _ in range(30):
            try:
                resp = requests.get(health_url, timeout=2)
                if resp.status_code == 200:
                    log(f"  ✓ {service} ready", "green")
                    break
            except:
                time.sleep(1)
        else:
            log(f"  ✗ {service} not responding. Is docker-compose running?", "red")
            sys.exit(1)

    # Load conversations.
    log("\n[Setup] Loading conversation files...", "cyan")
    base_path = Path(__file__).parent.parent
    with open(base_path / "conversations_A.json") as f:
        convs_a = json.load(f)
    with open(base_path / "conversations_B.json") as f:
        convs_b = json.load(f)
    log(f"  ✓ Loaded {len(convs_a)} conversations for User A", "green")
    log(f"  ✓ Loaded {len(convs_b)} conversations for User B", "green")

    # Step 1: Create room.
    log("\n[Step 1] User A creates room", "cyan")
    resp = requests.post(f"{coordinator_url}/room/create")
    resp.raise_for_status()
    room = resp.json()
    room_id = room["room_id"]
    log(f"  Room ID: {room_id}", "yellow")

    # Step 2: User A uploads data.
    log("\n[Step 2] User A uploads data", "cyan")
    resp = requests.post(
        f"{coordinator_url}/room/{room_id}/upload",
        json={
            "user_id": "a",
            "conversations": convs_a,
            "prompt": "Does this person value intellectual depth and meaningful conversations?",
            "expected": "Yes",
        },
    )
    resp.raise_for_status()
    log("  ✓ User A data uploaded", "green")

    # Step 3: User B uploads data.
    log("\n[Step 3] User B uploads data", "cyan")
    resp = requests.post(
        f"{coordinator_url}/room/{room_id}/upload",
        json={
            "user_id": "b",
            "conversations": convs_b,
            "prompt": "Does this person enjoy philosophical discussions and self-reflection?",
            "expected": "Yes",
        },
    )
    resp.raise_for_status()
    log("  ✓ User B data uploaded", "green")

    # Step 4: Check status.
    log("\n[Step 4] Check room status", "cyan")
    resp = requests.get(f"{coordinator_url}/room/{room_id}/status")
    status = resp.json()
    log(f"  State: {status['state']}", "yellow")
    log(f"  User A ready: {status['user_a_ready']}", "yellow")
    log(f"  User B ready: {status['user_b_ready']}", "yellow")

    # Step 5: User A marks ready.
    log("\n[Step 5] User A marks ready", "cyan")
    resp = requests.post(
        f"{coordinator_url}/room/{room_id}/ready",
        json={"user_id": "a"},
    )
    resp.raise_for_status()
    log("  ✓ User A is ready", "green")

    # Step 6: User B marks ready (triggers evaluation).
    log("\n[Step 6] User B marks ready", "cyan")
    resp = requests.post(
        f"{coordinator_url}/room/{room_id}/ready",
        json={"user_id": "b"},
    )
    resp.raise_for_status()
    log("  ✓ User B is ready", "green")
    log("  → Evaluation triggered!", "yellow")

    # Step 7: Wait for evaluation.
    log("\n[Step 7] Waiting for evaluation...", "cyan")
    log("  The evaluation performs 4 OpenAI API calls:", "yellow")
    log("    1/4: Answer A's prompt with B's conversations", "yellow")
    log("    2/4: Calculate A→B similarity score", "yellow")
    log("    3/4: Answer B's prompt with A's conversations", "yellow")
    log("    4/4: Calculate B→A similarity score", "yellow")
    log("  This typically takes 30-60 seconds total.\n", "yellow")

    start = time.time()
    while time.time() - start < 120:
        resp = requests.get(f"{coordinator_url}/room/{room_id}/status")
        status = resp.json()

        if status["state"] == "COMPLETED":
            log(f"  ✓ Evaluation completed in {int(time.time() - start)}s", "green")
            break

        elapsed = int(time.time() - start)
        # Show a simple progress indicator.
        dots = "." * ((elapsed // 2) % 4)
        print(f"\r  ⏳ Status: {status['state']:<20} ({elapsed:>3}s){dots:<3}", end="", flush=True)
        time.sleep(2)  # Poll every 2 seconds instead of 3.
    else:
        log("\n  ✗ Timeout waiting for evaluation", "red")
        sys.exit(1)

    # Step 8: Display results.
    log("\n[Step 8] Results", "cyan")
    result = status["result"]
    a_to_b = result["a_to_b_score"]
    b_to_a = result["b_to_a_score"]
    avg = (a_to_b + b_to_a) / 2

    log("\n" + "=" * 80, "green")
    log("✅ TEST PASSED - COMPATIBILITY RESULTS", "bold")
    log("=" * 80, "green")
    log(f"\n  Room ID: {room_id}", "yellow")
    log(f"  A→B Compatibility: {a_to_b}%", "green")
    log(f"  B→A Compatibility: {b_to_a}%", "green")
    log(f"  Average: {avg:.1f}%\n", "green")
    log("=" * 80 + "\n", "green")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\n⚠️  Test interrupted by user\n", "yellow")
        sys.exit(1)
    except Exception as e:
        log(f"\n\n❌ Test failed: {e}\n", "red")
        import traceback
        traceback.print_exc()
        sys.exit(1)
