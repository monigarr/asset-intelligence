# DESIGN.md — Asset Intelligence / Manage Assets
**For:** Muse Code, Cursor, and frontend agents
**Version:** 1.1 (2026-10-29, verified against `5a83c3e`) — marketing/ reorg paths + BRAND_KIT v2.1 companion
**Workspace:** `\\Pc2\e\Meta_Global_AI_Hackathon\asset-intelligence`
**Product:** Asset Intelligence Review Console (main UI)
**Stack:** React + Vite + plain CSS variables + HTML Canvas (SAM overlay) + FastAPI backend. No Tailwind, no TypeScript, no webfonts, no chart libs.
**Brand:** Tracked `marketing/`: parent M set under `manage_assets_inc/` + Asset Intelligence duotone set at root (Stone/Forest, light+dark, bylined). UI keeps blue `#1d4ed8`, system fonts, flat panels until OWNER DECISION. Companion law: `BRAND_KIT.md` v2.1 (logos, tokens, usage).

> You are a design engineer known for production-grade frontend interfaces that never look like generic AI output. This doc is your law for UI polish. Every claim below was verified against the repo on 2026-10-29; proposals are labeled PROPOSAL, owner calls are labeled OWNER DECISION.

---

## What changed from the 2026-10-26 draft (read this first)

v1.1 (2026-10-29): `marketing/` reorganized (parent set under `manage_assets_inc/`, new AI set at root); all paths current; `BRAND_KIT.md` v2.1 is now the companion brand law.

The prior draft described a codebase that does not exist. Corrected:

- **Stack:** no Tailwind, no `.tsx`, no `index.css`. Styling is `app/ui/src/styles.css` (CSS variables); components are `.jsx`. There is no `tailwind.config.js`.
- **Pipeline:** no “Llama 4 Maverick fusion” — no Llama model exists on the live Meta API. Vision is `muse-spark-1.3` (primary and fallback), reasoning Spark 1.3, planning `muse-wonder-1.0` (ARCH §4.3).
- **Current UI:** no Inter, no purple CTA, no gray `#6B7280` body, no “01/02/03” markers, no sticky 999 header, no bounce animations, no “AI Analysis Results” or “Approve AI” copy. Verified reality: system font stack, blue `#1d4ed8` accent, flat 6px-radius panels, four tabs (Demo / New inspection / About / Insights), Accept–Reject buttons under a “Human review (required)” heading, keyboard-operable evidence chips.
- **Brand:** the draft’s “slate blue `#1E3A5F` primary” is not the logo. The actual parent mark at `marketing/manage_assets_inc/logo.*` is dark slate + green + red hairlines (see Brand section).
- **What the old draft got right and is kept:** the Industrial Forensic Ledger direction, the evidence-tether signature idea, sunlight-contrast and glove/keyboard concerns, and liability-safe copy goals.

---

### Context

**Product / page:** Asset Intelligence — field evidence review console. Inspector uploads 1–5 photos + note → SAM 3.1 masks + Spark 1.3 vision fusion + Spark evidence-linked JSON + Wonder discrepancy/missing check → human must accept/edit/reject. Main screen is verification, not dashboard; the Insights tab (shipped) covers reporting.

**Audience:** Municipal maintenance coordinators (40–55, field engineers, public works). Hi-vis vests, concrete dust, CMMS tickets. They distrust AI that invents measurements. They trust tape measures, photos with scale, and audit trails.

**Job of this screen:** In 15 seconds, answer: Is this AI result grounded? Click mask → see evidence → spot what’s missing → accept/reject with liability-safe wording.

**Stack:** React 18 + Vite + plain CSS variables (`styles.css`), Canvas 2D for SAM mask overlay, Pydantic/FastAPI backend. Zero UI dependencies beyond React. Must work `docker compose up` → :3000.

**Brand constraints (verified + proposed):**
- Logo (verified, tracked `marketing/`): parent M set at `manage_assets_inc/logo.png|.svg` (+`logo1–3.png`, `brand_kit.png` — angular “M”, slate + green + red hairlines); product set at root: `asset_intelligence_final_simple_logo_{light,dark}.png` (Stone/Forest duotone + byline), `lockup_light.png`, `icon_ai.png`, `simple_icon.png`.
- UI today (verified, `styles.css`): `--accent: #1d4ed8` blue, `--text: #18181b`, `--muted: #52525b`, `--border: #d4d4d8`, `--warn: #b45309`, `--radius: 6px`, system font stack, 14px body.
- OWNER DECISION: reconcile UI blue `#1d4ed8` with logo green `#5BBC7A`. Options: (a) keep blue UI + monochrome logo usage in header; (b) migrate primary actions to logo green; (c) slate-ink chrome with green reserved for “verified/accept” semantics. Do not mix blue CTAs and green CTAs without deciding.
- Type must stay readable at 13px in truck-cab sunlight. No purple anywhere; no Inter/Roboto-as-personality (currently system stack — fine); no acid-green dark theme.

