"""End-to-end test for complete compatibility flow."""

import json
import logging
import time
import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from shared.schemas import UserId, RoomState

# Configure logging for test output.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestEndToEndFlow:
    """Test complete user flow from room creation to results."""

    @pytest.fixture
    def coordinator_client(self):
        """Create coordinator test client.

        Returns:
            TestClient instance.
        """
        from fastapi.testclient import TestClient
        from coordinator.main import app

        return TestClient(app)

    @pytest.fixture
    def enclave_client(self):
        """Create enclave test client.

        Returns:
            TestClient instance.
        """
        from fastapi.testclient import TestClient
        from enclave.main import app

        return TestClient(app)

    @pytest.fixture
    def conversations_a(self):
        """Load real conversations from conversations_A.json.

        Returns:
            List of conversation objects.
        """
        conversations_path = Path(__file__).parent.parent / "conversations_A.json"
        with open(conversations_path, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def conversations_b(self):
        """Load real conversations from conversations_B.json.

        Returns:
            List of conversation objects.
        """
        conversations_path = Path(__file__).parent.parent / "conversations_B.json"
        with open(conversations_path, 'r') as f:
            return json.load(f)

    def test_complete_compatibility_flow(
        self, coordinator_client
    ):
        """Test complete flow: create room → upload → ready → evaluate → results."""

        # Mock Redis, enclave HTTP client, and OpenAI for isolated test.
        with patch("coordinator.routes.rooms.redis_client") as mock_redis, \
             patch("coordinator.routes.rooms.httpx.AsyncClient") as mock_http_client, \
             patch("enclave.main.evaluator") as mock_evaluator:

            # Configure mocks.
            mock_redis.create_room.return_value = "test-room-e2e"
            mock_redis.get_room.return_value = Mock(room_id="test-room-e2e")
            mock_redis.mark_user_uploaded.return_value = True
            mock_redis.mark_user_ready.return_value = True
            mock_evaluator.evaluate.return_value = (85, 90)

            # Mock enclave upload response.
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_http_client.return_value.__aenter__.return_value.post.return_value = mock_response

            # Step 1: User A creates room.
            create_response = coordinator_client.post("/room/create")
            assert create_response.status_code == 200
            room_data = create_response.json()
            room_id = room_data["room_id"]
            invite_link = room_data["invite_link"]

            assert room_id == "test-room-e2e"
            assert room_id in invite_link

            # Step 2: User A uploads data.
            user_a_conversations = [
                {"role": "user", "content": "I value deep conversations"},
                {"role": "assistant", "content": "That's meaningful"},
            ]
            user_a_prompt = "Does this person value intellectual depth?"
            user_a_expected = "Yes"

            upload_a_response = coordinator_client.post(
                f"/room/{room_id}/upload",
                json={
                    "user_id": "a",
                    "conversations": user_a_conversations,
                    "prompt": user_a_prompt,
                    "expected": user_a_expected,
                },
            )
            assert upload_a_response.status_code == 200
            assert upload_a_response.json()["success"] is True

            # Step 3: User B receives invite link and uploads data.
            user_b_conversations = [
                {"role": "user", "content": "I enjoy philosophical discussions"},
                {"role": "assistant", "content": "Interesting perspective"},
            ]
            user_b_prompt = "Does this person enjoy deep thinking?"
            user_b_expected = "Yes"

            upload_b_response = coordinator_client.post(
                f"/room/{room_id}/upload",
                json={
                    "user_id": "b",
                    "conversations": user_b_conversations,
                    "prompt": user_b_prompt,
                    "expected": user_b_expected,
                },
            )
            assert upload_b_response.status_code == 200
            assert upload_b_response.json()["success"] is True

            # Step 4: Mock status check - both uploaded.
            from shared.schemas import RoomData, UserData

            mock_room_both_uploaded = RoomData(
                room_id=room_id,
                state=RoomState.BOTH_UPLOADED,
                created_at=time.time(),
                user_a=UserData(uploaded=True, ready=False),
                user_b=UserData(uploaded=True, ready=False),
            )
            mock_redis.get_room.return_value = mock_room_both_uploaded

            status_response = coordinator_client.get(f"/room/{room_id}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["state"] == "BOTH_UPLOADED"
            assert status_data["user_a_ready"] is False
            assert status_data["user_b_ready"] is False

            # Step 5: User A clicks "Ready".
            mock_redis.both_users_ready.return_value = False
            ready_a_response = coordinator_client.post(
                f"/room/{room_id}/ready",
                json={"user_id": "a"},
            )
            assert ready_a_response.status_code == 200

            # Step 6: User B clicks "Ready" - triggers evaluation.
            mock_room_both_ready = RoomData(
                room_id=room_id,
                state=RoomState.BOTH_UPLOADED,
                created_at=time.time(),
                user_a=UserData(
                    uploaded=True,
                    ready=True,
                ),
                user_b=UserData(
                    uploaded=True,
                    ready=True,
                ),
            )
            mock_redis.get_room.return_value = mock_room_both_ready
            mock_redis.both_users_ready.return_value = True

            ready_b_response = coordinator_client.post(
                f"/room/{room_id}/ready",
                json={"user_id": "b"},
            )
            assert ready_b_response.status_code == 200

            # Step 7: Mock evaluation completion.
            from shared.schemas import EvaluationResult

            mock_room_completed = RoomData(
                room_id=room_id,
                state=RoomState.COMPLETED,
                created_at=time.time(),
                result=EvaluationResult(a_to_b_score=85, b_to_a_score=90),
            )
            mock_redis.get_room.return_value = mock_room_completed

            # Step 8: Both users poll status and get results.
            final_status = coordinator_client.get(f"/room/{room_id}/status")
            assert final_status.status_code == 200
            final_data = final_status.json()

            assert final_data["state"] == "COMPLETED"
            assert final_data["result"]["a_to_b_score"] == 85
            assert final_data["result"]["b_to_a_score"] == 90

            print("\n✅ End-to-end test passed!")
            print(f"   Room ID: {room_id}")
            print(f"   A→B Compatibility: {final_data['result']['a_to_b_score']}%")
            print(f"   B→A Compatibility: {final_data['result']['b_to_a_score']}%")

    def test_complete_compatibility_flow_with_real_data(
        self,
        coordinator_client,
        conversations_a,
        conversations_b
    ):
        """Test complete flow with real conversation data: create room → upload → ready → evaluate → results."""

        logger.info("=" * 80)
        logger.info("Starting end-to-end compatibility test with real conversation data")
        logger.info("=" * 80)

        # Mock Redis, enclave HTTP client, and OpenAI for isolated test.
        with patch("coordinator.routes.rooms.redis_client") as mock_redis, \
             patch("coordinator.routes.rooms.httpx.AsyncClient") as mock_http_client, \
             patch("enclave.main.evaluator") as mock_evaluator:

            # Configure mocks.
            mock_redis.create_room.return_value = "test-room-real-data"
            mock_redis.get_room.return_value = Mock(room_id="test-room-real-data")
            mock_redis.mark_user_uploaded.return_value = True
            mock_redis.mark_user_ready.return_value = True

            # Mock evaluation with realistic scores.
            mock_a_to_b_score = 78
            mock_b_to_a_score = 82
            mock_evaluator.evaluate.return_value = (mock_a_to_b_score, mock_b_to_a_score)

            # Mock enclave upload response.
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_http_client.return_value.__aenter__.return_value.post.return_value = mock_response

            # Step 1: User A creates room.
            logger.info("\n[Step 1] User A creates room")
            create_response = coordinator_client.post("/room/create")
            assert create_response.status_code == 200
            room_data = create_response.json()
            room_id = room_data["room_id"]
            invite_link = room_data["invite_link"]

            logger.info(f"Room created: {room_id}")
            logger.info(f"Invite link: {invite_link}")

            assert room_id == "test-room-real-data"
            assert room_id in invite_link

            # Step 2: User A uploads real conversation data.
            logger.info("\n[Step 2] User A uploads conversation data")
            logger.info(f"Number of conversations: {len(conversations_a)}")

            user_a_prompt = "Does this person value intellectual depth and meaningful conversations?"
            user_a_expected = "Yes"

            upload_a_response = coordinator_client.post(
                f"/room/{room_id}/upload",
                json={
                    "user_id": "a",
                    "conversations": conversations_a,
                    "prompt": user_a_prompt,
                    "expected": user_a_expected,
                },
            )
            assert upload_a_response.status_code == 200
            assert upload_a_response.json()["success"] is True
            logger.info("User A data uploaded successfully")

            # Step 3: User B receives invite link and uploads data.
            logger.info("\n[Step 3] User B uploads conversation data")
            logger.info(f"Number of conversations: {len(conversations_b)}")

            user_b_prompt = "Does this person enjoy philosophical discussions and self-reflection?"
            user_b_expected = "Yes"

            upload_b_response = coordinator_client.post(
                f"/room/{room_id}/upload",
                json={
                    "user_id": "b",
                    "conversations": conversations_b,
                    "prompt": user_b_prompt,
                    "expected": user_b_expected,
                },
            )
            assert upload_b_response.status_code == 200
            assert upload_b_response.json()["success"] is True
            logger.info("User B data uploaded successfully")

            # Step 4: Mock status check - both uploaded.
            logger.info("\n[Step 4] Checking room status after both uploads")
            from shared.schemas import RoomData, UserData

            mock_room_both_uploaded = RoomData(
                room_id=room_id,
                state=RoomState.BOTH_UPLOADED,
                created_at=time.time(),
                user_a=UserData(uploaded=True, ready=False),
                user_b=UserData(uploaded=True, ready=False),
            )
            mock_redis.get_room.return_value = mock_room_both_uploaded

            status_response = coordinator_client.get(f"/room/{room_id}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["state"] == "BOTH_UPLOADED"
            assert status_data["user_a_ready"] is False
            assert status_data["user_b_ready"] is False
            logger.info(f"Room state: {status_data['state']}")

            # Step 5: User A clicks "Ready".
            logger.info("\n[Step 5] User A marks ready")
            mock_redis.both_users_ready.return_value = False
            ready_a_response = coordinator_client.post(
                f"/room/{room_id}/ready",
                json={"user_id": "a"},
            )
            assert ready_a_response.status_code == 200
            logger.info("User A is ready")

            # Step 6: User B clicks "Ready" - triggers evaluation.
            logger.info("\n[Step 6] User B marks ready - triggering evaluation")
            mock_room_both_ready = RoomData(
                room_id=room_id,
                state=RoomState.BOTH_UPLOADED,
                created_at=time.time(),
                user_a=UserData(
                    uploaded=True,
                    ready=True,
                ),
                user_b=UserData(
                    uploaded=True,
                    ready=True,
                ),
            )
            mock_redis.get_room.return_value = mock_room_both_ready
            mock_redis.both_users_ready.return_value = True

            ready_b_response = coordinator_client.post(
                f"/room/{room_id}/ready",
                json={"user_id": "b"},
            )
            assert ready_b_response.status_code == 200
            logger.info("User B is ready")
            logger.info("Evaluation should be triggered...")

            # Step 7: Mock evaluation completion.
            logger.info("\n[Step 7] Evaluation completes")
            from shared.schemas import EvaluationResult

            mock_room_completed = RoomData(
                room_id=room_id,
                state=RoomState.COMPLETED,
                created_at=time.time(),
                result=EvaluationResult(
                    a_to_b_score=mock_a_to_b_score,
                    b_to_a_score=mock_b_to_a_score
                ),
            )
            mock_redis.get_room.return_value = mock_room_completed

            # Step 8: Both users poll status and get results.
            logger.info("\n[Step 8] Users retrieve compatibility results")
            final_status = coordinator_client.get(f"/room/{room_id}/status")
            assert final_status.status_code == 200
            final_data = final_status.json()

            assert final_data["state"] == "COMPLETED"
            assert final_data["result"]["a_to_b_score"] == mock_a_to_b_score
            assert final_data["result"]["b_to_a_score"] == mock_b_to_a_score

            logger.info("\n" + "=" * 80)
            logger.info("✅ End-to-end test PASSED with real conversation data!")
            logger.info("=" * 80)
            logger.info(f"Room ID: {room_id}")
            logger.info(f"User A's conversations: {len(conversations_a)} loaded")
            logger.info(f"User B's conversations: {len(conversations_b)} loaded")
            logger.info(f"User A's question: {user_a_prompt}")
            logger.info(f"User B's question: {user_b_prompt}")
            logger.info("-" * 80)
            logger.info("EVALUATION RESULTS:")
            logger.info(f"  A→B Compatibility Score: {final_data['result']['a_to_b_score']}%")
            logger.info(f"  B→A Compatibility Score: {final_data['result']['b_to_a_score']}%")
            logger.info(f"  Average Compatibility: {(final_data['result']['a_to_b_score'] + final_data['result']['b_to_a_score']) / 2:.1f}%")
            logger.info("=" * 80 + "\n")

    def test_user_uploads_without_ready_stays_waiting(
        self, coordinator_client
    ):
        """Test that users can upload but evaluation doesn't start until both ready."""

        with patch("coordinator.routes.rooms.redis_client") as mock_redis, \
             patch("coordinator.routes.rooms.httpx.AsyncClient") as mock_http_client:
            mock_redis.create_room.return_value = "test-room-waiting"
            mock_redis.get_room.return_value = Mock(room_id="test-room-waiting")
            mock_redis.mark_user_uploaded.return_value = True

            # Mock enclave upload response.
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_http_client.return_value.__aenter__.return_value.post.return_value = mock_response

            # Create room.
            create_response = coordinator_client.post("/room/create")
            room_id = create_response.json()["room_id"]

            # User A uploads.
            coordinator_client.post(
                f"/room/{room_id}/upload",
                json={
                    "user_id": "a",
                    "conversations": [],
                    "prompt": "test prompt",
                    "expected": "test expected",
                },
            )

            # Mock room state - waiting for user B.
            from shared.schemas import RoomData, UserData

            mock_room = RoomData(
                room_id=room_id,
                state=RoomState.WAITING_FOR_USERS,
                created_at=time.time(),
                user_a=UserData(uploaded=True, ready=False),
            )
            mock_redis.get_room.return_value = mock_room

            status = coordinator_client.get(f"/room/{room_id}/status")
            assert status.status_code == 200
            assert status.json()["state"] == "WAITING_FOR_USERS"

    def test_cannot_mark_ready_without_upload(self, coordinator_client):
        """Test that users cannot mark ready without uploading data first."""

        with patch("coordinator.routes.rooms.redis_client") as mock_redis:
            mock_redis.mark_user_ready.return_value = False

            response = coordinator_client.post(
                "/room/test-room/ready",
                json={"user_id": "a"},
            )

            assert response.status_code == 400
            assert "hasn't uploaded" in response.json()["detail"]
