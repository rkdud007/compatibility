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
uv run scripts/test_real_e2e.py
```