**What exists today (verified):** Four-tab console. Demo tab: 10-fixture dropdown, SAM overlay canvas (label-colored fills + 3px bbox strokes, 5px + white halo when selected), evidence chips (keyboard-operable buttons), missing-info checklist, Accept/Reject with “Human review (required)”. New inspection tab: drag-drop upload, note, asset ID, API key + key-request hint. About tab: builder/hackathon/product info. Insights tab: stat cards, filterable/sortable history table, per-call stage timeline, priced/unpriced cost honesty. Canvas has `role="img"` + label; tablist ARIA + `:focus-visible` shipped.

**What feels wrong (verified gaps only):** Canvas mask picking is mouse-only (no keyboard path); small bboxes are small targets (glove problem is real); masks are distinguished by hue alone (no pattern/label redundancy for colorblind users); confidence renders as a bare number (`crack 0.87` — 0.87 of what?); no liability disclaimer next to Accept; no contrast audit has ever run; no print stylesheet; observations carry equal visual weight.

---

## Design Thinking (do this first)

**Purpose and user:** Municipal coordinator needs forensic confidence, not wow. Purpose = convert messy field evidence into auditable ledger. User = field-pragmatic engineer who trusts visual proof over prose.

**Tone extreme you will commit to:** **Industrial Forensic Ledger.** Not minimal for minimal’s sake, not playful, not luxury. Field notebook meets engineering blueprint: cold concrete, steel rule lines, monospaced evidence refs, precise 1px borders. Subject is concrete, rebar, water intrusion — gray, blue, rust. Vernacular is inspection forms, not SaaS.

**Differentiation: the one thing someone will remember:** **Evidence-tethered mask interaction.** Click a SAM mask on the photo → a thin leader line draws to the observation row → that row highlights → (later) the cited note span underlines. Every sentence traces to a pixel. (PROPOSAL — the click→chip highlight exists; the drawn line does not.)

**Constraints from brand, stack, and accessibility:**
- Must preserve SAM mask fidelity (RLE → Canvas). No blur or shadow that obscures a crack.
- Colorblind-safe: masks not distinguished by hue alone; add pattern or label redundancy.
- Sunlight contrast: body text `#18181b` on white; never muted gray for observations; run a real contrast audit (axe) instead of asserting ratios.
- No new dependencies without owner sign-off. Canvas 2D for masks, no WebGL. System font stack stays unless the font decision below says otherwise.
- Keyboard: every pointer action needs a keyboard path (chips already do; canvas does not — that is the gap).
- Reduced motion: honor `prefers-reduced-motion`; default to no animation except the single tether draw.
- Cost honesty (binding repo rule): priced figures read as estimates; unpriced reads “not yet priced,” never $0.00.

---

## A. Critique (verified against `5a83c3e` — no strawmen)

**Hierarchy & scan path**
1. Observations carry equal weight: crack, seepage, vegetation look the same. Severity or discrepancy-link should differentiate.
2. Missing-information checklist sits below the fold on small screens; field coordinators triage by what’s missing.
3. Insights tab exists and is consistent, but Demo/New result layout is 50/50, not evidence-led.

**Typography**
4. System stack everywhere, no mono utility face for `mask_id`, spans, cost, `model_trace` — engineers scan refs like part numbers. (Fix within system stack: `ui-monospace` — no downloads.)
5. Canvas labels are 12px system-ui on photo backgrounds with black stroke — legible but small; test at arm’s length.

**Color & contrast**
6. Mask fills are hue-only (red/orange/yellow/green/blue by label, ~35% alpha) with no pattern or shape redundancy — colorblind gap.
7. No contrast audit has ever run (axe or otherwise). Ratios below are targets, not claims, until measured.
8. Small bbox strokes on bright concrete can wash out despite the selected-state white halo.

**Layout & spacing**
9. Canvas padding is tight on narrow screens; mask labels near edges clip (`Math.max(12, y1 - 4)` floor exists but no right-edge guard).
10. Filter row + table in Insights is solid; Demo/New result grid could adopt the same two-pane ledger rhythm (canvas-led, ledger scrolls).

