# BRAND_KIT — Asset Intelligence by Manage Assets Inc.
**For:** Muse Code, Cursor, frontend agents — aligned to DESIGN.md v1.1 2026-10-29 verified `5a83c3e`
**Parent:** ManageAssets.net — Infrastructure Intelligence For The Real World
**Product:** Asset Intelligence — AI Field Evidence Intelligence Platform
**Version:** 2.1 — Aligned to DESIGN.md v1.1; marketing/ paths current as of 2026-10-29 reorg
**Owner:** Manage Assets Inc. / Monica Peters
**Status:** VERIFIED vs repo on 2026-10-29. Proposals labeled PROPOSAL, owner calls labeled OWNER DECISION.

> This kit is law for logos and brand tokens, but it does NOT override DESIGN.md stack facts. Where parent brand says Inter/Tailwind, DESIGN.md's verified system-stack + plain CSS wins until OWNER DECISION.

---

## 01 — What changed from 2026-10-26 ungrounded brand kit

- **Stack correction:** Old kit prescribed Tailwind + `index.css` + `tailwind.config.js` + Inter + JetBrains Mono CDN. Verified reality: `app/ui/src/styles.css` CSS variables only, components `.jsx`, system font stack, no Tailwind, no TS, no webfonts. This kit now uses `styles.css` tokens only.
- **Pipeline correction:** Old kit described Llama 4 Maverick fusion. Verified: no Llama model on live Meta API. Vision is `muse-spark-1.3` primary + fallback, reasoning Spark 1.3, planning `muse-wonder-1.0` (ARCH §4.3).
- **Logo correction:** Old kit invented “slate blue #1E3A5F primary” and M+A+Peaks from `brand_kit.png` as UI primary. Verified: UI primary is blue `#1d4ed8`, logo in `marketing/manage_assets_inc/logo.png|.svg` is angular M mark dark slate + green (~`#5BBC7A`) + thin red edge lines. `brand_kit.png` (3.8 MB, parent set — content extracted in §02).
- **What is kept from old kit and parent:** Forest green meaning growth, Lake blue trust, Stone strength, Fog balance, Sand people. M+A construction, Industrial Forensic Ledger direction, evidence-tether signature.

---

## 02 — Parent Brand — ManageAssets.net (verified from your uploads)

Extracted from `marketing/manage_assets_inc/brand_kit.png` (parent set + PDF):

