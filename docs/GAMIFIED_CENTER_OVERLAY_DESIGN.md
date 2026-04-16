# EchoNav — Gamified Center Overlay UI Design Document

## 1) Design Vision

Create a **compact, always-centered floating HUD (Heads-Up Display)** that stays in the middle of the screen as a **small intelligent control box**.

The UI should feel:

* **Accessible first** → optimized for low-vision and blind-assistive feedback workflows
* **Gamified** → task progress, action streaks, badges, confidence rings, smooth reward feedback
* **Minimal distraction** → never blocks too much screen content
* **Trustworthy** → clearly communicates what the AI is doing before any click happens
* **Premium futuristic** → polished like a game quest panel + AI assistant HUD

This is **not a full app window**. It is a **smart overlay card** that remains centered and adapts statefully.

---

## 2) Core UI Concept

The current strip/status UI should evolve into a **centered micro-dashboard widget**.

### Form Factor

A small floating card placed **dead center of the screen**.

### Suggested Dimensions

* **Idle state:** 420 × 220 px
* **Listening state:** 460 × 240 px
* **Thinking state:** 480 × 260 px
* **Expanded action preview:** 520 × 320 px

This keeps it:

* visually central
* non-intrusive
* large enough for readable feedback
* easy to focus on for low-vision users

### Placement

* exact screen center
* 90–95% opacity
* slightly blurred translucent backdrop
* soft glow aura to separate from busy backgrounds

---

## 3) UI Personality & Theme

## Theme Direction: "Parakeet-inspired Minimal Glass Overlay"

The UI should feel **friendly, calm, and highly legible**, inspired by the simplicity of modern voice assistants and the soft visual language associated with Parakeet-style AI interfaces.

### Visual Language

Focus on:

* clean accessibility-first utility
* soft glassmorphism
* rounded corners
* subtle motion only for state changes
* calm color transitions for trust

### Color System

Use a minimal translucent palette.

### Base Colors

* Background: frosted dark glass / soft smoke gray
* Border: soft white translucent edge
* Idle accent: muted blue-gray
* Listening accent: soft cyan
* Transcribing accent: violet-blue
* Executing accent: soft green
* Warning accent: warm amber
* Error accent: muted red

### State Color Rules

The card should mainly communicate state through border glow + top indicator color.

* Waiting → blue-gray
* Listening → cyan
* Transcribing → violet-blue
* Executing → green
* Warning → amber
* Error → red

This keeps the UI visually appealing without becoming distracting for blind and visually impaired users.

---

## 4) Layout Structure

The centered overlay should be a **single compact horizontal glass bar**, slightly larger than a normal taskbar widget.

### Suggested Dimensions

* compact width: 520–620 px
* height: 70–90 px
* fully rounded corners (pill / capsule shape)

This ensures:

* easy focus in the middle of screen
* minimal obstruction of content
* strong readability
* familiar lightweight presence

### Layout Zones

The bar should only have **3 simple zones**.

### A) Left Status Indicator

A small circular indicator.

This changes color by state:

* idle
* listening
* transcribing
* executing
* warning

Optional subtle pulse only while listening.

### B) Center Text Zone

Large readable live text.

This is the most important part.

Shows:

* waiting prompt
* live transcript
* current action status
* confirmation request

Examples:

* Ready
* Listening…
* Transcribing your request…
* Clicking Compose
* Awaiting confirmation

Typography should be:

* large
* semibold
* high contrast
* single line where possible

### C) Right Progress / Feedback Dot

A minimal progress visual.

This can be:

* spinner while transcribing
* check icon on success
* subtle waveform while listening

No cards, stacked panels, or heavy decorative sections.

The entire experience should feel like a **refined centered accessibility bar**.

## 5) Interaction States

The UI must be state-driven.

## State 1: Idle

Default compact centered card.

Shows:

* orb breathing
* "Ready for your next task"
* subtle hotkey hint