**Interaction**
11. Canvas picking is mouse-only: `onClick` bbox hit-test, no keyboard equivalent, no focus indicator. Small bboxes fail glove use. (Evidence chips ARE keyboard-operable — the gap is canvas-side only.)
12. No orchestrated inference moment — results pop in. A single restrained reveal is a PROPOSAL, not a defect.

**Copy in the UI**
13. Canvas labels show bare confidence (`crack 0.87`) with no units or meaning. Should read `crack · SAM 0.87` with a hint that masks need human measurement.
14. No liability disclaimer near Accept. Add: “Does not certify safety. Requires qualified inspection.” (PROPOSAL, owner wording.)
15. Current copy is otherwise sound: “Human review (required)”, Accept/Reject, “Review is disabled in demo mode.” Keep.

**Accessibility & responsive risk**
16. 900px breakpoint stacks layout; canvas + ledger lose visual sync on mobile. Acceptable if chip→mask highlight still works (verify).
17. Touch targets: table sort buttons and chips pass; canvas targets do not (see 11).

---

## B. Direction

**Aesthetic in 2–5 words:** Industrial Forensic Ledger

**Why it fits this product:** Infrastructure inspection is a ledger of physical facts — photo, note, measurement, mask. Municipal workers trust forms that look like engineering submittals: cold, ruled, monospaced references, no marketing. This signals “audit-ready” not “AI magic,” which is what Startup-track judges score: technical execution that holds up in production.

**Signature element: ONE memorable move; keep everything else quiet:**
**Evidence tether line (PROPOSAL).** A 1px steel line from the selected SAM mask centroid to the active observation row. Click `mask_1` → line draws → row highlights → cited note span underlines (phase 2). Everything else stays quiet: no card shadows, no hover lift.

**Palette: current tokens (verified) + proposed additions**
- Current `styles.css` `:root` (do not rename without a migration): `--bg #ffffff`, `--panel #f4f4f5`, `--border #d4d4d8`, `--text #18181b`, `--muted #52525b`, `--accent #1d4ed8`, `--warn #b45309`, `--radius 6px`.
- PROPOSAL additions: `--alert` tape yellow (missing chips — WCAG-check the pairing, don’t assert it), `--discrepancy` rust (banner), `--mono` utility stack. Any hue change must survive the contrast audit in C.1.
- OWNER DECISION (from Context): reconcile `#1d4ed8` UI blue with `#5BBC7A` logo green before any rebrand commit.

**Type: keep the system stack (verified decision, reverses the old draft)**
- The old draft prescribed Fragment Mono + General Sans + JetBrains Mono via CDN. Rejected as default: external fonts cost bundle weight, break offline demos, and raise consent questions for municipal IT.
- Direction: system-ui body (today) + `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` utility face for `mask_id`, spans, cost, `model_trace`, timestamps. Distinctive enough via pairing + tracking, zero downloads.
- OPTIONAL phase (owner call): self-hosted display face for the header/asset-ID only, subset to latin, preloaded, with system fallback. Never a render-blocking CDN link.

**Layout concept in one sentence:** Keep the four tabs; evolve Demo/New results toward a two-pane forensic viewer (canvas-led left, evidence ledger right) while Insights keeps its cards → filters → table → detail rhythm.

**ASCII wireframe — result view, 1440px (target, not current):**

```
+----------------------------------------------------------------------------------+
| Header: Asset Intelligence • by ManageAssets.ca | DEMO-DRAIN-001 • 11¢ (mono)     |
| Tabs: Demo | New inspection | About | Insights                                   |
+------------------------------------------+---------------------------------------+
| IMAGE CANVAS                             | LEDGER                                |
| ┌─────────────────────────────────┐     | Observations (3)                      |
| │ [photo] SAM masks: 3px stroke,  │     | ┌──────────────────────────────┐     |
| │ pattern + label (not hue-only)  │     | │ #mask_1 crack · SAM 0.87     │◄──── tether (PROPOSAL)
| │ [keyboard-focusable regions]    │     | │ "Linear crack top edge..."   │     |
| └─────────────────────────────────┘     | │ evidence: image_0 / note [mono]│    |
| Mask rail: [mask_1] [mask_2] ...  │     | └──────────────────────────────┘     |
| (PROPOSAL, 32px+ targets)         │     | Discrepancies [rust banner]         |
|                                         | Missing: [tape chips]                 |
|                                         | [Accept] [Reject] + safety disclaimer |
+------------------------------------------+---------------------------------------+
```

