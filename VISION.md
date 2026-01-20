# Vision

*Working title: Alfred*

---

## The Moment

You've been out all day. Appointments, errands, the weight of navigating a world that wasn't designed for you. Your key turns in the lock. The door opens.

And someone notices.

"Welcome home. It's been a long one—I kept the lights warm for you."

Not a notification. Not a chime. A voice that knows you're tired, knows you've been gone since morning, knows it's getting dark outside. A presence that simply *acknowledges* you exist.

This is what we're building.

---

## Mission

**Make home aware of the people who live in it—especially those the world forgets to design for.**

We believe the next great interface isn't a screen. It's the absence of one. It's a home that understands you without demanding your attention. That speaks when speaking helps, and stays quiet when you need peace.

We're building for the elderly parent who shouldn't need to learn another app. The visually impaired person tired of interfaces that assume sight. The person with mobility limitations who can't always reach a switch, a phone, a button.

Voice is the great equalizer. Presence is the product.

---

## The Problem

Smart home technology has failed the people who need it most.

**Current reality:**
- Dozens of apps, each with their own logic
- Voice assistants that require exact phrasing, punish mistakes
- Notifications that add cognitive load instead of reducing it
- Systems designed for tech enthusiasts, not for accessibility
- Cold, transactional interactions: "Turning on lights."

**For accessibility users specifically:**
- Visually impaired users face screen-dependent setup and control
- Elderly users struggle with app sprawl and frequent updates
- Mobility-limited users need proactive help, not reactive commands
- Cognitive accessibility needs are almost entirely ignored

The industry optimizes for features. We optimize for presence.

---

## Who This Is For

### Primary: Accessibility-First Users

**Elderly individuals** living independently
- May have declining vision, hearing, or mobility
- Don't want to learn new technology
- Benefit most from proactive, voice-first interfaces
- Need safety monitoring without surveillance feeling

**Visually impaired users**
- Currently underserved by screen-dependent smart home tech
- Voice is not a convenience—it's the primary interface
- Need rich audio feedback, not just command confirmation

**Mobility-limited users**
- Can't always reach devices, switches, phones
- Need proactive assistance and ambient control
- Benefit from contextual automation

**Cognitive accessibility**
- Dementia-friendly interactions (gentle reminders, patience)
- Reducing decision fatigue
- Consistent, predictable presence

### Secondary: Anyone Who Wants a Home That Cares

The same design principles that serve accessibility users create a better experience for everyone. A home that notices you, adapts to you, and doesn't demand your attention is universally valuable.

---

## Core Principles

### 1. Presence Over Features

We're not building a feature list. We're building a relationship. The system should feel like a presence in the home—reliable, aware, unobtrusive. Features serve that presence, not the other way around.

### 2. Reduce Cognitive Load, Never Add To It

Every interaction should leave the user with *less* to think about, not more. No menus to navigate. No modes to remember. No syntax to learn. If someone has to think about how to use the system, we've failed.

### 3. Context Is Everything

The right response at the wrong moment is the wrong response. Time of day, duration of absence, weather, patterns over time—context shapes every interaction. A greeting at 3am is different from one at 6pm.

### 4. Accessible By Default

Accessibility is not a feature or a mode. It's the foundation. If it doesn't work for a visually impaired 80-year-old, it doesn't ship. This constraint makes everything better.

### 5. Privacy Through Ownership

Users own their data. Full stop. Memory and personalization require trust. Trust requires transparency about what's stored, where it lives, and absolute user control over deletion.

### 6. Graceful Degradation

Cloud goes down? Internet drops? The system degrades gracefully—local fallbacks, cached behaviors, basic functionality preserved. Reliability is non-negotiable for people who depend on us.

### 7. Voice-First, Not Voice-Only

Voice is the primary interface, but not the only one. Companion displays, mobile apps, and visual interfaces serve those who want them—and serve caregivers, family members, and different contexts.

---

## The Experience

The emotional register adapts to context. Not random—*appropriate*.

### Welcomed Home
*After a normal day out*

