# Sales UI/UX Shared Patterns v1

## Purpose

This document defines a shared UI/UX baseline for `sales` menus that use similar tree, work-area, and detail-panel patterns.

The goal is not a full product-wide redesign in one pass. The goal is to stop menu drift, preserve the good improvements made in `배치`, and apply a stable common grammar across similar screens.

## Why now

Recent `배치` work produced better interaction patterns than some older menus, especially in:

- left-tree compact actions
- right-side detail / helper panel behavior
- dynamic height handling
- clearer work-area priority
- more consistent collapse / resize behavior

At the same time, `카탈로그`, `자산`, and related menus still carry older interaction and layout decisions. If those are improved one-by-one without a shared baseline, the product will drift again.

## Scope

This v1 covers menus that share one or more of these structures:

- left structure / category / tree panel
- center primary work area
- right detail or helper panel
- resizable split panes
- detail panels with title, tabs, and key/value content

Primary targets:

1. `배치`
2. `카탈로그`
3. `자산`
4. `자산역할` and similar tree/detail menus
5. `프로젝트`, `이력` where the same detail-panel grammar applies

## Core product principles

### 1. Main work area comes first

The largest visual and interaction priority should belong to the main task area.

Examples:

- `배치`: room grid / rack mount grid
- `카탈로그`: main list and product work area
- `자산`: asset list / asset work surface

Helper information must not steal too much width or height from the main task.

### 2. Similar menus should feel related

If two menus both use tree + work area + detail panel, they should share:

- collapse button location
- splitter behavior
- panel border and radius rules
- title + subtitle treatment
- tab styling
- detail row styling
- selected / muted / inactive semantics

### 3. Dynamic sizing over fixed caps

Avoid `vh` and hard pixel caps unless absolutely necessary.

Preferred rule:

- outer layout shell fills available height
- inner work areas consume remaining space with `flex` / `min-height: 0`
- scroll lives inside the correct working region
- visible scrollbars may be hidden where appropriate, but scroll must still work

### 4. Shared semantics across light and dark mode

Light and dark themes may use different palette values, but should keep the same meaning for:

- selected
- muted
- inactive
- dashed vs solid
- border-only vs filled states
- helper vs primary surfaces

## Shared layout grammar

## A. Left tree / structure panel

The `배치` tree should become the reference direction.

### A-1. Role

The left panel owns:

- structure navigation
- hierarchical context
- structure CRUD entry points
- local node actions

### A-2. Interaction rules

Use these as the default tree behavior:

- default mode is compact / clean
- each actionable node gets a fixed right-edge action toggle
- compact actions expand inline on the node
- only one compact action group stays open at once
- selection keeps the active branch strong and softly mutes others
- branch muting should remain soft, not aggressive

### A-3. Visual rules

- panel shell follows the same surface, radius, and border grammar as other side panels
- center / room / major groups get stronger grouping affordances than child nodes
- selected > muted > base priority must always be respected
- tree controls should sit in the tree header, not drift into the main work area

### A-4. What to back-port from `배치`

Candidate items to apply to `카탈로그` and similar menus:

- compact inline node actions
- fixed right-edge node action toggle
- cleaner grouping for major hierarchy levels
- branch focus / muting rules
- more explicit header control grouping

## B. Main work area

### B-1. Role

The center area is the primary task surface.

Examples:

- room grid
- rack mount grid
- catalog work surface
- main data grid

### B-2. Rules

- do not place redundant large help blocks inside the main work area unless the help is critical
- do not let side panels reduce the main work area below a sensible working width
- keep selection, drag/drop, and active states visually obvious
- when detail context changes, the main area should usually remain visible

### B-3. Sizing

- main work area width is protected first
- helper/detail side panels flex second
- if an internal split exists, define which side is fixed and which side flexes
  - for rack mount: mount grid stable, right info/helper side flexes

## C. Right detail / helper panel

There are two related but distinct patterns.

### C-1. Helper side panel

Used when the right side supports the main task directly.

Examples:

- `배치` room view showing `미배치 랙`
- rack mount view showing `랙정보 + 미배치 장비`

Rules:

- collapsible
- resizable
- scroll inside the panel, not outside
- compact headers, minimal wasted vertical space
- should not visually overpower the center work area

### C-2. Detail panel

Used when the right side is a proper detail view.

