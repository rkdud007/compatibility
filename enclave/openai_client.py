"""OpenAI client for GPT-based evaluation."""

import logging
from typing import List, Dict
from openai import OpenAI

from enclave.config import settings
from enclave.conversation_parser import extract_messages_from_chatgpt_export

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API interactions."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)

    def answer_prompt_with_context(
        self, conversations: List[Dict], prompt: str
    ) -> str:
        """Answer a prompt using conversation history as context.

        Args:
            conversations: List of conversation messages from ChatGPT export.
            prompt: The question to answer.

        Returns:
            GPT's answer based on the conversation context.
        """
        # Parse ChatGPT export format if needed.
        parsed_messages = extract_messages_from_chatgpt_export(conversations)

        # Build system message with conversation context.
        system_message = self._build_context_message(parsed_messages)

        logger.debug("=" * 80)
        logger.debug("PROMPT TO GPT:")
        logger.debug(f"User prompt: {prompt}")
        logger.debug(f"Raw conversations: {len(conversations)}")
        logger.debug(f"Parsed messages: {len(parsed_messages)}")
        logger.debug(f"System message (first 500 chars): {system_message[:500]}...")
        logger.debug("=" * 80)

        # Call GPT API.
        response = self.client.chat.completions.create(
            model="gpt-4",  # Use gpt-4 for better reasoning.
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,  # Moderate temperature for balanced reasoning and creativity.
            max_tokens=500,
        )

        answer = response.choices[0].message.content.strip()
        logger.debug(f"GPT Response: {answer}")
        logger.debug("=" * 80)

        return answer

    def _build_context_message(self, conversations: List[Dict]) -> str:
        """Build context message from conversation history.

        Args:
            conversations: Conversation messages.

        Returns:
            Formatted context for system message.
        """
        context_lines = [
            "You are an insightful psychologist and personality analyst examining a person's ChatGPT conversation history.",
            "Your task is to understand their personality, values, preferences, and behavioral patterns.",
            "",
            "IMPORTANT INSTRUCTIONS:",
            "- Make reasonable inferences based on conversation patterns, topics discussed, and tone.",
            "- Read between the lines: if someone frequently discusses work/tech, they likely value achievement and learning.",
            "- Consider indirect evidence: philosophical discussions suggest introspection, questions about relationships suggest social awareness.",
            "- Synthesize multiple data points to form holistic personality assessments.",
            "- Be confident in your analysis when patterns are clear, even if not explicitly stated.",
            "- Only say 'Unable to determine' if there is truly NO relevant information or the patterns are contradictory.",
            "",
            "Below is their conversation history:",
            "",
        ]

        # Add conversation excerpts with more generous limits.
        max_conversations = min(100, len(conversations))  # Increase to 100 for more context.
        for conv in conversations[:max_conversations]:
            role = conv.get("role", "user")
            content = conv.get("content", "")[:800]  # Increase to 800 chars per message.
            context_lines.append(f"[{role.upper()}]: {content}")

        context_lines.extend([
            "",
            "Based on this conversation history, answer the following question with thoughtful reasoning.",
            "Make inferences about their personality traits, values, and likely behaviors based on the evidence above.",
        ])

        return "\n".join(context_lines)

    def calculate_similarity_score(
        self, answer: str, expected: str
    ) -> int:
        """Calculate semantic similarity between answer and expected response.

        Args:
            answer: GPT's answer to the prompt.
            expected: Expected answer provided by user.

        Returns:
            Similarity score from 0-100.
        """
        # Use GPT to evaluate semantic similarity.
        similarity_prompt = f"""Compare the following two answers and rate their semantic similarity on a scale of 0-100.

Answer 1 (Actual): {answer}
Answer 2 (Expected): {expected}

Provide ONLY a number from 0-100 where:
- 0 = Completely opposite or unrelated
- 50 = Somewhat related but different
- 100 = Essentially the same meaning

Your response should be ONLY the number, nothing else."""

        logger.debug("=" * 80)
        logger.debug("SIMILARITY SCORING:")
        logger.debug(f"Actual answer: {answer}")
        logger.debug(f"Expected answer: {expected}")
        logger.debug("=" * 80)

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": similarity_prompt}],
            temperature=0.1,
            max_tokens=10,
        )

        raw_score = response.choices[0].message.content.strip()
        logger.debug(f"Raw similarity score from GPT: {raw_score}")

        try:
            score = int(raw_score)
            final_score = max(0, min(100, score))  # Clamp to 0-100.
            logger.debug(f"Final similarity score: {final_score}")
            logger.debug("=" * 80)
            return final_score
        except ValueError:
            logger.warning(f"Could not parse score '{raw_score}', using fallback")
            # Fallback: simple string matching if GPT doesn't return a number.
            fallback = self._fallback_similarity(answer, expected)
            logger.debug(f"Fallback similarity score: {fallback}")
            logger.debug("=" * 80)
            return fallback

    def _fallback_similarity(self, answer: str, expected: str) -> int:
        """Fallback similarity calculation using simple string matching.

        Args:
            answer: Actual answer.
            expected: Expected answer.

        Returns:
            Basic similarity score 0-100.
        """
        answer_lower = answer.lower()
        expected_lower = expected.lower()

        # Simple keyword matching.
        if expected_lower in answer_lower or answer_lower in expected_lower:
            return 80
        elif any(word in answer_lower for word in expected_lower.split()):
            return 50
        else:
            return 20
