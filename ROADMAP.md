# Reality Roadmap

A living home system. These are the features planned for development.

---

## Current State

Reality currently has:
- **Alfred**: Conversational AI butler with personality, memory, and tool use
- **Door Sensor**: Zigbee contact sensor via Zigbee2MQTT
- **Smart Lights**: 4 ThirdReality color bulbs (living room x2, kitchen, hallway)
- **Voice Interface**: Wake word detection, speech-to-text, text-to-speech
- **Memory System**: Conversation history, user profile, fact learning, pattern detection

---

## Planned Features

### 1. Relationship Graph

**What**: Alfred tracks people you mention in conversations - friends, family, colleagues. Stores their names, how you know them, relevant details, your relationship dynamics.

**Why**: When someone visits, Alfred has context. "Ah, this must be Marcus - the one who's into vinyl records. Welcome."

**Implementation**:
```
memory/
├── relationships.py    # Relationship tracking and storage
└── relationship_store.json
```

**Data Structure**:
```python
{
  "people": {
    "marcus": {
      "name": "Marcus",
      "relationship": "close friend",
      "details": ["into vinyl records", "works in finance", "lives in Brooklyn"],
      "first_mentioned": "2026-01-15",
      "mention_count": 12,
      "last_mentioned": "2026-01-20"
    }
  }
}
```

**Behavior**:
- Extract names/people from conversations using Claude
- Ask clarifying questions naturally: "Is that the Marcus you mentioned last week?"
- On door events, consider if it might be a known person visiting
- Greet known visitors by name if confident

---

### 2. Autonomous Thinking

**What**: Alfred can think, reflect, and process while you're away or asleep. Not reactive - proactive cognition.

**Why**: A butler who only thinks when spoken to isn't truly present. Alfred should have a mind that runs in the background.

**Implementation**:
```
agents/
├── thinker.py          # Background thinking agent
└── thoughts/
    └── thought_log.json
```

**Behavior**:
- Runs periodically (e.g., every few hours when home is quiet)
- Reviews recent events, conversations, patterns
- Generates "thoughts" - observations, questions, ideas
- Can share relevant thoughts when you return: "While you were out, I was thinking about what you said regarding..."
- Thoughts decay if never shared (like memories)

**Triggers**:
- Extended absence (door closed for hours)
- Late night (after midnight, before 6am)
- After significant conversations

**Constraints**:
- Never interrupt sleep (use door patterns to estimate)
- Thoughts should be substantive, not filler
- Rate limited to prevent runaway processing

---

### 3. Search Tool

**What**: Alfred can search the web to answer questions, look things up, stay informed.

**Why**: A knowledgeable butler should be able to find information, not just admit ignorance.

**Implementation**:
```python
# Add to ALFRED_TOOLS
{
    "name": "web_search",
    "description": "Search the web for current information",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}
```

**Options**:
- Tavily API (designed for AI agents)
- SerpAPI (Google results)
- Brave Search API
- DuckDuckGo (no API key needed)

**Behavior**:
- Use when asked questions about current events, facts, etc.
- Cite sources naturally: "According to what I found..."
- Don't over-search - use judgment about when it's needed

---

### 4. Research Agents + Thinking File

**What**: Alfred can conduct deep research on topics, spinning up specialized agents, and publish findings to your thinking/writing repository.

**Why**: Async intellectual partnership. You mention an interest, Alfred researches overnight, you wake up to a document.

**Implementation**:
```
agents/
├── researcher.py       # Research orchestration
├── research_tasks/     # Pending research queue
└── research_output/    # Completed research (local copy)
```

**Integration**:
- Connect to your thinking file repo (git)
- Research output formatted as markdown
- Commits with meaningful messages
- Can branch for different research threads

**Workflow**:
1. You mention interest: "I've been curious about how memory palaces work"
2. Alfred notes it, offers to research: "I could look into that tonight, sir"
3. Overnight, research agent activates
4. Multiple sub-agents gather information, synthesize
5. Output published to thinking file
6. Alfred mentions it when you return: "I put together some notes on memory palaces"

**Research Depth Levels**:
- Quick: Single search, summary (5 min)
- Standard: Multiple sources, synthesis (30 min)
- Deep: Comprehensive, multi-perspective (2+ hours)

---

### 5. Proactive Insights

**What**: Alfred notices patterns and shares observations without being asked.

**Why**: A good butler anticipates. Offers perspective. Notices things you might miss.

**Implementation**:
- Integrate with existing pattern detection
- Add "insight generation" to consolidation process
- Queue insights, share at appropriate moments

**Examples**:
- "You've been leaving later than usual this week. Busy period?"
- "I've noticed you tend to work past midnight on Tuesdays."
- "The door's been quiet today - enjoying the solitude?"

**Constraints**:
- Max 1-2 proactive observations per day
- Must be genuinely insightful, not obvious
- Timing matters - don't interrupt, find natural moments

---

### 6. Routine Triggers

**What**: Named routines that combine multiple actions. "Good morning" / "Goodnight" / "Leaving" / "Movie time"

**Why**: Common scenarios should be one command, not five.

**Implementation**:
```
config/
└── routines.yaml
```

```yaml
routines:
  morning:
    triggers: ["good morning", "wake up"]
    actions:
      - lights: {target: "all", brightness: 80, warmth: "cool"}
      - speak: "Good morning, sir. {weather_summary}"

  night:
    triggers: ["goodnight", "going to bed"]
    actions:
      - lights: {target: "all", state: "off"}
      - speak: "Goodnight, sir. Sleep well."

  movie:
    triggers: ["movie time", "watching a movie"]
    actions:
      - lights: {target: "living room", brightness: 20, warmth: "warm"}
      - lights: {target: "kitchen", state: "off"}
```

