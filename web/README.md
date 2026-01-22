# Compatibility Check Web UI

Production-quality web interface for the compatibility check backend services.

## Overview

This Next.js application provides an interactive UI that mirrors the exact flow implemented in `tests/test_real_e2e.py`. It allows users to:

1. Check health status of both coordinator and enclave services
2. Create or join compatibility check rooms
3. Upload conversation data for two users (A and B)
4. Trigger compatibility evaluation
5. View real-time results with detailed logging

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **API**: Native `fetch()` (no axios)
- **State**: React hooks + localStorage for persistence

## Prerequisites

Make sure the backend services are running:

```bash
# From the project root
docker-compose up -d
```

This starts:
- Coordinator service on `http://localhost:8000`
- Enclave service on `http://localhost:8001`

## Installation

```bash
cd web
bun install
```

## Development

```bash
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Production Build

```bash
bun run build
bun run start
```

## Environment Variables

The application uses environment variables to configure backend service URLs. Defaults match the values in `tests/test_real_e2e.py`:

```env
NEXT_PUBLIC_COORDINATOR_URL=http://localhost:8000
NEXT_PUBLIC_ENCLAVE_URL=http://localhost:8001
```

You can override these by creating a `.env.local` file (see `.env.local.example`).

## Features

### Landing Page (`/`)

- **Health Checks**: Real-time status badges for both services
- **Create Room**: Generates a new room ID and navigates to it
- **Join Room**: Enter an existing room ID to join

### Room Page (`/room/[roomId]`)

Interactive flow matching `tests/test_real_e2e.py`:

**Step 1**: Room created (automatic)
**Step 2**: User A uploads data
- Upload JSON file OR load default from `conversations_A.json`
- Enter prompt and expected answer
- Upload to backend

**Step 3**: User B uploads data
- Upload JSON file OR load default from `conversations_B.json`
- Enter prompt and expected answer
- Upload to backend

**Step 4**: Check room status (automatic)

**Step 5**: User A marks ready

**Step 6**: User B marks ready (triggers evaluation)

**Step 7**: Poll for completion
- Polls every 2 seconds
- 120-second timeout
- Shows progress in log console

**Step 8**: Display results
- A→B compatibility score
- B→A compatibility score
- Average compatibility

### Data Persistence

- Room ID and user data are saved to `localStorage`
- Data persists across page refreshes
- Each room maintains separate state

### Log Console

Collapsible console that shows:
- Step-by-step progress (1-8)
- Timestamps
- Color-coded messages (success, error, info)
- Mirrors the output from `tests/test_real_e2e.py`

### Error Handling

- Validates JSON file parsing
- Shows backend errors with status code and payload
- Disables buttons during API requests
- Friendly error messages for all failure cases

## File Structure

```
web/
├── app/
│   ├── api/
│   │   └── default-conversations/
│   │       └── route.ts          # API route to load repo JSON files
│   ├── room/
│   │   └── [roomId]/
│   │       └── page.tsx          # Room page (main flow)
│   ├── favicon.ico
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx                  # Landing page
├── components/
│   └── log-console.tsx           # Collapsible log component
├── lib/
│   └── api-client.ts             # Typed API client
├── .env.local                    # Environment variables (gitignored)
├── .env.local.example            # Environment template
├── package.json
├── tsconfig.json
└── README.md
```

## API Client

The typed API client (`lib/api-client.ts`) provides methods for all backend endpoints:

```typescript
// Coordinator
await apiClient.checkCoordinatorHealth()
await apiClient.createRoom()
await apiClient.uploadData(roomId, data)
await apiClient.getRoomStatus(roomId)
await apiClient.markReady(roomId, { user_id: "a" })

// Enclave
await apiClient.checkEnclaveHealth()
```

## Default Conversations

Users can choose to:
1. **Upload their own** conversation JSON files
2. **Load defaults** from the repository:
   - `conversations_A.json` (User A)
   - `conversations_B.json` (User B)

The default files are loaded via a Next.js API route (`/api/default-conversations?user=a|b`) which reads the files from the repo root.

## Testing the Flow

1. Start backend services: `docker-compose up -d`
2. Start web UI: `cd web && bun run dev`
3. Open browser to `http://localhost:3000`
4. Click "Create New Room"
5. For User A:
   - Click "Load Default" to use `conversations_A.json`
   - Enter prompt: "Does this person like to travel?"
   - Enter expected: "Yes, the person likes to travel"
   - Click "Upload Data"
   - Click "Mark Ready"
6. For User B:
   - Click "Load Default" to use `conversations_B.json`
   - Enter prompt: "Does this person prioritize work over partner?"
   - Enter expected: "No, this person prioritizes partner more"
   - Click "Upload Data"
   - Click "Mark Ready"
7. Watch the evaluation progress in the log console
8. View results when state becomes "COMPLETED"

## Notes

- No authentication (as per requirements)
- Browser cannot read arbitrary repo files directly; the API route handles file access
- The UI exactly mirrors the test script's behavior and endpoints
- All API calls use the same request bodies as the Python test script
- Polling interval (2s) and timeout (120s) match the test script values

## Troubleshooting

**Services show as offline:**
- Verify docker-compose is running: `docker-compose ps`
- Check service logs: `docker-compose logs coordinator` or `docker-compose logs enclave`

**Cannot load default conversations:**
- Ensure the web app is started from the `/web` directory
- Check that `conversations_A.json` and `conversations_B.json` exist in the parent directory

**API errors:**
- Open browser DevTools to see detailed error messages
- Check that environment variables point to the correct URLs