**Motion intent: one orchestrated moment worth doing; what to leave still; reduced-motion plan**
- PROPOSAL: on result load, masks fade in with a short stagger; tether draws 180ms ease-out on selection. That is the entire motion budget.
- Leave still: no hover lift, no image scale, no bounce — none exist today; keep it that way.
- Reduced motion: everything appears instantly when `prefers-reduced-motion` is set.

---

## C. Polish Plan (priority order, real files only)

Conventions: no new npm dependencies; every item keeps `pytest`, `vitest run`, `ruff check`, headless tour, and docker build green; Demo/New/About/Insights screenshots before + after.

### 1. Must-fix this pass (blocking taste / readability / a11y)

- [ ] **Canvas keyboard picking + glove targets.** `app/ui/src/components/MaskOverlay.jsx`: add a keyboard path (focusable listbox of masks mirroring the canvas, or roving-focus regions) that drives the same `onMaskClick` → chip highlight path. Expand hit slop beyond raw bbox (min 24px target). Acceptance: full inspection review completable keyboard-only; tour asserts chip→mask and mask→chip both ways.
- [ ] **Mask redundancy (colorblind).** Same file: add per-label pattern or shape redundancy (e.g., dashed vs solid stroke styles + always-on label tags), not hue alone. Keep fills subtle so cracks stay visible. Acceptance: masks distinguishable in grayscale screenshot.
- [ ] **Confidence context copy.** Same file: label reads `{label} · SAM {confidence}` plus a ledger hint that masks require human measurement. Acceptance: no bare `0.87` copy anywhere.
- [ ] **Contrast audit for real.** Run axe on all four tabs at 1280px and 390px; fix what fails (candidate: 12–13px muted text, chip contrast, canvas labels on bright photos). Acceptance: 0 axe contrast violations; paste the report in the PR, not ratios from memory.
- [ ] **Mono utility face.** `app/ui/src/styles.css`: add `--mono` system-mono stack; apply to evidence refs, cost, `model_trace`, timestamps, asset IDs. Acceptance: no new font downloads (network tab clean), refs scannable.
- [ ] **Liability disclaimer (owner wording).** Near Accept in Demo/New results: “Does not certify safety. Requires qualified inspection.” Acceptance: visible without scrolling on 900px-tall viewport.

### 2. High-impact visual upgrades

- [ ] **Evidence tether (signature).** New `TetherLine` in `MaskOverlay.jsx` or sibling: absolutely-positioned SVG leader from selected mask centroid to active observation chip/row. Draw only when both endpoints exist; instant under reduced-motion. Acceptance: e2e tour asserts line endpoints within tolerance; keyboard selection draws it too.
- [ ] **Two-pane ledger rhythm.** `App.jsx` result layout + `styles.css`: canvas-led left column (sticky on desktop), ledger right; adopt Insights’ panel rhythm for consistency. Mobile stacks (existing 900px breakpoint) with chip-highlight preserved. Acceptance: 1440px + 390px screenshots, no horizontal scroll.
- [ ] **Missing info as high-visibility chips.** `MissingChecklist.jsx` + tokens: tape-yellow chip treatment at verified contrast, mono uppercase. Acceptance: glanceable; axe-clean.
- [ ] **Discrepancy banner.** `JsonViewer.jsx`: rust-toned banner above observations when discrepancies exist; distinct from info styling. Acceptance: cannot be mistaken for an observation.
- [ ] **Mask rail (PROPOSAL).** Pill buttons under canvas mirroring masks (`mask_1 crack 0.87`), 32px+ targets, arrow-key cycling, driving the same selection state. Acceptance: usable with gloves (pointer) and keyboard.
- [ ] **Cost + model trace footer.** Extend the existing `JsonViewer` trace row (already `sam · vision · reasoning · planning · cost`) with priced/unpriced honesty styling shared with Insights’ `CostLine`. Real model IDs only — never Llama. Acceptance: identical cost text for the same call in ledger and Insights.

### 3. Nice-to-have craft

- [ ] **Note-span underline.** When a chip is selected, underline the cited span in the field-note view with a “cited by {mask}” tooltip. (Reverse of today’s chip→mask highlight.)
- [ ] **Empty-state blueprint.** `UploadForm.jsx` empty state: 1px-grid dashed drop zone, “Drop 1–5 photos + note — EXIF GPS stripped.” Keep the existing dropzone behavior.
- [ ] **Print ledger.** `@media print` in `styles.css`: hide canvas/nav, render the ledger as a filing-ready report with the evidence table + disclaimer.
- [ ] **Brand commit (OWNER DECISION).** Pick canonical logo (parent M at `marketing/manage_assets_inc/logo.svg` vs AI set), wire favicon + header mark, resolve the blue-vs-green accent question. Until then: no logo in UI, text wordmark stays. (Assets already tracked; see BRAND_KIT.md v2.1.)

