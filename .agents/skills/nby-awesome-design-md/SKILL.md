---
name: nby-awesome-design-md
version: 0.1.0
description: Apply real-world design systems to your project via DESIGN.md. Trigger when user says "use Stripe design", "apply Notion style", "DESIGN.md", "design system", "用 Stripe 风格", "应用 Linear 设计", "套用设计系统", or names any supported brand (Stripe, Vercel, Linear, Notion, Figma, Spotify, Airbnb, Apple, etc.) in a UI/frontend context. Sources design tokens, colors, typography, components, and layout rules from VoltAgent/awesome-design-md.
---

# Awesome Design MD

Apply pixel-accurate design systems from 54 real-world websites to any project. Powered by [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md).

## Language

Match the user's language.

## Available Design Systems

### AI & ML
`claude` `cohere` `elevenlabs` `minimax` `mistral.ai` `ollama` `opencode.ai` `replicate` `runwayml` `together.ai` `voltagent` `x.ai`

### Developer Tools
`cursor` `expo` `linear.app` `lovable` `mintlify` `posthog` `raycast` `resend` `sentry` `supabase` `superhuman` `vercel` `warp` `zapier`

### Infrastructure & Cloud
`clickhouse` `composio` `hashicorp` `mongodb` `sanity` `stripe`

### Design & Productivity
`airtable` `cal` `clay` `figma` `framer` `intercom` `miro` `notion` `pinterest` `webflow`

### Fintech
`coinbase` `kraken` `revolut` `wise`

### Enterprise & Consumer
`airbnb` `apple` `bmw` `ibm` `nvidia` `spacex` `spotify` `uber`

## Workflow

### Step 1: Ensure Local Cache

Clone the repo once, reuse on subsequent runs.

```bash
REPO_DIR="$HOME/.nby-skills/nby-awesome-design-md/repo"

if [ -d "$REPO_DIR/.git" ]; then
  echo "Cache exists, pulling latest..."
  cd "$REPO_DIR" && git pull --ff-only 2>/dev/null || true
else
  echo "First run, cloning..."
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone --depth 1 https://github.com/VoltAgent/awesome-design-md.git "$REPO_DIR"
fi
```

### Step 2: Identify Target Design

If the user specifies a brand name, map it to the directory slug (e.g., "Linear" -> `linear.app`, "xAI" -> `x.ai`). If unclear, list available designs and ask.

To list all available designs:
```bash
ls "$HOME/.nby-skills/nby-awesome-design-md/repo/design-md/"
```

### Step 3: Apply DESIGN.md

Copy the chosen DESIGN.md to the project root:

```bash
BRAND="stripe"  # replace with user's choice
cp "$HOME/.nby-skills/nby-awesome-design-md/repo/design-md/$BRAND/DESIGN.md" ./DESIGN.md
```

If a `DESIGN.md` already exists in the project root, warn the user before overwriting.

### Step 4: Confirm and Guide

After placing DESIGN.md:

1. Briefly summarize the design system's key characteristics (2-3 lines: primary colors, font, vibe)
2. Inform the user that DESIGN.md is now in the project root
3. Proceed with UI generation if the user has a specific request, referencing DESIGN.md for all design decisions

## Rules

- Always read the applied DESIGN.md before generating any UI code — use it as the single source of truth for colors, typography, spacing, components, and layout.
- Never hardcode design values without checking DESIGN.md first.
- If the user wants to mix styles from multiple brands, copy one as the base and note which elements come from elsewhere.
- When generating components, reference the exact color hex values, font families, border-radius, and shadow values from DESIGN.md.