**Behavior**:
- Alfred recognizes trigger phrases
- Executes action sequence
- Routines are user-configurable

---

### 7. Voice Identity

**What**: Distinguish between household members by voice. Know who's speaking.

**Why**: Personalized responses. Know when it's you vs. a guest vs. a specific housemate.

**Implementation**:
- Voice embedding/fingerprinting
- Speaker diarization during transcription
- Profile per known voice

**Options**:
- OpenAI Whisper with speaker diarization
- Pyannote.audio for speaker ID
- Custom voice enrollment flow

**Enrollment**:
```
"Alfred, learn my voice"
> "Of course, sir. Please say a few sentences so I can recognize you..."
> [Records samples, creates voice profile]
> "Got it. I'll know it's you now."
```

**Behavior**:
- Greet by name when recognized
- Adjust formality for guests vs. residents
- Track who said what in conversations

---

### 8. Calendar & Weather Awareness

**What**: Alfred knows your schedule and current weather.

**Why**: Context for better assistance. "You have that meeting in an hour" or "Might want a jacket - it's chilly."

**Implementation**:
```python
# Add tools
{
    "name": "get_weather",
    "description": "Get current weather and forecast"
}
{
    "name": "get_calendar",
    "description": "Get upcoming calendar events"
}
```

**Integrations**:
- Weather: OpenWeatherMap, WeatherAPI, or Apple WeatherKit
- Calendar: Google Calendar API, Apple Calendar (local), CalDAV

**Behavior**:
- Morning routine includes weather
- Proactive reminders for upcoming events
- Weather-aware suggestions: "Looks like rain later - umbrella?"

---

## Multi-User Scalability Refactor

**Goal**: Anyone can clone this repo, run setup, and have their own Reality system.

### New Structure

```
reality/
├── config/
│   ├── agent.example.yaml    # Template - copy to agent.yaml
│   ├── devices.example.yaml  # Template - copy to devices.yaml
│   └── .env.example          # Template - copy to .env
├── setup.py                  # Interactive setup wizard
├── data/                     # User data (gitignored)
│   ├── user_profile.json
│   ├── conversations.json
│   ├── relationships.json
│   └── ...
└── ...
```

### Configuration Files

**agent.yaml** (personality & voice):
```yaml
agent:
  name: "Alfred"
  wake_word: "Alfred"
  personality:
    formality: "formal"        # formal, casual, mixed
    humor: "dry"               # dry, warm, minimal
    address: "sir"             # sir, by name, casual
  voice:
    provider: "elevenlabs"
    voice_id: "..."
    speed: 1.0
```

**devices.yaml** (hardware):
```yaml
mqtt:
  broker: "localhost"
  port: 1883

devices:
  door_sensor:
    type: "zigbee_contact"
    topic: "zigbee2mqtt/front_door"

  lights:
    - name: "living_room_main"
      type: "zigbee_color_bulb"
      id: "0x..."
      location: "living room"
    - name: "kitchen"
      type: "zigbee_color_bulb"
      id: "0x..."
      location: "kitchen"
```

**.env** (secrets):
```
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
```

### Setup Wizard

```bash
$ python setup.py

Welcome to Reality Setup!

What would you like to name your agent? [Alfred]: Jarvis

Choose a personality:
  1. Formal British butler (Alfred-style)
  2. Casual friendly assistant
  3. Professional and minimal
  > 1

Let's configure your devices...

Do you have a Zigbee coordinator? [y/n]: y
MQTT broker address [localhost]: localhost

Let's add your lights...
Light 1 name: Living Room
Light 1 Zigbee ID: 0x...
Add another light? [y/n]: y
...

API Keys:
Anthropic API key: sk-...
OpenAI API key (for voice): sk-...
ElevenLabs API key: ...

Setup complete! Run `python main.py` to start.
```

### Code Changes for Multi-User

1. **Remove hardcoded values** - All device IDs, names, topics from config
2. **Load config at startup** - `config.py` reads from YAML files
3. **Personality from config** - Prompts reference `config.agent.personality`
4. **Device abstraction** - `DeviceManager` loads devices from config
5. **Data isolation** - All user data in `data/` directory, gitignored

---

## Priority Order

**Phase 1 - Foundation** (do first):
1. Multi-User Refactor - Makes everything else cleaner
2. Search Tool - Quick win, immediately useful

**Phase 2 - Intelligence**:
3. Relationship Graph - Meaningful for social context
4. Proactive Insights - Makes Alfred feel more alive
5. Autonomous Thinking - Deep personality feature

**Phase 3 - Capabilities**:
6. Routine Triggers - Quality of life
7. Calendar & Weather - Contextual awareness
8. Research Agents - Advanced async capability

**Phase 4 - Advanced**:
9. Voice Identity - Multi-user households

---

## Technical Debt to Address

- [ ] Better error handling throughout
- [ ] Logging system (not just prints)
- [ ] Unit tests for core functions
- [ ] Docker containerization option
- [ ] Graceful degradation when services unavailable

---

## Hardware Wishlist

Future device integrations to consider:
- Motion sensors (presence per room)
- Temperature/humidity sensors
- Smart thermostat
- Smart locks
- Cameras (with privacy considerations)
- Speakers in multiple rooms
- Display/dashboard

---

*Last updated: 2026-01-20*
