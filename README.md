# pen-audit

Design file scanner — extracts UI features from `.pen` files into actionable development tasks.

Forked from [desloppify](https://github.com/peteromallet/desloppify) and rebuilt for [Pencil MCP](https://pencil.li) design files.

## What it does

`pen-audit` scans exported `.pen` design files and produces a structured feature inventory with:

- **Screen detection** — identifies screens by frame dimensions and classifies platform (mobile/tablet/desktop)
- **Complexity tiers** — T1 (static) through T4 (device APIs) based on detected UI patterns
- **Pattern recognition** — forms, navigation, CRUD operations, data displays, interactive elements
- **State tracking** — tracks which features are implemented, deferred, or open across scans
- **Output formatters** — markdown inventory, `routes.json`, Jira tasks (more coming)

## Install

```bash
pip install -e .
```

## Usage

### 1. Export your .pen file

Use Pencil MCP's `batch_get` tool to export a depth-3+ JSON tree:

```
# Via Pencil MCP
batch_get(filePath: "your-design.pen", readDepth: 3, searchDepth: 4)
```

Save the JSON output to a file (e.g., `design-export.json`), wrapped in a root document frame.

### 2. Scan

```bash
pen-audit scan design-export.json
```

Output:
```
pen-audit scan

  Loaded: design-export.json
  Screens: 25
  Components: 0

  Detected: 128 features
┌─────────────────────────────────────────────┐
│ pen-audit scan results                      │
│                                             │
│ Screens:     25                             │
│ Features:    128                            │
│                                             │
│ T1 (Static pages — ): 32 features           │
│ T2 (Standard CRUD s): 76 features           │
│ T3 (Complex interac): 18 features           │
│ T4 (Advanced (real-):  2 features           │
│                                             │
│ Completion: 0.0% (0/128)                    │
└─────────────────────────────────────────────┘
```

### 3. Track progress

```bash
# Dashboard with progress bars
pen-audit status

# Browse features
pen-audit show                    # all features
pen-audit show screen             # filter by detector
pen-audit show "Food Log"         # filter by name
pen-audit show --status open      # filter by status

# What to build next
pen-audit next
pen-audit next --tier 1 --count 10

# Mark as done
pen-audit resolve implemented "Food Log"
pen-audit resolve deferred "Coming Soon"
```

### 4. Generate artifacts

```bash
# Markdown feature inventory
pen-audit plan --format markdown --output ./output/

# Route definitions
pen-audit plan --format routes --output ./output/

# All formats
pen-audit plan --format all --output ./output/
```

## Detectors

| Detector | Finds | Tier |
|----------|-------|------|
| `screen` | Top-level screen frames, dimensions, platform | T1-T4 |
| `component` | Reusable design system components, usage counts | T1 |
| `navigation` | Tab bars, sidebars, headers, back buttons | T1-T2 |
| `form` | Input fields, toggles, sliders, date pickers | T2-T3 |
| `data_display` | Lists, cards, charts, tables | T2-T3 |
| `interactive` | Tabs, modals, accordions, swipe, drag-drop | T2-T3 |
| `crud` | Add/edit/delete buttons, detail views, empty states | T2 |

## Complexity Tiers

| Tier | Name | Examples | Effort Weight |
|------|------|----------|--------------|
| T1 | Static | About, Terms, Settings | 1x |
| T2 | Standard CRUD | Forms, lists, detail views | 2x |
| T3 | Complex | Charts, timers, builders | 4x |
| T4 | Advanced | Camera, maps, real-time | 8x |

## State

Scan results persist in `.pen-audit/state.json`. Re-scanning merges new features and auto-removes deleted ones without losing resolution status.

## License

MIT
