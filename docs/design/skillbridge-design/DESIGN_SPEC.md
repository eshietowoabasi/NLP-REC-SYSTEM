# SkillBridge — UI redesign spec

This folder is the approved design for the NLP-RS front end, renamed **SkillBridge**.
It is a *visual* redesign only. Backend, API calls, data flow, permissions and tests stay as they are.

## What's in this folder

| File | What it is |
|---|---|
| `DESIGN_SPEC.md` | This file: tokens, components, rules, page map |
| `pages/*.dc.html` | 20 page mockups + 2 shared components (Sidebar, TopBar) + logo board |
| `assets/login-photo.jpg` | Photo for the right half of the sign-in page |

### How to read the mockups
Each `.dc.html` is plain HTML with inline styles — read the styles as the source of truth for spacing, colour and type.
A few non-standard tags come from the design tool:
- `<dc-import name="Sidebar" active="…" admin="…">` = render the Sidebar component (see `Sidebar.dc.html`) with those props.
- `<sc-for list="{{rows}}" as="r">…</sc-for>` = a `.map()` over a list. `{{r.title}}` = a value.
- `<sc-if value="{{x}}">` = conditional render.
- The `<script type="text/x-dc">` at the bottom holds **sample data only** (`renderVals()`). Never hard-code it — use the real API data.
- Placeholder text in square brackets, e.g. `[admin email]`, is a slot for real data.

## 1. Brand tokens

Put these in the Tailwind 4 theme (`@theme` in the main CSS) and map the shadcn/ui CSS variables to them.

| Token | Hex | Use |
|---|---|---|
| `terracotta` (primary) | `#A8431E` | Primary buttons, active nav, links, brand |
| `terracotta-dark` | `#7E2F12` | Hover/pressed primary, text on tint |
| `terracotta-tint` | `#F8E6DC` | Active nav background, soft highlights |
| `amber` | `#F2B84B` | Accent, keystone, "needs attention" |
| `amber-tint` | `#FDF1D8` | Help cards, warnings (text `#6B4A00`) |
| `ink` | `#231A14` | Main text, dark surfaces |
| `sand` | `#FBF6EF` | App background |
| `white` | `#FFFFFF` | Cards, sidebar, inputs |
| `border` | `#EADFD3` | Card borders |
| `input-border` | `#E3D6C8` | Inputs, secondary buttons |
| `divider` | `#F1E8DE` | Row dividers inside cards |
| `body` | `#4A3F37` / `#5E5249` | Body / secondary text |
| `muted` | `#6F625A` | Helper text, meta |
| `faint` | `#8A7C72` | Section labels ("WORKSPACE") |
| `teal` | `#1F6F5C` on `#DCEFE8` | Info, "compared", Viewer role |
| `green` | `#2F6B3A` on `#E3F1E4` | Success, accepted |
| `red` (errors only) | `#B42318` on `#FDECEA` | Errors, rejected, destructive |

shadcn mapping: `--primary` = terracotta, `--primary-foreground` = white, `--background` = sand, `--card` = white, `--border` = border, `--input` = input-border, `--ring` = terracotta, `--muted-foreground` = muted, `--accent` = terracotta-tint, `--destructive` = red. Dark mode is out of scope.

## 2. Typography
- Font: **Plus Jakarta Sans** (400/500/600/700/800), loaded once (Google Fonts or `@fontsource/plus-jakarta-sans`). Fallback `system-ui, sans-serif`.
- Page title (h1): 28px / 800 / letter-spacing -0.03em.
- Sign-in heading: 44px / 800 / -0.035em.
- Card title (h2): 17px / 800.
- Body: 14–15px / 400–500, line-height 1.5–1.6.
- Meta/helper: 12–13px, colour `muted`.
- Section labels: 11px / 700 / letter-spacing 0.1em / uppercase / colour `faint`.
- Big numbers (stat tiles): 22–32px / 800.

