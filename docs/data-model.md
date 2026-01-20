# Alfred Memory Data Model

This document describes the data structures that power Alfred's memory and understanding.

---

## 1. User Profile (`data/user_profile.json`)

Stores facts Alfred learns about the user.

```json
{
  "name": "sir",

  "learned_facts": [
    {
      "id": "fact_001",
      "fact": "Works in technology",
      "confidence": 0.8,
      "source": "conversation 2026-01-20",
      "learned": "2026-01-20T10:30:00",
      "last_reinforced": "2026-01-22T14:00:00",
      "reinforcement_count": 2,
      "status": "active",
      "contradicts": []
    }
  ],

  "preferences": {
    "communication_style": {
      "value": "direct, minimal small talk",
      "confidence": 0.7,
      "source": "observed",
      "learned": "2026-01-20T10:30:00"
    }
  },

  "routines": {
    "weekday_departure": {
      "value": "typically leaves around 9:00am",
      "confidence": 0.6,
      "source": "door_pattern",
      "learned": "2026-01-20T10:30:00",
      "observation_count": 5
    }
  },

  "interests": ["technology", "building things"],

  "important_dates": {
    "birthday": "March 15"
  },

  "knowledge_gaps": [
    {
      "gap": "preferred_name",
      "question": "How would you like me to address you, sir?",
      "priority": "low",
      "asked": false
    }
  ]
}
```

### Fact Lifecycle

```
New fact learned (confidence: 0.7)
        │
        ▼
Time passes ──────► Decay: -0.1 confidence per week
        │
        ▼
Heard again? ─────► Reinforce: +0.2 confidence (max 1.0)
        │
        ▼
Confidence < 0.3? ► Mark as "faded" (excluded from prompts)
        │
        ▼
Confidence < 0.1? ► Mark as "forgotten" (can be pruned)
```

---

## 2. Patterns (`data/patterns.json`)

Behavioral patterns detected from door events and other sensors.

```json
{
  "door_patterns": [
    {
      "id": "pattern_001",
      "type": "recurring_departure",
      "description": "Leaves around 9am on weekdays",
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
      "time_range": {"start": "08:30", "end": "09:30"},
      "confidence": 0.7,
      "observations": 8,
      "first_observed": "2026-01-15",
      "last_observed": "2026-01-22",
      "promoted_to_routine": true
    }
  ],

  "activity_patterns": [
    {
      "id": "pattern_002",
      "type": "night_owl",
      "description": "Often active past midnight",
      "confidence": 0.6,
      "observations": 5
    }
  ]
}
```

### Pattern → Routine Promotion

```
5+ observations of same pattern
        │
        ▼
Confidence > 0.6?
        │
        ▼
Create routine in user_profile
        │
        ▼
Mark pattern as "promoted"
```

---

## 3. Conversations (`data/conversations.json`)

Already exists. Enhanced structure:

```json
{
  "conversations": [
    {
      "id": "conv_001",
      "date": "2026-01-20T10:30:00",
      "summary": "Discussed home automation setup preferences",
      "topics": ["home automation", "preferences"],
      "facts_learned": ["prefers minimal notifications"],
      "mood": "curious",
      "importance": "normal",
      "referenced_count": 0
    }
  ],

  "last_topics": ["home automation"],

  "pinned_conversations": []
}
```

### Conversation Importance Levels

- `trivial` - Small talk, greetings (auto-delete after 7 days)
- `normal` - Regular conversations (auto-delete after 30 days)
- `important` - Significant discussions (keep 90 days)
- `pinned` - Never auto-delete

---

## 4. Understanding (`data/understanding.json`)

Higher-level synthesis of all data. Updated periodically.

```json
{
  "last_consolidated": "2026-01-22T00:00:00",

  "personality_sketch": "A technical builder who values efficiency and directness. Prefers substance over pleasantries. Night owl tendencies. Curious and engaged when discussing projects.",

  "current_situation": "Working on a home automation project. Seems engaged and energetic about it.",

  "communication_notes": "Responds well to dry humor. Appreciates brevity. Dislikes unnecessary questions.",

  "themes": [
    {
      "theme": "building and creating",
      "evidence": ["interested in technology", "working on home automation", "asks technical questions"],
      "confidence": 0.85
    }
  ],

  "open_questions": [
    "What does he do for work specifically?",
    "Does he live alone?"
  ]
}
```

---

## Relationships Between Data

```
┌─────────────────────────────────────────────────────────────┐
│                        UNDERSTANDING                         │
│              (synthesized from everything)                   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ consolidation (weekly)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  USER PROFILE │◄───│   PATTERNS    │    │ CONVERSATIONS │
│    (facts)    │    │ (door events) │    │  (summaries)  │
└───────────────┘    └───────────────┘    └───────────────┘
        ▲                     ▲                     │
        │                     │                     │
        │  fact extraction    │ pattern detection   │
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                         raw events
```

---

## Decay & Reinforcement Constants

```python
CONFIDENCE_DECAY_PER_WEEK = 0.1
REINFORCEMENT_BOOST = 0.2
MAX_CONFIDENCE = 1.0
FADE_THRESHOLD = 0.3      # Below this, excluded from prompts
FORGET_THRESHOLD = 0.1    # Below this, can be pruned

PATTERN_PROMOTION_THRESHOLD = 5      # observations needed
PATTERN_CONFIDENCE_THRESHOLD = 0.6   # confidence to promote

CONVERSATION_RETENTION = {
    "trivial": 7,      # days
    "normal": 30,
    "important": 90,
    "pinned": float("inf")
}
```