- **Mark construction (from 02 Logo Construction):** M = Manage (Stone #222B32 dark) + A = Assets (Forest #5CB176 / #5BBC7A green) + Peaks = Infrastructure (Stone + Fog + Forest). Tagline: Infrastructure intelligence for the real world. Essence: Real assets. Brighter communities. Manifesto: Land. People. Assets. Stronger together.
- **Sampled palette from 05 Colour System (coordinates 377,438,500,562,624 / 466):**
  - Forest Growth #59AA71 sampled → **#5CB176 official / ~#5BBC7A marketing** — Growth Communities
  - Lake Trust #4380B2 — Trust Stability
  - Stone Strength #222B32 sampled → #1A242E deep / #0E1619 dark bg — Strength Infrastructure
  - Fog Balance #B5B5B5 sampled → #C7C9CA polished → #D4D4D8 border — Balance Clarity
  - Sand People #F1F0EC sampled → #F2F0EB polished — People Places
  - Typography per 06: Inter — Clean. Modern. Reliable.
  - Visual Direction 08: field worker in hi-vis vest overlooking lake/mountains, sustainable resilient communities.
  - System Details 09: Chips Inspection (location), Needs Review (doc), Approved (check Forest), Uncertain (AI) (warning).

**Parent usage:** Business cards, web app mock (Assets/Inspections/Maintenance/Reports left rail dark Stone #0E1619 active white).

---

## 03 — Verified Reality — Asset Intelligence repo `5a83c3e`

**Brand (verified, `marketing/` tracked since 2026-10-29):**
- `marketing/manage_assets_inc/logo.png` (+`.svg`, `logo1–3.png`, `brand_kit.png`): angular “M” mark, dark slate left facet, green right facet (~`#5BBC7A`), thin red edge lines.
- `marketing/asset_intelligence_*`: product set — `final_simple_logo_{light,dark}.png` duotone lockups with byline, `lockup_light.png`, `icon_ai.png`, `simple_icon.png`, plus `manageassets_icon_{light,dark}_transparent.png` parent cuts.
- Simple icon generated to match description (dark slate + green + thin red): `manage_assets_m_mark_red_edge.png` [MISSING — not in marketing/ as of 2026-10-29] — see Simple Logo section.

**UI today (verified, `styles.css`):**
```css
--bg: #ffffff; --panel: #f4f4f5; --border: #d4d4d8;
--text: #18181b; --muted: #52525b; --accent: #1d4ed8;
--warn: #b45309; --radius: 6px;
system font stack, 14px body
```
Flat 6px-radius panels, four tabs (Demo / New inspection / About / Insights), Accept/Reject under “Human review (required)”, keyboard-operable evidence chips, SAM overlay label-colored fills 35% + 3px bbox strokes + 5px white halo when selected, `role="img"` + label, tablist ARIA + `:focus-visible`.

**OWNER DECISION (blocking rebrand):**
Reconcile UI blue `#1d4ed8` with logo green `#5BBC7A`. Options:
(a) Keep blue UI + monochrome logo usage in header (safest — keeps current tokens);
(b) Migrate primary actions to logo green `#5BBC7A` (requires contrast audit);
(c) Slate-ink chrome with green reserved for “verified/accept” semantics (Forest for Approved only).
Do not mix blue CTAs and green CTAs without deciding.

---

## 04 — Sub-Brand — Asset Intelligence (PROPOSAL, aligned to verified DESIGN.md)

**Sub-brand architecture:** Asset Intelligence is product of Manage Assets Inc. Inherits parent M mark, adds intelligence layer.

**Logo system (PROPOSAL, pending OWNER DECISION on canonical file):**

1. **Primary Icon — Parent Exact (trust, PROPOSAL):** Use parent M+A Peaks unchanged for municipal trust. File: `marketing/manageassets_icon_light_transparent.png` (exact parent cut) + `manage_assets_m_mark_red_edge.png` [MISSING — not in marketing/ as of 2026-10-29] (M with red hairline).

2. **AI Variant — Peaks + Lake Accent (for product UI, PROPOSAL):** Left peak Stone #1A242E, middle Fog #4A5A67, right Forest #5BBC7A, small Lake #4380B2 triangle at overlap = AI layer. File: `asset_intelligence_icon_ai.png`. Use in SAM loader, model trace footer.

3. **Wordmark — Asset Intelligence (PROPOSAL, system font until brand commit):** Until OWNER DECISION, header keeps text wordmark per DESIGN.md: “Asset Intelligence • by ManageAssets.ca”. When brand commits, Inter 600, Asset Stone #18181b, Intelligence Forest #5BBC7A. File: `asset_intelligence_wordmark.png` [MISSING — not in marketing/ as of 2026-10-29] (for docs, not UI until decision).

4. **Lockup Light/Dark (PROPOSAL, for README/deck, not UI):** `asset_intelligence_lockup_light.png`, `asset_intelligence_lockup_dark.png` [MISSING], `asset_intelligence_final_simple_logo_light.png`, `asset_intelligence_final_simple_logo_dark.png`. Use in README header, pitch deck, video intro — NOT in UI until OWNER DECISION says logo in UI.

**Usage rules (from parent 02, aligned to verified):**
- Min clear space 1x peak height, min size Icon 24px, Lockup 120px wide.
- Never stretch, never add drop shadow, never recolor Forest to lime or purple-indigo gradient.
- On field photos, use white container 4px radius (verified `--radius: 6px` but 4px for icon container) + 1px Fog border.
- For Asset Intelligence outside product, include “by ManageAssets.ca” 10px system uppercase tracking 0.08em below lockup when used (matches DESIGN.md header pattern).
- Until OWNER DECISION: no logo in UI, text wordmark stays per DESIGN.md “Brand commit” item.

---

## 05 — Colour Tokens — Aligned to `styles.css` (verified + proposed)

**Do not rename existing tokens without migration (DESIGN.md law). Edit `styles.css` `:root` only.**

Current (verified):
```
--bg #ffffff, --panel #f4f4f5, --border #d4d4d8,
--text #18181b, --muted #52525b, --accent #1d4ed8,
--warn #b45309, --radius 6px
```

PROPOSAL additions (each needs C.1 contrast audit per DESIGN.md, do not assert ratios):
```
--alert: #ffc93a   /* tape yellow — missing chips — verify pairing */
--discrepancy: #c43a31  /* rust — banner — verify pairing */
--mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
--forest: #5BBC7A  /* logo green — PROPOSAL, pending OWNER DECISION */
--stone-deep: #0E1619 /* for dark header variant — from parent 01 LOGO bg */
```

**Parent to verified mapping (for future OWNER DECISION):**
- Parent Forest #5CB176 / #5BBC7A → maps to PROPOSAL --forest, reserved for Approved/verified per option (c) or primary per option (b).
- Parent Lake #4380B2 → maps to info/discrepancy detail links (PROPOSAL).
- Parent Stone #222B32 → maps to verified --text #18181b is close enough (keep #18181b until decision).
- Parent Fog #B5B5B5 → maps to verified --border #d4d4d8 / --muted #52525b.
- Parent Sand #F1F0EC → not used today (bg is #ffffff), optional blueprint grid uses --panel #f4f4f5.

Accessibility: Never use Forest #5BBC7A on white for 13px body until axe passes. Use only for icons, 18px+ bold “Intelligence”, borders, Approved check. Body stays #18181b.

---

## 06 — Typography — System Stack (verified decision, reverses old draft)

**DESIGN.md law:** System stack stays. No Inter/Roboto-as-personality (currently system stack — fine). Old draft prescribed Fragment Mono + General Sans + JetBrains Mono via CDN — rejected as default: external fonts cost bundle weight, break offline demos, raise municipal IT consent questions.

- **Body / Observations:** system-ui (today) 14px, line-height 1.55, max 62ch. Readable at 13px truck-cab sunlight per DESIGN.md.
- **Utility / Evidence Refs (PROPOSAL):** `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` 11px uppercase tracking 0.06em for `mask_id`, `span: [0,45]`, `cost_cents`, `model_trace: sam-3.1 • spark-1.3 • wonder`. Adds forensic distinction, zero downloads, network tab clean.
- **Display / Lockup (OPTIONAL phase, owner call):** Self-hosted display face for header/asset-ID only, subset latin, preloaded, system fallback. Never render-blocking CDN.

Parent Inter is documented but not used in UI until OWNER DECISION.

**Copy Voice (from parent + verified microcopy):**
- Parent tagline: Infrastructure intelligence for the real world.
- Product: Real assets. Brighter communities. Assets into action.
- Verified microcopy (keep): “Human review (required)”, Accept/Reject, “Review is disabled in demo mode.”
- PROPOSAL microcopy per DESIGN.md: “Inspection intelligence — evidence linked”, “3 masks · 2 discrepancies · 2 missing — review in 15 seconds”, “crack · SAM 0.87 — requires human measurement”, “Does not certify safety. Requires qualified inspection.”

---

## 07 — Simple Logo — Production Ready, Aligned to parent M description

**Verified description:** geometric “M” mark, dark slate + green (~#5BBC7A) + thin red edge lines.

**Primary — M Mark with Red Edge (matches parent M):**
File: `manage_assets_m_mark_red_edge.png` [MISSING — not in marketing/ as of 2026-10-29] — dark slate #1A242E left, forest green #5BBC7A right, thin red #C43A31 hairline at facet edge. Use for brand commit decision, favicon candidate, header mark candidate.

**Icon Only — Parent Exact (trust, from your logo.png cutout):**
File: `manageassets_icon_light_transparent.png` — exact M+A Peaks, transparent. Min 24px, clear space 1x peak.

**Icon Dark:**
File: `manageassets_icon_dark_transparent.png` — white + Forest on Stone #0E1619.

**AI Variant (product differentiator, PROPOSAL):**
File: `asset_intelligence_icon_ai.png` — same peaks + Lake blue triangle.

**Lockup Light (for README/deck, NOT UI until OWNER DECISION):**
File: `asset_intelligence_lockup_light.png` — icon + Asset Intelligence Stone/Forest duotone. Also `asset_intelligence_final_simple_logo_light.png` with byline “BY MANAGEASSETS.NET — INFRASTRUCTURE INTELLIGENCE FOR THE REAL WORLD”.

**Lockup Dark:**
File: `asset_intelligence_final_simple_logo_dark.png` + `asset_intelligence_lockup_dark.png` [MISSING]

**App Icon 1024:**
File: `asset_intelligence_app_icon_1024.png` [MISSING] + `asset_intelligence_simple_icon.png` (1024×1024, present)

**For Muse Code:** Place icons in `marketing/` candidates and `app/ui/public/` after OWNER DECISION picks canonical `logo.svg`. Until then, keep text wordmark in UI per DESIGN.md. Use lockups in README/docs only.

---

## 08 — UI Application — How Brand Kit Maps to DESIGN.md C. Polish Plan

- **SAM overlay:** Stroke only, 3px selected + white halo (verified), fills subtle 35% alpha (verified). Add pattern/shape redundancy per C.1 colorblind fix, not hue alone — keep cracks visible.
- **Evidence tether (signature PROPOSAL):** 1px steel line #18181b or Forest #5BBC7A pending OWNER DECISION, Lake dot optional. Draw only when both endpoints exist, instant under `prefers-reduced-motion`. From MaskOverlay.jsx to observation row.
- **Ledger chips:** Inspection / Needs Review / Approved / Uncertain (AI) per parent 09 System Details, but styled with verified tokens: Approved Forest tint (if option c), Needs Review tape yellow #ffc93a (PROPOSAL, verify contrast), Uncertain rust #c43a31.
- **Top bar:** DESIGN.md target: “Asset Intelligence • by ManageAssets.ca | DEMO-DRAIN-001 • 11¢ (mono)”. Keep text wordmark until brand commit. Cost honesty: priced estimate with ¢, unpriced “not yet priced”.
- **Blueprint grid:** 1px #d4d4d8 24px intervals opacity 0.4 for empty state “Drop 1–5 photos + note — EXIF GPS stripped”.

---

## 09 — Usage for Muse Code — Law

- Candidate logos are tracked in `marketing/` (committed 2026-10-29); canonical `logo.svg` pick still pending OWNER DECISION. Wire favicon + header mark only after decision.
- Edit tokens only in `app/ui/src/styles.css` `:root`, never new file.
- Keep stack: React 18 + Vite + plain CSS + Canvas 2D, no Tailwind, no TS, no webfonts, no chart libs, no Framer Motion.
- Keep tests green: `pytest`, `vitest run`, `ruff check`, headless tour, `docker compose up` → :3000.
- Never present Llama models, unpriced costs as figures, or measured ratios without running measurement (axe).
- Do NOT mix blue CTAs `#1d4ed8` and green CTAs `#5BBC7A` without OWNER DECISION. Do NOT add purple anywhere.
- Do NOT invent brand facts: logo shortlist lives in tracked `marketing/`; header keeps text wordmark until brand decision lands.

**OWNER DECISION checklist (required before rebrand):**
- [ ] Pick canonical logo file (`manage_assets_inc/logo.svg` vs `logo1–3.png` vs AI set `final_simple_logo_*`)
- [ ] Commit SVG, wire favicon + header mark
- [ ] Resolve blue-vs-green accent: option (a) blue UI + monochrome logo, (b) migrate to green, (c) slate-ink chrome with green reserved for verified/accept
- [ ] Run axe contrast audit at 1280px and 390px on all four tabs, paste report in PR

---

**End — BRAND_KIT aligned to DESIGN.md v1.1 verified `5a83c3e`. Parent ManageAssets.net: Real assets. Brighter communities. Evidence into intelligence. Intelligence into action.**

Copyright 2026 Manage Assets Inc. — manageassets.net / ManageAssets.ca