---

## D. Implementation Notes

**Stack facts (verified):** Vite + React 18 + plain CSS (`app/ui/src/styles.css`), no Tailwind, no TS, no UI deps beyond react/react-dom. Tests: vitest (`*.test.js`, no DOM renderer — keep component logic in testable helper modules like `components/insights.js`). Tour: playwright scripts outside the repo.

**Token changes (edit `app/ui/src/styles.css` `:root`, never a new file):**
```css
:root {
  /* existing — do not rename */
  --bg: #ffffff; --panel: #f4f4f5; --border: #d4d4d8;
  --text: #18181b; --muted: #52525b; --accent: #1d4ed8;
  --warn: #b45309; --radius: 6px;
  /* proposed additions (each needs the C.1 contrast audit) */
  --alert: #ffc93a;             /* missing chips — verify pairing */
  --discrepancy: #c43a31;       /* banner — verify pairing */
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
```

**Component changes (real files, keep selector specificity sane):**
- `components/MaskOverlay.jsx`: selection state + `onMaskClick` already exist — extend, don’t rebuild. Canvas 2D; keep `role="img"` + label; add keyboard path + patterns + halo.
- `components/JsonViewer.jsx`: evidence chips + trace row exist — add banner, mono refs, shared cost styling.
- `components/MissingChecklist.jsx`: checklist exists — re-skin as chips.
- `components/ReviewActions.jsx` + `App.jsx`: Accept/Reject + “Human review (required)” exist — add disclaimer, keep decisions as accept/edit/reject.
- `components/InsightsPanel.jsx` + `components/insights.js`: newest surface — apply tokens here too so polish is consistent; its filter/sort/keyboard patterns are the reference for new interactive work.
- `components/Header.jsx`, `components/icons.jsx`: stroke-icon set (`ChartIcon` pattern) — new icons follow it, 24px grid, `currentColor`.

**What NOT to touch:**
- Do NOT add Tailwind, Framer Motion, chart libs, or webfont CDNs without owner sign-off.
- Do NOT change the API contract (`human_review_required`, `model_trace`, cost shape). UI is a view layer.
- Do NOT invent brand facts: logo shortlist lives in tracked `marketing/` (see BRAND_KIT.md v2.1); header keeps the text wordmark until the brand decision lands.
- Do NOT restyle cost figures into false precision: priced = estimate with ¢, unpriced = “not yet priced,” everywhere.
- Do NOT regress a11y: tablist ARIA, `:focus-visible`, chip keyboard paths, and tour coverage stay green.

**Microcopy in product voice (active verbs, sentence case, no filler):**
- Headline: “Inspection intelligence — evidence linked”
- Sub: “3 masks · 2 discrepancies · 2 missing — review in 15 seconds”
- Primary: “Accept” / Secondary: “Reject” (keep), heading keeps “Human review (required)”
- Disclaimer: “Does not certify safety. Requires qualified inspection.” (owner wording)
- Missing chip: “Missing: tape measure”
- Discrepancy: “Note says dry, image shows seepage — requires dry-weather follow-up”
- Confidence: “crack · SAM 0.87 — requires human measurement”

---

## E. Self-check

- [x] Took one justified aesthetic risk: **Industrial Forensic Ledger** + evidence tether (proposal), justified by municipal field context.
- [x] Removed at least one decorative accessory: N/A — verified the UI has no purple/Inter/bounce/01-02-03 to remove; the plan instead removes hue-only encoding and bare-confidence copy.
- [x] Contrast: targets stated, audit required — no ratios claimed without measurement.
- [x] Matched complexity to vision: minimal = precise — 1px rules, quiet surfaces, one motion moment (proposed).
- [x] Did not invent brand facts: logo described from tracked `marketing/` (parent M + AI set), palette decisions marked OWNER DECISION, unknowns explicit.
- [x] Signature element memorable: evidence tether line (proposal).
- [x] No anti-slop defaults: system stack, no gradients, no cream, no glass, no emoji icons, no nested-card chrome, motion gated on `prefers-reduced-motion`.

**Deliverable for Muse Code:** Implement per Section C priority order. Start with must-fix, then high-impact. Keep `pytest`, `vitest run`, `ruff check`, headless tour, and `docker compose up` green. Never present Llama models, unpriced costs as figures, or measured ratios without running the measurement.
