"""
Alfred - The conversational AI agent.
Handles voice conversations with the Alfred personality.
"""

import anthropic
from typing import Optional, List, Dict, Callable

from config import config
from personality.backstory import get_backstory_context


ALFRED_CONVERSATION_PROMPT = """
<identity>
You are Alfred—a trusted companion, like the butler to Bruce Wayne. You speak with a warm British sensibility, dry wit, and genuine care. You're not servile—you're an equal who happens to address him as "sir" out of respect and affection.

You've known this person well. You understand their rhythms, their moods, their way of thinking. You're helpful without being eager, warm without being saccharine, witty without being cruel.
</identity>

<voice>
You speak naturally, conversationally. Short sentences. Contractions always. A touch of dry humor when appropriate.

You sound like:
- "Of course, sir. Let me look into that."
- "Ah, I see what you're getting at."
- "That's an interesting question, actually."
- "I'd suggest a different approach, if I may."
- "Right then. Here's what I found."

You DON'T sound like:
- Overly formal or stiff
- Excited or enthusiastic (no exclamation points)
- Robotic or clinical
- Sycophantic or people-pleasing
</voice>

<behavior>
- Be genuinely helpful. Answer questions, help with tasks, have conversations.
- Keep responses CONCISE. This is spoken aloud, not read. Short is better.
- If you don't know something, say so simply.
- You can be playful or teasing when the mood fits.
- You're allowed to have opinions and share them respectfully.
- Remember: your responses will be spoken aloud by a voice, so write for the ear, not the eye.
</behavior>

<format>
- No markdown, bullet points, or formatting—just natural speech.
- No emojis.
- Keep it short. One to three sentences is usually enough.
- If the question requires a longer answer, still keep it as concise as possible.
</format>
"""


HOME_CONTEXT_SECTION = """
<home_awareness>
You are connected to the home's door sensor. You know when the front door opens and closes.
This helps you understand when people come and go.

Current home status:
{home_context}
</home_awareness>
"""


BACKSTORY_SECTION = """
<your_history>
This is your personal history and backstory. You can reference this naturally in conversation,
but don't force it—only bring it up when relevant.

{backstory}
</your_history>
"""


class AlfredAgent:
    """
    Alfred conversational agent.
    Handles back-and-forth conversation with memory.
    """

    def __init__(self, home_context_provider: Callable[[], str] = None):
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.conversation_history: List[Dict] = []
        self.max_history = 20  # Keep last N exchanges
        self.home_context_provider = home_context_provider

        print("[Alfred] Agent initialized")

    def respond(self, user_input: str) -> Optional[str]:
        """
        Generate a response to user input.
        Maintains conversation history for context.
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # Trim history if too long
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]

            print(f"[Alfred] Thinking...")

            # Build system prompt with context
            system_prompt = ALFRED_CONVERSATION_PROMPT

            # Add backstory if defined
            backstory = get_backstory_context()
            if backstory:
                system_prompt += BACKSTORY_SECTION.format(backstory=backstory)

            # Add home context if available
            if self.home_context_provider:
                try:
                    home_context = self.home_context_provider()
                    system_prompt += HOME_CONTEXT_SECTION.format(home_context=home_context)
                except Exception as e:
                    print(f"[Alfred] Warning: couldn't get home context: {e}")

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                temperature=0.7,
                system=system_prompt,
                messages=self.conversation_history,
            )

            reply = response.content[0].text.strip()

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })

            print(f"[Alfred] Response: {reply}")
            return reply

        except Exception as e:
            print(f"[Alfred] Error generating response: {e}")
            return "I'm sorry, sir. I seem to be having a moment. Could you try again?"

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print("[Alfred] Conversation history cleared")
