---
name: Project Maya Command Core
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#bccbb9'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#869585'
  outline-variant: '#3d4a3d'
  surface-tint: '#4ae176'
  primary: '#4be277'
  on-primary: '#003915'
  primary-container: '#22c55e'
  on-primary-container: '#004b1e'
  inverse-primary: '#006e2f'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#ffba61'
  on-tertiary: '#472a00'
  tertiary-container: '#ef9900'
  on-tertiary-container: '#5c3800'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6bff8f'
  primary-fixed-dim: '#4ae176'
  on-primary-fixed: '#002109'
  on-primary-fixed-variant: '#005321'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 12px
    letterSpacing: 0.06em
  data-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: -0.02em
  data-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0em
spacing:
  gutter: 0.5rem
  gutter-mobile: 0.25rem
  margin: 0.75rem
  margin-mobile: 0.5rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system establishes a high-density, mission-critical operational cockpit tailored for scientific computation, strategic decision support, and real-time telemetry simulation. The aesthetic balances brutalist precision with modern technical ergonomics: severe, hyper-structured, and utterly devoid of decorative ornamentation. Every visual artifact must justify its cognitive footprint. 

The environment speaks to senior systems architects, tactical operators, and domain researchers who require low visual fatigue under sustained operations. It communicates uncompromising accuracy, analytical rigor, and low-latency situational awareness. Visual rhythm relies on micro-tabular grids, monolithic contrast divisions, precise status-driven chromatic signals, and exact data alignment.

## Colors

The chromatic architecture operates in a deep, near-black spectrum to prioritize data legibility and optical preservation in darkened control rooms. Backgrounds migrate through stepped charcoal and deep obsidian tones (`#020617` canvas baseline, `#090d16` primary panels, `#0f172a` interactive containers). Surface elevation is rendered using tone boundaries rather than shadow diffusion.

Borders rely strictly on low-energy dividers (`#1e293b` and `#27272a`), accented with calibrated functional states:
- **Baseline / Neutral Accent:** `#38bdf8` (Simulated vectors, projected trajectories, active cursor targets).
- **Nominal / Stabilized:** `#22c55e` and `#4ade80` (Nominal states, validated simulation models; 20% alpha border tint `rgba(34, 197, 94, 0.20)`).
- **Advisory / Warning:** `#f59e0b` and `#fbbf24` (Elevated telemetry thresholds, parameter divergence; 20% alpha border tint `rgba(245, 158, 11, 0.20)`).
- **Critical / Intercept:** `#ef4444` and `#f43f5e` (Terminal failure, system breach, containment threshold; 20% alpha border tint `rgba(239, 68, 68, 0.20)`).

Saturated hues are strictly reserved for operational significance; informational surfaces and labels remain muted within `#64748b` (sub-tier labels) and `#e2e8f0` (primary operational values).

## Typography

The typographic hierarchy enforces a disciplined separation of structural content and telemetric data. Structural UI framing, procedural instructions, and contextual metadata utilize **Inter**, optimized for density and readability at condensed scales. Telemetry feeds, coordinate systems, model confidence readouts, and timestamps employ **JetBrains Mono** to guarantee strict tabular alignment across oscillating values.

All operational labels default to upper-case tracking with positive letter-spacing (`0.04em` to `0.06em`) to preserve legibility in ambient darkness. Tabular numbers (`font-variant-numeric: tabular-nums`) must be enabled universally across numeric displays to prevent viewport jitter during real-time stream execution.

## Layout & Spacing

The layout is built upon a rigid, non-fluid 12-column sub-grid paired with dense modular docks. Vertical and horizontal rhythms snap to strict 4px increments. Screen real estate is treated as mission-critical; negative space is minimized, functioning purely as a delineator of logical hardware modules and computation pipelines.