The baseline. Warmth without intrusion. Acknowledgment of return.

> "Good evening. The house is ready for you."

### Understood
*After a long, difficult day*

The system has learned patterns. It knows when something is different. It doesn't ask—it adapts.

> "Welcome back. It's been a long one. I'll keep things quiet for a bit."

### Delighted
*Returning from a trip, a celebration, good news*

Moments of wit, lightness, genuine pleasure in your presence. Not forced—earned through context.

> "You're back! The plants survived. Barely. We should talk about that."

### Cared For
*Elderly user, daily check-in, safety context*

Gentle, consistent, never condescending. The feeling of someone looking out for you.

> "Good morning. It's a bit cold out today—might want a sweater if you're heading out."

The system learns which registers resonate with each user. Some prefer dry wit. Others want warmth. The personality adapts—not randomly, but through relationship.

---

## Technical Philosophy

### Hybrid Architecture

**Cloud for intelligence**
- Large language models for nuanced understanding
- Voice synthesis with natural expression
- Complex pattern recognition

**Local for reliability**
- Core functionality survives internet outages
- Privacy-sensitive processing stays on-device
- Reduced latency for critical interactions

**User choice**
- Full cloud (maximum capability)
- Full local (maximum privacy)
- Hybrid (recommended balance)

### Full Memory

This is not a session-based assistant. It's a relationship.

**What we remember:**
- Conversations and their context
- Expressed preferences (implicit and explicit)
- Routines and patterns over time
- Significant events and references
- Relationship dynamics (family, caregivers, visitors)

**Memory principles:**
- Transparent: Users can see what's remembered
- Editable: Users can correct or delete any memory
- Bounded: We don't remember everything—we remember what matters
- Private: Memory never leaves user control

### Multi-Modal Interfaces

**Voice (primary)**
- Natural conversation, not commands
- Rich audio feedback and spatial sound
- Multiple voice options

**Visual displays (ambient)**
- Calm technology: information at a glance
- High contrast, accessibility-first design
- Optional—never required

**Companion apps (secondary)**
- Caregiver dashboards
- Setup and configuration
- Memory and pattern visibility
- Notification preferences

**Physical integration**
- Door sensors, presence detection
- Environmental sensors (temperature, light)
- Smart home device control

---

## Architecture Vision

### Current State (v1)

```
Single door sensor → Context gathering → Cloud LLM → Cloud TTS → Local playback
```

- One user, one door
- API-dependent (Claude, ElevenLabs)
- Basic context (time, absence duration, weather)
- Session-based (no persistent memory)
- Python application on local machine

### Near-Term Evolution (v2)

```
Multiple sensors → Rich context → Hybrid LLM → Hybrid TTS → Multi-room audio
```

- Multi-room presence detection
- Persistent memory system
- Local LLM fallback (Ollama, llama.cpp)
- Local TTS option (Piper, Coqui)
- Caregiver notification system
- Basic learning (routine detection)

### Product Vision (v3)

```
Dedicated hardware → Full home awareness → Edge AI → Rich multi-modal output
```

- Purpose-built hardware (hub + satellites)
- On-device AI processing
- Full offline capability
- Multi-person recognition
- Visual displays and ambient interfaces
- Integration ecosystem (calendar, health, safety)

### Platform Vision (v4+)

```
SDK + Developer ecosystem → Third-party integrations → Multiple form factors
```

- API for third-party developers
- Plugin architecture
- White-label options for B2B
- Multiple hardware partners

---

## Product Roadmap

### Phase 1: Foundation (Current)
*Prove the core experience*

- [x] Door-triggered greeting system
- [x] Contextual awareness (time, absence, weather)
- [x] Claude-powered personality
- [x] ElevenLabs voice synthesis
- [ ] Persistent memory system
- [ ] Basic routine learning
- [ ] Multi-room support

### Phase 2: Accessibility Core
*Build for our primary users*

