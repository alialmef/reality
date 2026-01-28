"""
Alfred - The conversational AI agent.
Uses Claude's native tool calling to control the home.
"""

import anthropic
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Callable, Generator

from config import config


def _load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory. Reloads each time for hot-reload support."""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    try:
        return prompt_path.read_text()
    except FileNotFoundError:
        print(f"[Alfred] Warning: Prompt file {prompt_path} not found")
        return ""


from personality.backstory import get_backstory_context
from memory.user_profile import get_profile_context, get_knowledge_gap_context
from memory.conversation_store import get_conversation_store, get_conversation_context
from memory.consolidation import get_consolidator, get_understanding_context
from memory.relationships import get_relationship_graph, get_relationships_context
from devices.lights import get_light_controller
from devices.music import get_music_controller
from devices.diffusers import get_diffuser_controller
from devices.coffee import get_coffee_controller


# Tool definitions - these are what Alfred can do
ALFRED_TOOLS = [
    {
        "name": "control_lights",
        "description": "Control the home's smart lights. Can turn on/off, set brightness, change color, or adjust warmth.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["on", "off", "brightness", "color", "warmth"],
                    "description": "What to do with the lights"
                },
                "target": {
                    "type": "string",
                    "description": "Which lights: 'living room', 'kitchen', 'hallway', or 'all'"
                },
                "value": {
                    "type": "string",
                    "description": "For brightness: 0-100. For color: red/blue/green/etc. For warmth: warm/cool/neutral"
                }
            },
            "required": ["action", "target"]
        }
    },
    {
        "name": "get_light_status",
        "description": "Check the current state of all lights - whether on/off, brightness level, and color",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_home_status",
        "description": "Get overall home status including door activity patterns and current light states",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "control_music",
        "description": "Control music playback - play, pause, skip, volume, search for songs/artists/playlists",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "pause", "toggle", "next", "previous", "volume", "search", "playlist", "shuffle"],
                    "description": "What to do: play/pause/toggle playback, next/previous track, set volume, search for music, play a playlist, or toggle shuffle"
                },
                "query": {
                    "type": "string",
                    "description": "For search: song/artist/album name. For playlist: playlist name. For volume: 'up', 'down', or 0-100"
                },
                "app": {
                    "type": "string",
                    "enum": ["Music", "Spotify"],
                    "description": "Which app to use (default: Apple Music)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_music_status",
        "description": "Get what's currently playing, player state, and volume level",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {
                    "type": "string",
                    "enum": ["Music", "Spotify"],
                    "description": "Which app to check (default: Apple Music)"
                }
            },
            "required": []
        }
    },
    {
        "name": "control_audio_output",
        "description": "Switch system audio output to a different speaker. Music uses External Headphones (Audioengine via AUX), Alfred's voice uses Yealink SP92.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["switch", "list", "current"],
                    "description": "switch to a device, list available devices, or get current device"
                },
                "device": {
                    "type": "string",
                    "enum": ["External Headphones", "Yealink SP92", "Mac mini Speakers"],
                    "description": "Device to switch to (for switch action)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "eucalyptus",
        "description": "Control the eucalyptus scent diffuser. Fresh, clean scent - energizing and clarifying. Good for focus and clear thinking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["on", "off", "status"],
                    "description": "Turn the eucalyptus diffuser on, off, or check its status"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "orange",
        "description": "Control the orange scent diffuser. Warm, citrus scent - uplifting and cheerful. Good for mood and welcoming guests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["on", "off", "status"],
                    "description": "Turn the orange diffuser on, off, or check its status"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "coffee",
        "description": "Control the coffee maker. Turning it on starts brewing. The coffee maker is connected via smart plug.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["brew", "off", "status"],
                    "description": "Start brewing coffee, turn off the coffee maker, or check its status"
                }
            },
            "required": ["action"]
        }
    }
]


class AlfredAgent:
    """
    Alfred conversational agent with tool use.
    Claude decides when to use tools - no hardcoded routing.
    """

    def __init__(self, home_context_provider: Callable[[], str] = None):
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.conversation_history: List[Dict] = []
        self.max_history = 20
        self.home_context_provider = home_context_provider
        self.last_interaction_time: float = 0
        self.conversation_timeout = 300
        self.light_controller = get_light_controller()
        self.music_controller = get_music_controller()
        self.diffuser_controller = get_diffuser_controller()
        self.coffee_controller = get_coffee_controller()

        print("[Alfred] Agent initialized")

    def respond(self, user_input: str) -> Optional[str]:
        """Generate a response, using tools when needed."""
        try:
            self.check_conversation_timeout()

            # Add user message
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # Trim history
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]

            print(f"[Alfred] Thinking...")

            # Build system prompt with all context
            system_prompt = self._build_system_prompt()

            # Call Claude with tools
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                temperature=0.7,
                system=system_prompt,
                messages=self.conversation_history,
                tools=ALFRED_TOOLS,
            )

            # Process response (may involve tool calls)
            reply = self._process_response(response)

            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })

            print(f"[Alfred] Response: {reply}")
            self.last_interaction_time = time.time()
            return reply

        except Exception as e:
            print(f"[Alfred] Error: {e}")
            import traceback
            traceback.print_exc()
            return "I'm sorry, sir. I seem to be having a moment. Could you try again?"

    def _process_response(self, response) -> str:
        """Process Claude's response, executing any tool calls."""

        # Check for tool use
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        text_blocks = [block for block in response.content if block.type == "text"]

        if not tool_uses:
            # No tools - just return text
            if text_blocks:
                return text_blocks[0].text.strip()
            return ""

        # Execute tools
        tool_results = []
        for tool_use in tool_uses:
            print(f"[Alfred] Using tool: {tool_use.name}")
            result = self._execute_tool(tool_use.name, tool_use.input)
            print(f"[Alfred] Tool result: {result}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result
            })

        # Build assistant message with tool use for history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_content
        })
        self.conversation_history.append({
            "role": "user",
            "content": tool_results
        })

        # Get final response after tool execution
        follow_up = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            temperature=0.7,
            system=self._build_system_prompt(),
            messages=self.conversation_history,
            tools=ALFRED_TOOLS,
        )

        # Extract text (shouldn't have more tool calls for simple actions)
        for block in follow_up.content:
            if block.type == "text":
                return block.text.strip()

        return "Done."

    def _execute_tool(self, name: str, inputs: dict) -> str:
        """Execute a tool and return the result."""
        try:
            if name == "control_lights":
                return self._control_lights(
                    inputs.get("action"),
                    inputs.get("target"),
                    inputs.get("value")
                )
            elif name == "get_light_status":
                return self.light_controller.get_detailed_status()
            elif name == "get_home_status":
                return self._get_home_status()
            elif name == "control_music":
                return self._control_music(
                    inputs.get("action"),
                    inputs.get("query"),
                    inputs.get("app")
                )
            elif name == "get_music_status":
                return self.music_controller.get_status(inputs.get("app"))
            elif name == "control_audio_output":
                return self._control_audio_output(
                    inputs.get("action"),
                    inputs.get("device")
                )
            elif name == "eucalyptus":
                return self._control_diffuser("eucalyptus", inputs.get("action"))
            elif name == "orange":
                return self._control_diffuser("orange", inputs.get("action"))
            elif name == "coffee":
                return self._control_coffee(inputs.get("action"))
            else:
                return f"Unknown tool: {name}"
        except Exception as e:
            print(f"[Alfred] Tool error: {e}")
            return f"Error: {e}"

    def _control_lights(self, action: str, target: str, value: str = None) -> str:
        """Execute a light control action."""
        lc = self.light_controller
        target_lower = target.lower() if target else ""

        if action == "on":
            if target_lower == "all":
                return lc.turn_all_on()
            return lc.turn_on(target)

        elif action == "off":
            if target_lower == "all":
                return lc.turn_all_off()
            return lc.turn_off(target)

        elif action == "brightness":
            brightness = int(value) if value else 100
            if target_lower == "all":
                return lc.set_all_brightness(brightness)
            return lc.set_brightness(target, brightness)

        elif action == "color":
            color = value or "white"
            if target_lower == "all":
                return lc.set_all_color(color)
            return lc.set_color(target, color)

        elif action == "warmth":
            warmth = value or "neutral"
            if target_lower == "all":
                return lc.set_all_color_temp(warmth)
            return lc.set_color_temp(target, warmth)

        return f"Unknown action: {action}"

    def _control_music(self, action: str, query: str = None, app: str = None) -> str:
        """Execute a music control action."""
        mc = self.music_controller

        if action == "play":
            if query:
                return mc.search_and_play(query, app)
            return mc.play(app)

        elif action == "pause":
            return mc.pause(app)

        elif action == "toggle":
            return mc.toggle_playback(app)

        elif action == "next":
            return mc.next_track(app)

        elif action == "previous":
            return mc.previous_track(app)

        elif action == "volume":
            if query:
                # Check for up/down
                if query.lower() in ["up", "louder", "higher"]:
                    return mc.adjust_volume("up")
                elif query.lower() in ["down", "lower", "quieter"]:
                    return mc.adjust_volume("down")
                # Otherwise treat as absolute level
                try:
                    level = int(query)
                    return mc.set_volume(level)
                except ValueError:
                    return f"Invalid volume: {query}. Use 'up', 'down', or 0-100"
            return mc.get_volume()

        elif action == "search":
            if query:
                return mc.search_and_play(query, app)
            return "Please specify what to search for"

        elif action == "playlist":
            if query:
                return mc.play_playlist(query, app)
            return "Please specify a playlist name"

        elif action == "shuffle":
            return mc.shuffle(True, app)

        return f"Unknown music action: {action}"

    def _control_audio_output(self, action: str, device: str = None) -> str:
        """Control system audio output device."""
        import platform
        import subprocess

        system = platform.system()

        if system == "Darwin":  # macOS
            if action == "current":
                result = subprocess.run(
                    ["SwitchAudioSource", "-c"],
                    capture_output=True, text=True
                )
                return f"Current audio output: {result.stdout.strip()}"

            elif action == "list":
                result = subprocess.run(
                    ["SwitchAudioSource", "-a", "-t", "output"],
                    capture_output=True, text=True
                )
                return f"Available outputs:\n{result.stdout.strip()}"

            elif action == "switch":
                if not device:
                    return "Please specify a device to switch to"
                result = subprocess.run(
                    ["SwitchAudioSource", "-s", device],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    return f"Switched audio output to: {device}"
                return f"Error switching to {device}: {result.stderr.strip()}"

        elif system == "Windows":
            # Audio device switching on Windows requires additional setup
            # User should set default audio device in Windows Sound settings
            if action == "current":
                return "Audio device info: Check Windows Sound settings"
            elif action == "list":
                return "Audio device list: Check Windows Sound settings"
            elif action == "switch":
                return "Audio switching on Windows: Please set default device in Windows Sound settings"

        return f"Unknown audio action: {action}"

    def _control_diffuser(self, scent: str, action: str) -> str:
        """Control a scent diffuser."""
        dc = self.diffuser_controller

        if action == "on":
            return dc.turn_on(scent)
        elif action == "off":
            return dc.turn_off(scent)
        elif action == "status":
            return dc.get_scent_info(scent)
        else:
            return f"Unknown diffuser action: {action}"

    def _control_coffee(self, action: str) -> str:
        """Control the coffee maker."""
        cc = self.coffee_controller

        if action == "brew":
            return cc.brew()
        elif action == "off":
            return cc.turn_off()
        elif action == "status":
            return cc.get_status()
        else:
            return f"Unknown coffee action: {action}"

    def _get_home_status(self) -> str:
        """Get combined home status."""
        parts = []

        # Light status
        parts.append("Lights:\n" + self.light_controller.get_detailed_status())

        # Door/presence status
        if self.home_context_provider:
            try:
                home_ctx = self.home_context_provider()
                parts.append("\nHome activity:\n" + home_ctx)
            except Exception as e:
                parts.append(f"\nHome activity: unavailable ({e})")

        return "\n".join(parts)

    def _build_system_prompt(self) -> str:
        """Build full system prompt with context. Loads prompt fresh each time for hot-reload."""
        prompt = _load_prompt("alfred")

        # Add current time
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
        prompt += f"\n<current_time>\n{time_str}\n</current_time>\n"

        # Add backstory
        backstory = get_backstory_context()
        if backstory:
            prompt += f"\n<your_history>\n{backstory}\n</your_history>\n"

        # Add user profile
        profile = get_profile_context()
        if profile:
            prompt += f"\n<what_you_know_about_them>\n{profile}\n</what_you_know_about_them>\n"

        # Add understanding
        try:
            consolidator = get_consolidator()
            consolidator.maybe_consolidate()
            understanding = get_understanding_context()
            if understanding:
                prompt += f"\n<your_understanding>\n{understanding}\n</your_understanding>\n"
        except Exception:
            pass

        # Add conversation history
        history = get_conversation_context()
        if history:
            prompt += f"\n<past_conversations>\n{history}\n</past_conversations>\n"

        # Add relationship context (people you know)
        relationships = get_relationships_context()
        if relationships:
            prompt += f"\n<people_you_know>\n{relationships}\n</people_you_know>\n"

        # Add pending clarifications about people
        try:
            graph = get_relationship_graph()
            clarification = graph.get_pending_clarification()
            if clarification:
                matches_desc = ", ".join(
                    f"{m['name']} ({m.get('relationship_type', 'unknown')})"
                    for m in clarification.get("matches", [])
                )
                prompt += f"\n<clarification_needed>\nYou heard about \"{clarification['name']}\" but there are multiple people with similar names: {matches_desc}. When natural, ask which one they mean.\n</clarification_needed>\n"
        except Exception:
            pass

        # Add home context
        if self.home_context_provider:
            try:
                home_context = self.home_context_provider()
                prompt += f"\n<current_home_state>\n{home_context}\n</current_home_state>\n"
            except Exception:
                pass

        # Add current light state
        try:
            light_state = self.light_controller.get_detailed_status()
            prompt += f"\n<current_lights>\n{light_state}\n</current_lights>\n"
        except Exception:
            pass

        # Knowledge gaps
        gap_prompt = get_knowledge_gap_context()
        if gap_prompt:
            prompt += f"\n<curiosity>\n{gap_prompt}\n</curiosity>\n"

        return prompt

    def save_conversation(self):
        """Save current conversation to memory."""
        if len(self.conversation_history) >= 2:
            store = get_conversation_store()
            store.store_conversation(self.conversation_history)
            return True
        return False

    def check_conversation_timeout(self):
        """Check if conversation timed out and save if so."""
        if not self.conversation_history:
            return
        if self.last_interaction_time == 0:
            return

        idle_time = time.time() - self.last_interaction_time
        if idle_time > self.conversation_timeout:
            print(f"[Alfred] Conversation idle for {idle_time:.0f}s, saving...")
            if self.save_conversation():
                self.conversation_history = []
                self.last_interaction_time = 0

    def clear_history(self):
        """Save and clear conversation history."""
        self.save_conversation()
        self.conversation_history = []
        print("[Alfred] Conversation history cleared")
