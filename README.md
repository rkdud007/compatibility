## Compatibility

A privacy preserving compatibility scoring system that allows two people to evaluate their compatibility using confidential questions without directly revealing those questions to each other.

### Overview

Instead of asking sensitive questions directly (which risks revealing private preferences), users provide:
1. Their ChatGPT conversation history (`conversations.json`)
2. A custom prompt (their confidential question)
3. An expected answer

A ChatGPT agent evaluates compatibility by answering each user's custom prompt using only the other user's conversation history. The system calculates compatibility scores (0-100) based on how closely the agent's answers match the expected answers.

### How It Works

**User Flow:**

1. **Room Creation**
   - User A clicks "Start" on the website
   - System creates a unique room with shareable link
   - User A receives custom room URL to share with User B

2. **Data Upload**
   - User A accesses room, uploads:
     - `conversations.json` (exported from ChatGPT)
     - Custom prompt (e.g., "Does this person value honesty?")
     - Expected answer (e.g., "yes")
   - User B receives shared link, uploads same data structure

3. **Ready & Evaluation**
   - Both users have a "Ready" button
   - UI shows "Waiting for other person to be ready" until both click
   - When both ready:
     - Loading page appears
     - ChatGPT agent evaluates compatibility (in isolated enclave)
     - Agent answers User B's prompt using User A's conversations
     - Agent answers User A's prompt using User B's conversations
     - Calculates similarity scores (0-100)