Purpose:
low cognitive load.

---

## State 2: Listening

Expand slightly.

Visuals:

* waveform ring
* real-time transcript preview
* cyan pulse border

Microcopy:

> Listening… tell me your next objective

---

## State 3: Interpreting

Replace transcript with parsed goal.

Example:

> Understood: Opening Chrome and searching weather

Show:

* intent confidence percentage
* route estimation ("~3 actions")

This creates trust.

---

## State 4: Thinking / Vision Analysis

The most cinematic state.

Display:

* rotating radar
* "Scanning current screen"
* detected UI landmarks
* button confidence

Possible micro labels:

* Primary CTA found
* Text field detected
* Safe action route mapped

---

## State 5: Action Preview

Before clicking, show a mini action card.

Example:

> Next Move: Click Compose button
> Confidence: 94%

For destructive actions:

* warning amber border
* explicit confirmation badge

---

## State 6: Success / Completed

Quick celebratory feedback.

Examples:

* checkmark pulse
* XP sparkle
* task progress increased
* success narration synced

Example text:

> Step complete. Moving to next objective.

---

## 6) Accessibility Feedback System

This section replaces all gamification with **clear functional feedback only**.

The UI should never use XP, streaks, tasks, badges, or reward language.
Instead, it should communicate only what the assistant is currently doing.

### Functional Feedback Types

* Ready
* Listening
* Transcribing
* Processing screen
* Executing action
* Awaiting confirmation
* Action complete
* Error encountered

### Feedback Principles

* concise wording
* single clear state at a time
* no decorative scoring systems
* no achievement concepts
* no unnecessary symbols
* always paired with voice narration

The purpose is reassurance and clarity for blind and visually impaired users, not engagement mechanics.

---

## 7) Accessibility Requirements

Since this is assistive-tech focused, accessibility must lead the design.

### Typography

* minimum 18 px body
* 24–28 px hero intent
* semibold minimum
* no thin fonts

### Contrast

WCAG AAA equivalent contrast.

### Motion

Animations must be:

* smooth
* slow enough for comprehension
* optionally reducible
* never seizure-risking

### Audio Pairing

Every visual state change must have:

* matching narration
* optional soft SFX cue
* haptic-style visual flash simulation

---

## 8) Advanced UI Enhancements

Optional premium features.

### A) Mini Screen Focus Indicator

When AI decides a click target:

* overlay draws a thin beam line from center HUD toward click area
* makes action direction visually obvious

### B) Action Timeline Drawer

Expandable bottom drawer:

* transcript
* AI decision
* executed action
* confidence
* undo possibility

### C) Badge Shelf

Tiny icons for:

* mic active
* online/offline
* model provider
* privacy mode
* redaction enabled

---

## 9) UX Rules

Strict rules to preserve usability.

### Must Do

* always centered
* never exceed 20% of screen width in compact mode
* collapse automatically after inactivity
* expand only during important actions

### Must Not Do

* never cover confirmation dialogs
* never block screen center during text-heavy reading mode
* never flash aggressively
* never use excessive particle effects

---

## 10) Suggested Final Experience

The ideal emotional experience should feel like:

> "A smart AI co-pilot giving me clear task progress while safely navigating my desktop."

The user should feel:

* in control
* rewarded
* safe
* informed
* futuristic

The UI should make the product feel **less like automation software and more like a trusted game-like navigator companion**.

---

## 11) MVP Design Scope

For version 1, prioritize:

* centered floating card
* animated orb
* 6 state transitions
* task progress strip
* action preview card
* confirmation warning theme

This is enough to dramatically outperform the current strip UI.

---

## 12) Future Evolution

Later versions can evolve into:

* adaptive HUD skins
* customizable themes
* achievement system
* voice avatar companion
* dynamic minimap of click targets
* "boss mode" for complex workflows

This keeps the gamified identity scalable.