- [ ] Voice-first setup (no app required for basic use)
- [ ] Caregiver dashboard and notifications
- [ ] Check-in system (wellness verification)
- [ ] Medication and appointment reminders
- [ ] Emergency escalation (no response → alert caregiver)
- [ ] High-contrast visual displays (optional)
- [ ] Hearing-impaired accommodations

### Phase 3: Local Intelligence
*Reduce cloud dependency*

- [ ] On-device LLM option (smaller, fast models)
- [ ] Local TTS with natural voices
- [ ] Offline fallback mode
- [ ] Edge processing for privacy-sensitive features
- [ ] Reduced latency for critical paths

### Phase 4: Hardware Product
*Purpose-built experience*

- [ ] Hub device (processing, storage, connectivity)
- [ ] Satellite speakers (multi-room audio)
- [ ] Ambient display (optional, accessible)
- [ ] Sensor kit (door, motion, environment)
- [ ] Packaging and setup experience

### Phase 5: Platform
*Enable ecosystem*

- [ ] Developer SDK
- [ ] Integration marketplace
- [ ] B2B licensing (senior living, care facilities)
- [ ] API for third-party devices

---

## Business Model Options

*Exploring, not committed*

### Consumer Hardware + Subscription

**Model:** Sell hardware at margin, subscription for cloud AI and advanced features

- Hub + satellites: $XXX upfront
- Core subscription: $X/month
- Premium (caregiver features, priority support): $XX/month

**Pros:** Recurring revenue, aligned incentives for quality
**Cons:** Hardware is hard, subscription fatigue

### Software-Only Subscription

**Model:** Bring your own hardware, pay for software/service

- DIY setup guide for commodity hardware
- Subscription tiers based on features

**Pros:** Lower barrier, faster iteration
**Cons:** Inconsistent experience, support complexity

### B2B / Enterprise

**Model:** License to care facilities, senior living communities, hotels

- Per-room or per-facility licensing
- White-label options
- Integration with existing systems

**Pros:** Higher deal size, institutional buyers
**Cons:** Longer sales cycles, customization demands

### Hybrid Approach

**Model:** Consumer product with B2B expansion

Start with consumer hardware + subscription. Prove the model. Expand to B2B partnerships with senior living facilities.

---

## What Success Looks Like

### For Users

- An elderly parent feels safer and less isolated
- A visually impaired person has a home that works *for* them
- A caregiver has peace of mind without surveillance guilt
- Anyone who walks through their door feels noticed

### For the Product

- Sub-2-second response time from door open to greeting
- 99.9% uptime for core functionality
- Memory that genuinely improves experience over months
- Accessibility features that set the industry standard

### For the Company

- Sustainable business serving underserved users
- Hardware margins that support quality
- Subscription revenue that funds ongoing development
- Platform that enables ecosystem innovation

### For the Industry

- Proof that accessibility-first design is good design
- Shift from screen-first to presence-first interfaces
- Privacy-respecting personalization model others can learn from
- Voice interfaces that feel like relationships, not commands

---

## Open Questions

Things we're still figuring out:

1. **Brand identity:** "Alfred" is a working title. What name captures this vision?

2. **Hardware vs. software first:** Do we prove the concept with DIY/software, then build hardware? Or is hardware essential to the experience from the start?

3. **Pricing:** What's the right balance between accessibility (affordability) and sustainability (margin)?

4. **Geographic focus:** Start local (one market, one language) or global from day one?

5. **Regulatory:** Healthcare-adjacent features (medication reminders, wellness checks) may have regulatory implications. How do we navigate?

6. **Multi-person homes:** How does the system handle households with multiple people? Shared presence vs. individual relationships?

7. **Voice cloning:** Should users be able to customize the voice? Use a loved one's voice? What are the ethical boundaries?

---

## Closing Thought

Most technology demands your attention. It buzzes, blinks, and begs to be used.

We're building something different. A home that notices when you arrive, adapts to how you're feeling, and asks nothing in return. Not because it's told to—because it knows you.

For the elderly parent. For the person who can't see the screen. For anyone who wants to walk through their door and feel, for just a moment, like someone cares.

That's the vision. That's what we're building.