## 3. Shape, spacing, elevation
- Radius: inputs & buttons 12–14px; cards 20px; large panels 22–28px; chips/pills 999px.
- App shell: sidebar 256px wide, white, right border; top bar 72px; main content padding 28px 40px, gap 16–18px.
- Heights: inputs 44–54px, primary buttons 46–56px, nav items 44px, table rows ~52px.
- Elevation: flat — borders, not shadows. Only a highlighted/selected card gets `0 12px 32px rgba(168,67,30,.12)`.

## 4. Components
- **Logo**: Keystone mark (see `Logos.dc.html`, Option 2, marked "Chosen"). Build `<Logo size />`. Wordmark "SkillBridge", 800, ink. Favicon = the dark-square version.
- **Sidebar** (`Sidebar.dc.html`): logo + "UNIUYO · Computer Science"; WORKSPACE group (Dashboard, Documents, Analyses, Reports); ADMINISTRATION group shown **only for Admin** (NUC core curriculum, Users, Settings, Activity log); amber "New here?" help card pinned to bottom. Active item: terracotta-tint bg, terracotta text, 700.
- **TopBar** (`TopBar.dc.html`): breadcrumb + page title left; bell + user chip (initials avatar, name, role) right.
- **Buttons**: primary (terracotta, white text, 700), secondary (white, input-border, ink text), text link (terracotta, 700, no underline).
- **Status chips** (pill, 12px/700): Accepted = green; Undecided/Needs review = amber; Rejected = red; Compared/Info = teal; Left out/Neutral = divider bg + muted text.
- **Cards**: white, 1px border, radius 20, padding 20–26.
- **Lists/tables**: rows inside a card, 1px divider between rows, no zebra stripes.
- **Score**: always shown **out of 100** (e.g. "82 / 100"), never 0.82. Show the 3 parts as "Employer demand · How often it comes up · How new it is".
- **Empty / no-access states**: centred illustration + one sentence + one primary button (see `NoAccess.dc.html`).

## 5. Wording rules (important)
Plain English, no jargon on screen. Use these labels:
- "Suggested topics" (not recommendations/clusters), "Evidence" (not corpus), "Documents", "Analyses".
- "Employer demand", "How often it comes up", "How new it is" (not frequency/novelty/weights).
- "May already be in NUC core" (not overlap/similarity threshold).
- "Activity log" (not audit log). "Left out" (not excluded).
- Buttons say what happens: "Accept topic", "Design this course", "Download report".

## 6. Page map (mockup → app screen)

| # | Mockup | Screen / route (match to existing routes) | Who sees it |
|---|---|---|---|
| 01 | `Login` | Sign in — split screen, form left, photo right with dark caption card | Everyone |
| 02 | `Dashboard` | Home — next steps, progress, stat tiles | All roles |
| 03 | `Documents` | Documents list | All (add = Planner/Admin) |
| 04 | `AddDocuments` | Add documents / collect job adverts dialog | Planner, Admin |
| 05 | `DocumentDetail` | One document + extracted skills | All |
| 06 | `Analyses` | Analyses list | All |
| 07 | `NewAnalysis` | Start an analysis | Planner, Admin |
| 08 | `AnalysisProgress` | Running analysis — step progress | All |
| 09 | `Evidence` | Evidence behind an analysis | All |
| 10 | `Recommendations` | Suggested topics list (score / 100, status chip) | All (decide = Planner/Admin) |
| 11 | `RecommendationDetail` | One topic — score breakdown, evidence, accept/reject | All |
| 12 | `DesignCourse` | Design course form (code, title, units, outline) | Planner, Admin |
| 13 | `ProposedCourses` | Proposed courses + total units | All |
| 14 | `Reports` | Download PDF / Word report | All |
| 15 | `NucCore` | NUC core curriculum (admin) | Admin |
| 16 | `Users` | Users + role explainer cards | Admin |
| 17 | `Settings` | Scoring sliders, overlap %, topics per analysis | Admin |
| 18 | `AuditLog` | Activity log | Admin |
| 19 | `Profile` | Profile + change password | All |
| 20 | `NoAccess` | 403 page | Anyone hitting a blocked route |

If a mockup shows a feature the app does not have yet, **don't build the feature** — style what exists and list the gap in your report.
