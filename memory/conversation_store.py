"""
Conversation memory - stores summaries of past conversations.
Uses Claude to summarize and extract facts after conversations end.
"""

import json
import anthropic
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from config import config
from memory.user_profile import get_user_profile
from memory.relationships import get_relationship_graph


SUMMARIZE_PROMPT = """Summarize this conversation between Alfred (an AI butler) and the user.

Conversation:
{conversation}

Provide a JSON response with:
1. "summary": A 1-2 sentence summary of what was discussed
2. "topics": List of topics covered (max 5)
3. "facts_learned": List of facts learned about the user (things they mentioned about themselves, their preferences, plans, etc.) - only include if clearly stated, not inferred
4. "mood": The user's apparent mood (e.g., "relaxed", "stressed", "curious")
5. "people_mentioned": List of people mentioned in the conversation, each with:
   - "name": The person's name (e.g., "Sarah", "Marcus from Brooklyn", "my brother Tom")
   - "relationship": How user knows them (friend, brother, sister, colleague, boss, etc.) - use "acquaintance" if unclear
   - "details": List of any facts learned about this person (e.g., ["works at Google", "into vinyl records"])
   - "visiting": true if user mentioned they're visiting/coming over, false otherwise
   - "visit_time": When they're visiting if mentioned (e.g., "tomorrow", "Thursday", "next week")

Only include people_mentioned if people were actually mentioned. Do not include Alfred or the user themselves.

Respond ONLY with valid JSON, no other text."""


class ConversationStore:
    """
    Stores conversation summaries and extracts facts for the user profile.
    """

    def __init__(self, store_file: str = "conversations.json"):
        self.store_file = Path(__file__).parent.parent / "data" / store_file
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()

        if config.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        else:
            self.client = None

    def _load(self):
        """Load conversation history from disk."""
        if self.store_file.exists():
            try:
                with open(self.store_file, "r") as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[ConversationStore] Error loading: {e}")
                self._data = self._default_store()
        else:
            self._data = self._default_store()

    def _default_store(self) -> dict:
        """Return empty store structure."""
        return {
            "conversations": [],
            "last_topics": [],
        }

    def _save(self):
        """Persist store to disk."""
        # Keep only last 30 days of conversations
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        self._data["conversations"] = [
            c for c in self._data["conversations"]
            if c.get("date", "") > cutoff
        ]

        with open(self.store_file, "w") as f:
            json.dump(self._data, f, indent=2)

    def summarize_conversation(self, messages: List[Dict]) -> Optional[Dict]:
        """
        Summarize a conversation and extract facts.

        Args:
            messages: List of {"role": "user"/"assistant", "content": str}

        Returns:
            Summary dict or None if summarization failed
        """
        if not self.client:
            return None

        if len(messages) < 2:
            return None  # Too short to summarize

        # Format conversation for summarization
        conversation_text = ""
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Alfred"
            conversation_text += f"{role}: {msg['content']}\n"

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Good balance of quality and cost
                max_tokens=1000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": SUMMARIZE_PROMPT.format(conversation=conversation_text)
                }]
            )

            result_text = response.content[0].text.strip()

            # Parse JSON response
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)

            return {
                "date": datetime.now().isoformat(),
                "summary": result.get("summary", ""),
                "topics": result.get("topics", []),
                "facts_learned": result.get("facts_learned", []),
                "mood": result.get("mood", "neutral"),
            }

        except Exception as e:
            print(f"[ConversationStore] Summarization error: {e}")
            return None

    def store_conversation(self, messages: List[Dict]):
        """
        Summarize and store a conversation.
        Also extracts facts to the user profile and people to the relationship graph.
        """
        summary = self.summarize_conversation(messages)
        if not summary:
            return

        # Store the summary
        self._data["conversations"].append(summary)

        # Update last topics
        self._data["last_topics"] = summary.get("topics", [])[:5]

        self._save()
        print(f"[ConversationStore] Stored: {summary['summary'][:50]}...")

        # Add learned facts to user profile
        profile = get_user_profile()
        for fact in summary.get("facts_learned", []):
            profile.add_fact(
                fact=fact,
                confidence=0.7,
                source=f"conversation {summary['date'][:10]}"
            )

        # Process people mentioned into relationship graph
        graph = get_relationship_graph()
        for person in summary.get("people_mentioned", []):
            try:
                graph.process_mention(
                    name=person.get("name", ""),
                    relationship_type=person.get("relationship", "acquaintance"),
                    details=person.get("details", []),
                    visiting=person.get("visiting", False),
                    visit_time=person.get("visit_time"),
                )
            except Exception as e:
                print(f"[ConversationStore] Error processing person {person}: {e}")

    def get_recent_summaries(self, count: int = 5) -> List[Dict]:
        """Get the most recent conversation summaries."""
        return self._data["conversations"][-count:]

    def get_last_topics(self) -> List[str]:
        """Get topics from the last conversation."""
        return self._data.get("last_topics", [])

    def get_context(self) -> Optional[str]:
        """
        Format recent conversations as context for prompts.
        Returns None if no conversation history.
        """
        recent = self.get_recent_summaries(3)
        if not recent:
            return None

        lines = []
        for conv in recent:
            date = conv.get("date", "")[:10]
            summary = conv.get("summary", "")
            if summary:
                lines.append(f"- {date}: {summary}")

        if not lines:
            return None

        return "Recent conversations:\n" + "\n".join(lines)


# Singleton instance
_store = None


def get_conversation_store() -> ConversationStore:
    """Get the conversation store singleton."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store


def get_conversation_context() -> Optional[str]:
    """Convenience function to get formatted conversation history."""
    return get_conversation_store().get_context()
