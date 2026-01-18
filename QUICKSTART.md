# Quick Start: Real E2E Test

Run the complete compatibility flow with real services and real OpenAI API - no mocking!

## Steps

### 1. Start Docker Services

```bash
docker-compose up -d
```

This starts:
- Redis (port 6379)
- Coordinator service (port 8000)
- Enclave service (port 8001)

### 2. Run the Test

```bash
uv run scripts/test_real_e2e.py
```

That's it! The test will:
1. Wait for services to be ready
2. Load your real conversation data (`conversations_A.json`, `conversations_B.json`)
3. Create a room
4. Upload data for both users
5. Mark both users ready
6. Wait for real OpenAI evaluation (~30-60 seconds)
7. Display compatibility scores

## Expected Output

```
================================================================================
REAL E2E TEST 
================================================================================

[Setup] Waiting for services...
  ✓ Coordinator ready
  ✓ Enclave ready

[Setup] Loading conversation files...
  ✓ Loaded 150 conversations for User A
  ✓ Loaded 89 conversations for User B

[Step 1] User A creates room
  Room ID: abc123...

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

[Step 7] Waiting for evaluation (this may take 30-60 seconds)...
  ⏳ Status: EVALUATING (15s)
  ✓ Evaluation completed in 42s

[Step 8] Results

================================================================================
✅ TEST PASSED - COMPATIBILITY RESULTS
================================================================================

  Room ID: abc123...
  A→B Compatibility: 78%
  B→A Compatibility: 82%
  Average: 80.0%

================================================================================
```

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Restart
docker-compose down
docker-compose up -d
```

### Test can't connect to services
```bash
# Verify services are running
docker-compose ps

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### OpenAI API errors
- Check your `.env` file has valid `OPENAI_API_KEY`
- Verify API key at: https://platform.openai.com/api-keys

## Stop Services

```bash
docker-compose down
```

## What This Tests

✅ Real Redis state management
✅ Real HTTP communication between services
✅ Real OpenAI API calls
✅ Complete state machine flow
✅ Actual data serialization
✅ Real timing and async behavior

This is the same flow as `test_complete_compatibility_flow_with_real_data` in [tests/test_e2e.py:214](tests/test_e2e.py#L214), but without any mocking!
