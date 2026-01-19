## Compatibility

A privacy preserving compatibility scoring system that allows two people to evaluate their compatibility using confidential questions without directly revealing those questions to each other.

### Overview

Instead of asking sensitive questions directly (which risks revealing private preferences), users provide:
1. Their ChatGPT conversation history (`conversations.json`)
2. A custom prompt (their confidential question)
3. An expected answer

A ChatGPT agent evaluates compatibility by answering each user's custom prompt using only the other user's conversation history. The system calculates compatibility scores (0-100) based on how closely the agent's answers match the expected answers.

### Quick Start

**Prerequisites:**
- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- Redis
- OpenAI API key

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f compatibility-coordinator
docker-compose logs -f compatibility-enclave

# Stop services
docker-compose down
```

### Run e2e test

```bash
uv sync
uv run scripts/test_real_e2e.py
```

### How It Works

```bash
compatibility on  main [✘?] is 📦 v0.1.0 via 🐍 v3.10.15 
❯ uv run tests/test_real_e2e.py

================================================================================
REAL E2E TEST
================================================================================

[Setup] Waiting for services...
  ✓ Coordinator ready
  ✓ Enclave ready

[Setup] Loading conversation files...
  ✓ Loaded 4 conversations for User A
  ✓ Loaded 3 conversations for User B

[Step 1] User A creates room
  Room ID: 72d1ca23-42d6-41bb-80d1-2cf25581b0c9

[Step 2] User A uploads data
  ✓ User A data uploaded

[Step 3] User B uploads data
  ✓ User B data uploaded

[Step 4] Check room status
  State: BOTH_UPLOADED
  User A ready: False
  User B ready: False

[Step 5] User A marks ready
  ✓ User A is ready

[Step 6] User B marks ready
  ✓ User B is ready
  → Evaluation triggered!

[Step 7] Waiting for evaluation...
  The evaluation performs 4 OpenAI API calls:
    1/4: Answer A's prompt with B's conversations
    2/4: Calculate A→B similarity score
    3/4: Answer B's prompt with A's conversations
    4/4: Calculate B→A similarity score
  This typically takes 30-60 seconds total.

  ⏳ Status: EVALUATING           ( 12s)..   ✓ Evaluation completed in 14s

[Step 8] Results

================================================================================
✅ TEST PASSED - COMPATIBILITY RESULTS
================================================================================

  Room ID: 72d1ca23-42d6-41bb-80d1-2cf25581b0c9
  A→B Compatibility: 40%
  B→A Compatibility: 60%
  Average: 50.0%

================================================================================
```

