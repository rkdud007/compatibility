"""Core evaluation logic for compatibility scoring."""

import logging
from typing import Tuple

from enclave_service.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class CompatibilityEvaluator:
    """Stateless compatibility evaluator.

    This component runs in the enclave (Docker for MVP, TEE for production).
    It evaluates compatibility and returns only scores.
    """

    def __init__(self):
        """Initialize evaluator with OpenAI client."""
        self.openai = OpenAIClient()

    def evaluate(
        self,
        user_a_conversations: list,
        user_a_prompt: str,
        user_a_expected: str,
        user_b_conversations: list,
        user_b_prompt: str,
        user_b_expected: str,
    ) -> Tuple[int, int]:
        """Evaluate compatibility between two users.

        This is the core enclave function that:
        1. Evaluates User A's prompt using User B's conversations.
        2. Evaluates User B's prompt using User A's conversations.
        3. Calculates similarity scores.
        4. Returns only the scores (no data leakage).

        Args:
            user_a_conversations: User A's conversation history.
            user_a_prompt: User A's question.
            user_a_expected: User A's expected answer.
            user_b_conversations: User B's conversation history.
            user_b_prompt: User B's question.
            user_b_expected: User B's expected answer.

        Returns:
            Tuple of (a_to_b_score, b_to_a_score).
        """

        logger.info("[1/4] Evaluating A→B: Answering A's prompt with B's context...")
        # A→B: Does B match A's expectations?
        # Answer A's prompt using B's conversations.
        a_to_b_answer = self.openai.answer_prompt_with_context(
            conversations=user_b_conversations,
            prompt=user_a_prompt,
        )
        logger.info(f"[1/4] ✓ Got answer: {a_to_b_answer[:100]}...")

        logger.info("[2/4] Calculating A→B similarity score...")
        a_to_b_score = self.openai.calculate_similarity_score(
            answer=a_to_b_answer,
            expected=user_a_expected,
        )
        logger.info(f"[2/4] ✓ A→B Score: {a_to_b_score}%")

        logger.info("[3/4] Evaluating B→A: Answering B's prompt with A's context...")
        # B→A: Does A match B's expectations?
        # Answer B's prompt using A's conversations.
        b_to_a_answer = self.openai.answer_prompt_with_context(
            conversations=user_a_conversations,
            prompt=user_b_prompt,
        )
        logger.info(f"[3/4] ✓ Got answer: {b_to_a_answer[:100]}...")

        logger.info("[4/4] Calculating B→A similarity score...")
        b_to_a_score = self.openai.calculate_similarity_score(
            answer=b_to_a_answer,
            expected=user_b_expected,
        )
        logger.info(f"[4/4] ✓ B→A Score: {b_to_a_score}%")

        logger.info("✓ Evaluation complete!")
        # Return only scores.
        return a_to_b_score, b_to_a_score