- **Desktop (1440px and above):** 12-column grid, `0.5rem` gutters, fixed top telemetry bar (36px height), auxiliary system monitor docks (fixed 320px sidebar), and a flexible central tactical canvas.
- **Tablet / Secondary Display (768px - 1439px):** Split 8-column layout with collapsing secondary parameter panels into tabbed trays.
- **Mobile / Tactical Field Unit (< 768px):** Single-column stacked stream, fixed `0.5rem` outer margins, critical visual indicators pinned to top persistent nodes.

## Elevation & Depth

This design system avoids traditional drop shadows and blur-based glassmorphism, both of which introduce visual ambiguity and GPU overhead in multi-stream rendering pipelines. Depth is communicated strictly through surface luminance and hairline mechanical borders:

1. **Floor 0 (Base Canvas):** `#020617` (Deepest slate, represents unallocated viewport).
2. **Floor 1 (Structural Panels):** `#090d16` with a uniform `1px solid #1e293b` frame.
3. **Floor 2 (Sub-modules & Data Cells):** `#0f172a` inset within Floor 1, segmented by `1px solid #27272a`.
4. **Floor 3 (Interactive Floating Monitors / Command Prompts):** `#1e293b` background with `1px solid #38bdf8` (active cyan trace) or state-driven alpha borders (`rgba(34, 197, 94, 0.20)`, `rgba(239, 68, 68, 0.20)`).

When layered dialogs or diagnostic overlays are active, an un-blurred `#020617` backdrop with 85% opacity suppresses the underlying telemetry while maintaining grid line continuity.

## Shapes

The design system employs a zero-radius geometry (`roundedness: 0`). Every panel, button, tag, and modal window terminates in precise 90-degree corners, evoking military hardware consoles and raw scientific instrumentation. 

Chamfered or notched corner trims (4px diagonal cuts) are permitted exclusively on critical status badges and primary execution triggers to signal active procedural state changes.

## Components

### Buttons & Operational Triggers
- **Primary Execution:** Solid background (`#22c55e` or `#38bdf8`) with high-contrast text (`#020617`), `0px` radius, monospace uppercase labels (`label-md`), `space-xs` vertical padding, `space-md` horizontal padding.
- **Secondary / Telemetry Command:** Inset charcoal (`#0f172a`), `1px solid #1e293b`, hover effect shifts border to `#38bdf8` without shifting layout.
- **Destructive / Abort:** Border `1px solid rgba(239, 68, 68, 0.40)`, background `rgba(239, 68, 68, 0.08)`, text `#f43f5e`.

### Telemetry Badges & Chips
- Monospaced tags with a left-aligned 6px status pip (solid circle or square).
- Border: `1px solid` matching state alpha (e.g., `#22c55e` at 20%). Background is tinted at 5% opacity of state color. Text rendered in `label-sm`.

### Data Tables & Parameter Lists
- Compact row height (28px - 32px).
- Alternating subtle row fills (`transparent` vs `rgba(255, 255, 255, 0.015)`).
- Hairline horizontal dividers (`#1e293b`).
- Monospaced values right-aligned; parameter keys left-aligned in `#94a3b8`.

### Inputs & Vector Fields
- Flat background (`#020617`), `1px solid #27272a`.
- Focus state instantly activates a solid 1px highlight (`#38bdf8`) without drop shadows.
- Suffix units (e.g., `MS/S`, `RAD`, `dBm`) are rendered statically inside the field in `label-sm` muted text (`#64748b`).

### Checkboxes & Toggle Switches
- Checkboxes: Square `14px x 14px`, `0px` radius, `1px solid #334155`. Checked state features a centered `8px x 8px` solid block (`#38bdf8` or `#22c55e`).
- Toggles: Segmented two-position horizontal buttons (`ENABLED` / `HALTED`) replacing sliding thumbs for tactile certainty.

### Tactical Cards & Frame Modules
- Headers contain a distinct technical titlebar (`#0f172a`), separated from the module body by a `1px solid #1e293b` divider.
- Module titles paired with an alphanumeric indexing tag (e.g., `MOD-04 // SIMULATION_CORE`).
- Corner crosshairs or coordinate stamps optionally rendered in `label-sm` `#475569`.