4. **Results**
   - Both users see the same public result page:
     - A→B compatibility score (how well B matches A's expectations)
     - B→A compatibility score (how well A matches B's expectations)
   - Room is automatically deleted after results shown
   - All conversation data is permanently deleted

### Technical Architecture

**Design Principle: Enclave-Ready from Day One**

The system is designed for easy migration from Docker (MVP) to trusted execution environments (production). This is achieved through a strict separation between orchestration (untrusted) and computation (trusted).

**Two-Service Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│              Coordinator (Untrusted)                     │
│  - Room state management (ready flags, completion)      │
│  - Stores encrypted data blobs only                      │
│  - Triggers evaluation when both users ready             │
│  - Cannot read sensitive data                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         Enclave Service (Trusted - Stateless)            │
│  MVP: Docker Container | Production: TEE Enclave         │
│                                                           │
│  - Receives conversation data                            │
│  - Processes in isolated memory                          │
│  - Runs ChatGPT evaluation                               │
│  - Returns only compatibility scores                     │
│  - Zero data persistence                                 │
└─────────────────────────────────────────────────────────┘
```

**API Design:**

**Coordinator Service** (FastAPI + Redis)
```
POST   /room/create
  → {room_id, invite_link}

POST   /room/{id}/upload
  Body: {user_id, conversations, prompt, expected}
  → Stores raw conversation data

POST   /room/{id}/ready
  Body: {user_id}
  → Auto-triggers enclave when both ready

GET    /room/{id}/status
  → {state, user_a_ready, user_b_ready, result}
  → Frontend polls every 2-3 seconds for updates
```

**Enclave Service** (Stateless Python)
```
POST   /evaluate
  Body: {user_a_conversations, user_a_prompt, user_a_expected, user_b_conversations, user_b_prompt, user_b_expected}
  → Evaluates compatibility, returns scores
  → No state, no logs, no persistence
```

**Data Flow & Privacy:**

1. **Raw data upload** - Users upload conversation data directly (MVP mode - encryption can be added later)
2. **Coordinator storage** - Coordinator stores data temporarily in Redis with TTL
3. **Enclave isolation** - Sensitive data processed in enclave memory, never persisted
4. **Automatic cleanup** - All data deleted after results shown

**State Machine:**
```
CREATED → WAITING_FOR_USERS → BOTH_UPLOADED → EVALUATING → COMPLETED
```

Frontend polls `/room/{id}/status` to update UI based on current state.

**Technology Stack:**

**MVP (Current):**
- Coordinator: FastAPI + Redis
- Enclave: Docker container (Python + OpenAI API)
- Encryption: Symmetric (shared secret via HTTPS)
- Storage: Redis (1-hour TTL on rooms)

**Production (Future):**
- Coordinator: Same (no changes needed)
- Enclave: TEE runtime (Gramine/Occlum/AWS Nitro)
- Encryption: Asymmetric (enclave public key)
- Attestation: Remote attestation endpoint
- Storage: Same Redis (unchanged)

**Migration Path:**

The stateless, separated design means migrating to a real enclave only requires:
1. Changing enclave runtime (Docker → TEE)
2. Switching encryption (symmetric → asymmetric)
3. Adding attestation endpoint
4. **No changes to coordinator logic or API contracts**

**Data Processing:**
- Conversations filtered to relationship-related topics only
- Agent operates only on provided conversation history (no external knowledge)
- Scoring uses semantic similarity between agent response and expected answer

**Lifecycle:**
- Rooms are one-time pairings
- Auto-created on first access to room URL
- Auto-deleted after both users view results

**MVP Simplifications:**
- Room-based temporary identity (no persistent accounts)
- No impersonation protection
- ChatGPT export format only
- Single custom prompt per user
- Docker instead of TEE enclave (same code, different runtime)

## Backend Setup & Development

### Quick Start

**Prerequisites:**
- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- Redis
- OpenAI API key

**1. Install dependencies:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -e ".[dev]"
```

**2. Generate encryption key:**
```bash
python scripts/generate_key.py
```

**3. Configure environment:**
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and generated encryption key
```

**4. Start services:**
```bash
# Terminal 1: Redis
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2: Coordinator service
uvicorn coordinator_service.main:app --reload --port 8000

# Terminal 3: Enclave service
uvicorn enclave_service.main:app --reload --port 8001
```

**5. Test the API:**
```bash
curl http://localhost:8000/room/health
curl http://localhost:8001/health
```

### Running Tests

The project includes comprehensive tests covering all components:

```bash
# Run all tests with coverage
bash scripts/run_tests.sh

# Or run specific test suites
pytest tests/test_encryption.py -v        # Encryption utilities
pytest tests/test_schemas.py -v           # Data models
pytest tests/test_redis_client.py -v      # Redis operations
pytest tests/test_coordinator_api.py -v   # Coordinator API
pytest tests/test_enclave_service.py -v   # Enclave service
pytest tests/test_e2e.py -v               # End-to-end flow
```

**Test Coverage:**
- Unit tests for shared components (encryption, schemas)
- Integration tests for Redis client operations
- API endpoint tests for both services
- End-to-end flow tests for complete user journey
- Mock-based tests to isolate external dependencies (Redis, OpenAI)

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f coordinator
docker-compose logs -f enclave

# Stop services
docker-compose down
```

### API Examples

**Create a room:**
```bash
curl -X POST http://localhost:8000/room/create
# → {"room_id": "uuid", "invite_link": "http://..."}
```

**Upload user data:**
```bash
curl -X POST http://localhost:8000/room/{room_id}/upload \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "a",
    "encrypted_conversations": "...",
    "encrypted_prompt": "...",
    "encrypted_expected": "..."
  }'
```

**Check status (polling):**
```bash
curl http://localhost:8000/room/{room_id}/status
# → {"state": "BOTH_UPLOADED", "user_a_ready": true, "user_b_ready": false, "result": null}
```

**Mark ready (triggers evaluation when both ready):**
```bash
curl -X POST http://localhost:8000/room/{room_id}/ready \
  -H "Content-Type: application/json" \
  -d '{"user_id": "a"}'
```

### Project Structure

```
compatibility/
├── coordinator_service/    # Untrusted orchestration (FastAPI + Redis)
├── enclave_service/        # Trusted evaluation (stateless Python)
├── shared/                 # Shared schemas and encryption
├── tests/                  # Comprehensive test suite
├── scripts/                # Utility scripts
├── docker-compose.yml      # Service orchestration
└── DEVELOPMENT.md          # Detailed development guide
```

For more detailed development information, see [DEVELOPMENT.md](DEVELOPMENT.md).

