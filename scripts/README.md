# Test Scripts

## Real E2E Test

**[test_real_e2e.py](test_real_e2e.py)** - Single script to test the complete compatibility flow with real services.

### What it does

Replicates the exact flow from `tests/test_e2e.py:214` (`test_complete_compatibility_flow_with_real_data`) but **without any mocking**:

1. ✅ Real Redis for state management
2. ✅ Real Coordinator service API calls
3. ✅ Real Enclave service evaluation
4. ✅ Real OpenAI API for compatibility scoring
5. ✅ Real conversation data from `conversations_A.json` and `conversations_B.json`

### Quick Usage

```bash
# Start services
docker-compose up -d

# Run test
python scripts/test_real_e2e.py
```

### Test Flow

The script simulates two users going through the complete flow:

```
User A creates room
    ↓
User A uploads conversations + custom prompt
    ↓
User B uploads conversations + custom prompt
    ↓
Check room status (BOTH_UPLOADED)
    ↓
User A marks ready
    ↓
User B marks ready → triggers evaluation
    ↓
Wait for OpenAI evaluation (~30-60s)
    ↓
Display compatibility scores
```

### Output Example

```
REAL E2E TEST - NO MOCKING

[Setup] Waiting for services...
  ✓ Coordinator ready
  ✓ Enclave ready

[Setup] Loading conversation files...
  ✓ Loaded 150 conversations for User A
  ✓ Loaded 89 conversations for User B

[Step 1] User A creates room
  Room ID: abc-123-def

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
  ⏳ Status: EVALUATING (42s)
  ✓ Evaluation completed in 42s

[Step 8] Results

================================================================================
✅ TEST PASSED - COMPATIBILITY RESULTS
================================================================================

  A→B Compatibility: 78%
  B→A Compatibility: 82%
  Average: 80.0%

================================================================================
```

### Requirements

- Docker & Docker Compose running
- Valid `OPENAI_API_KEY` in `.env`
- Python 3.11+ with `requests` library
- Conversation files: `conversations_A.json`, `conversations_B.json`

### Troubleshooting

**Services not responding?**
```bash
docker-compose ps                    # Check status
docker-compose logs coordinator      # Check logs
docker-compose logs enclave
```

**Connection refused?**
- Make sure services are up: `docker-compose up -d`
- Wait 5-10 seconds for services to start
- Check health: `curl http://localhost:8000/health`

**OpenAI API errors?**
- Verify API key in `.env` is valid
- Check OpenAI status: https://status.openai.com

## Other Scripts

- **[quickstart.sh](quickstart.sh)** - Interactive menu for starting services and running tests
- **[interactive_test.py](interactive_test.py)** - Step-by-step interactive test (press Enter between steps)

## Notes

- Each test run makes **2 real OpenAI API calls** (costs ~$0.01-0.10 depending on model)
- Test takes **60-90 seconds** total (most time is OpenAI evaluation)
- No mocking means you're testing the actual production code path
- Services must be running before test execution