Reference direction: `카탈로그 > 제품상세`

Rules:

- title / subtitle header
- tab header row
- compact detail body
- key/value rows with consistent spacing and borders
- actions live in a stable, predictable location

### C-3. Shared visual baseline for side panels

All right-side panels should share:

- border color family
- border radius
- surface tone
- internal spacing rhythm
- collapse handle position
- splitter thickness and hover treatment

## Shared component grammar

## D. Detail header

Use one common pattern:

- title
- optional subtitle
- optional actions on the right

This should be reused across:

- catalog detail
- asset detail
- rack info detail
- other similar panels

## E. Tabs

Use a single tab grammar:

- thin bottom border
- compact tab paddings
- active tab indicated by text + underline
- avoid menu-specific tab inventions unless necessary

For small panels, it is acceptable to use a single visible tab like `기본정보` if future expansion is expected.

## F. Detail rows

Use a shared key/value pattern:

- compact row height
- consistent label width
- values aligned predictably
- border separation between rows
- no heavy card-inside-card styling unless needed

## G. Splitter / collapse controls

Use a common rule for:

- splitter thickness
- hover/drag affordance
- handle position
- collapse arrow direction logic
- compact visual height

Avoid oversized splitter indicators that visually dominate the boundary.

## H. Scroll behavior

Preferred rule:

- scroll works where needed
- visible scrollbars may be hidden for polished side/work panels
- auto-scroll to selected / focused content is allowed
- never rely on hidden overflow that makes content unreachable

## Menu-by-menu rollout plan

## Phase 1. Define and freeze common patterns

Deliverables:

- this document finalized as v1
- identify reusable CSS utilities / component classes
- identify current one-off styles that should be retired later

Output should include:

- tree panel pattern
- detail panel pattern
- splitter/collapse pattern
- dynamic height pattern
- selection / muted semantics

## Phase 2. Treat `배치` as tree/work-area reference

Use `배치` as the reference for:

- left tree interactions
- side helper panel behavior
- dynamic shell sizing
- work-area priority

Tasks:

- stabilize the current `배치` layout and eliminate remaining one-off style inconsistencies
- extract reusable classes/tokens where possible
- document what is canonical vs what is `배치`-specific

## Phase 3. Apply tree improvements to `카탈로그`

Goal:

- bring `카탈로그` tree behavior closer to `배치`

Tasks:

- audit current category tree actions
- compare compact/detail action behavior
- adopt fixed toggle / inline action expansion where appropriate
- align grouping, spacing, and muted/selected semantics

## Phase 4. Align detail panels across `카탈로그`, `자산`, and rack info

Goal:

- use a common detail grammar

Tasks:

- compare catalog detail, asset detail, rack info detail
- unify title/subtitle structure
- unify tab styling
- unify key/value row styling
- reduce card-inside-card drift

## Phase 5. Align other related menus

Target candidates:

- `자산역할`
- `프로젝트`
- `이력`
- other list/detail or tree/detail screens

Goal:

- visual parity and interaction predictability, not pixel-perfect sameness

## Decision rules during rollout

When there is a tradeoff, prefer the option that:

1. preserves main work area size
2. reuses an established in-product pattern
3. keeps interaction consistent with similar menus
4. minimizes one-off CSS exceptions
5. keeps light/dark semantics aligned

## What not to do

- do not do a giant unscoped product-wide visual rewrite in one pass
- do not hardcode page-specific colors when shared tokens/classes would work
- do not solve layout issues with repeated `vh` caps unless unavoidable
- do not invent a new detail grammar for each menu
- do not let helper panels outgrow the main working surface

## Immediate next actions

1. Review current `배치` tree and side-panel behavior and mark what is now canonical.
2. Audit `카탈로그` tree behavior against the canonical `배치` tree rules.
3. Identify a reusable CSS/markup subset for:
   - tree header
   - compact node actions
   - detail header
   - tabs
   - detail key/value rows
4. Apply the first cross-menu convergence pass to `카탈로그`.
5. After `카탈로그`, apply the same detail grammar to `자산` and similar menus.

## Success criteria

This effort is successful when:

- users can predict where structure actions live across similar menus
- side panels feel related across menus
- detail panels read like one product family
- dynamic height behavior is consistent and robust
- page-by-page styling drift is noticeably reduced
- future UI work can reference a shared standard instead of inventing local fixes
