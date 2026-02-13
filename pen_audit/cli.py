"""CLI entry point for pen-audit."""

import argparse
import json
import sys
from pathlib import Path

from .utils import c, print_box, print_table


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pen-audit",
        description="pen-audit — design file feature scanner for .pen files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  pen-audit scan design-export.json
  pen-audit scan design-export.json --format markdown
  pen-audit status
  pen-audit show screen
  pen-audit show "Food Log"
  pen-audit next
  pen-audit resolve screen::abc123::FoodLog --status implemented
  pen-audit plan --format all --output ./output/
""",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # scan: run all detectors
    p_scan = sub.add_parser("scan", help="Scan a .pen export and detect UI features")
    p_scan.add_argument("file", type=str, help="Path to .pen JSON export file")
    p_scan.add_argument("--state", type=str, default=None, help="State file path")
    p_scan.add_argument("--format", type=str, default="summary",
                        choices=["summary", "json", "markdown"],
                        help="Output format (default: summary)")

    # status: show completion dashboard
    p_status = sub.add_parser("status", help="Show completion dashboard")
    p_status.add_argument("--state", type=str, default=None)
    p_status.add_argument("--json", action="store_true")

    # show: dig into features
    p_show = sub.add_parser("show", help="Show detected features by detector, screen, or pattern")
    p_show.add_argument("pattern", nargs="?", default=None,
                        help="Filter: detector name, screen name, or feature ID")
    p_show.add_argument("--state", type=str, default=None)
    p_show.add_argument("--status", choices=["open", "implemented", "deferred", "all"],
                        default="all")

    # next: suggest next feature to implement
    p_next = sub.add_parser("next", help="Suggest next feature to implement")
    p_next.add_argument("--state", type=str, default=None)
    p_next.add_argument("--tier", type=int, choices=[1, 2, 3, 4], default=None)
    p_next.add_argument("--count", type=int, default=5)

    # resolve: mark feature status
    p_resolve = sub.add_parser("resolve", help="Mark feature(s) as implemented/deferred/out_of_scope")
    p_resolve.add_argument("status", choices=["implemented", "deferred", "out_of_scope"])
    p_resolve.add_argument("patterns", nargs="+", help="Feature ID(s) or screen name patterns")
    p_resolve.add_argument("--state", type=str, default=None)

    # match: auto-detect implemented features from codebase
    p_match = sub.add_parser("match", help="Match features against codebase to auto-resolve implemented ones")
    p_match.add_argument("project_dir", type=str, help="Path to the project root")
    p_match.add_argument("--app-subdir", type=str, default="", help="App subdirectory (e.g., apps/mobile-web)")
    p_match.add_argument("--state", type=str, default=None)
    p_match.add_argument("--dry-run", action="store_true", help="Don't modify state, just show matches")

    # plan: generate output artifacts
    p_plan = sub.add_parser("plan", help="Generate development artifacts from scan")
    p_plan.add_argument("--state", type=str, default=None)
    p_plan.add_argument("--format", type=str, default="markdown",
                        choices=["markdown", "jira", "routes", "stubs", "tests", "all"],
                        help="Output format")
    p_plan.add_argument("--output", type=str, default=None, help="Output directory")

    return parser


def _get_state_path(args) -> Path | None:
    p = getattr(args, "state", None)
    return Path(p) if p else None


def cmd_scan(args):
    """Run all detectors against a .pen export file."""
    from .pen_parser import load_pen_file
    from .detectors import run_all_detectors
    from .state import load_state, save_state, merge_scan

    print(c("\npen-audit scan\n", "bold"))

    # Load the .pen export
    doc = load_pen_file(args.file)
    print(c(f"  Loaded: {args.file}", "dim"))
    print(c(f"  Screens: {len(doc.screens)}", "dim"))
    print(c(f"  Components: {len(doc.components)}", "dim"))
    print()

    # Run all detectors
    features = run_all_detectors(doc)
    print(c(f"  Detected: {len(features)} features", "dim"))

    # Merge into state
    sp = _get_state_path(args)
    state = load_state(sp)
    diff = merge_scan(state, features, source_file=args.file)
    save_state(state, sp)

    # Show results
    if args.format == "json":
        print(json.dumps({
            "screens": len(doc.screens),
            "components": len(doc.components),
            "features": len(features),
            "diff": diff,
            "stats": state["stats"],
            "features_list": features,
        }, indent=2))
    elif args.format == "markdown":
        _print_markdown_summary(doc, features, state)
    else:
        _print_scan_summary(doc, features, state, diff)


def _print_scan_summary(doc, features, state, diff):
    """Print the scan summary box."""
    stats = state["stats"]
    by_tier = stats.get("by_tier", {})

    # Count by detector
    by_detector: dict[str, int] = {}
    for f in features:
        det = f["detector"]
        by_detector[det] = by_detector.get(det, 0) + 1

    lines = [
        "pen-audit scan results",
        "",
        f"Screens:     {len(doc.screens)}",
        f"Components:  {len(doc.components)} ({len(set(c['name'] for c in features if c['detector'] == 'component'))} unique)",
        f"Features:    {len(features)}",
        "",
    ]

    for tier in sorted(by_tier.keys(), key=int):
        tier_int = int(tier)
        from .scoring import TIER_DESCRIPTIONS
        label = TIER_DESCRIPTIONS.get(tier_int, f"Tier {tier}")
        total = by_tier[tier]["total"]
        done = by_tier[tier]["done"]
        lines.append(f"T{tier} ({label[:15]}): {total:3d} features")

    lines.append("")
    lines.append(f"Completion: {stats['pct']}% ({stats['implemented']}/{stats['total']})")

    print_box(lines)

    # Diff
    if diff["new"]:
        print(c(f"\n  +{diff['new']} new features detected", "yellow"))
    if diff["removed"]:
        print(c(f"  -{diff['removed']} removed from design", "dim"))
    print()

    # Per-detector breakdown
    print(c("  Features by detector:", "bold"))
    for det, count in sorted(by_detector.items()):
        print(f"    {det:<15} {count:3d}")
    print()


def _print_markdown_summary(doc, features, state):
    """Print a markdown feature inventory."""
    print(f"# pen-audit: Feature Inventory\n")
    print(f"**Source**: {doc.source_file}")
    print(f"**Screens**: {len(doc.screens)}")
    print(f"**Components**: {len(doc.components)}")
    print(f"**Features detected**: {len(features)}\n")

    # Group by screen
    by_screen: dict[str, list[dict]] = {}
    non_screen = []
    for f in features:
        if f["category"] == "screen":
            by_screen.setdefault(f["name"], []).append(f)
        elif f["category"] == "component":
            non_screen.append(f)
        else:
            screen_name = f["detail"].get("screen_name", "Unknown")
            by_screen.setdefault(screen_name, []).append(f)

    print("## Screens\n")
    for screen_name, screen_features in sorted(by_screen.items()):
        screen_f = [f for f in screen_features if f["category"] == "screen"]
        tier = screen_f[0]["tier"] if screen_f else 2
        platform = screen_f[0]["detail"].get("platform", "unknown") if screen_f else "unknown"
        print(f"### {screen_name} (T{tier}, {platform})\n")
        for f in screen_features:
            status_icon = {"open": "[ ]", "implemented": "[x]", "deferred": "[-]"}.get(f["status"], "[ ]")
            print(f"- {status_icon} {f['summary']}")
        print()

    if non_screen:
        print("## Design System Components\n")
        for f in sorted(non_screen, key=lambda x: x["detail"].get("usage_count", 0), reverse=True):
            usage = f["detail"].get("usage_count", 0)
            print(f"- **{f['name']}** — used {usage}x")
        print()


def cmd_status(args):
    """Show completion dashboard."""
    from .state import load_state

    sp = _get_state_path(args)
    state = load_state(sp)

    if not state["features"]:
        print(c("  No scan data. Run: pen-audit scan <file>", "yellow"))
        return

    stats = state["stats"]

    if getattr(args, "json", False):
        print(json.dumps(stats, indent=2))
        return

    print(c("\npen-audit status\n", "bold"))

    # Overall progress bar
    pct = stats["pct"]
    bar_len = 30
    filled = round(pct / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    color = "green" if pct >= 80 else ("yellow" if pct >= 40 else "red")
    print(f"  Progress: {c(bar, color)} {pct}%")
    print(f"  {stats['implemented']}/{stats['total']} implemented"
          f" · {stats['deferred']} deferred"
          f" · {stats['out_of_scope']} out-of-scope"
          f" · {stats['open']} open\n")

    # By tier
    by_tier = stats.get("by_tier", {})
    from .scoring import TIER_NAMES
    rows = []
    for tier in sorted(by_tier.keys(), key=int):
        tier_int = int(tier)
        ts = by_tier[tier]
        tier_pct = round(ts["done"] / ts["total"] * 100) if ts["total"] else 0
        filled_t = round(tier_pct / 100 * 15)
        bar_t = "█" * filled_t + "░" * (15 - filled_t)
        rows.append([
            f"T{tier}",
            TIER_NAMES.get(tier_int, "?"),
            bar_t,
            f"{tier_pct}%",
            f"{ts['done']}/{ts['total']}",
        ])

    print_table(
        ["Tier", "Type", "Progress", "%", "Done"],
        rows,
        [4, 10, 15, 5, 8],
    )
    print()


def cmd_show(args):
    """Show features, optionally filtered."""
    from .state import load_state

    sp = _get_state_path(args)
    state = load_state(sp)

    if not state["features"]:
        print(c("  No scan data. Run: pen-audit scan <file>", "yellow"))
        return

    features = list(state["features"].values())

    # Filter by status
    if args.status != "all":
        features = [f for f in features if f["status"] == args.status]

    # Filter by pattern
    if args.pattern:
        pat = args.pattern.lower()
        features = [f for f in features if (
            pat in f.get("detector", "").lower() or
            pat in f.get("name", "").lower() or
            pat in f.get("screen_id", "").lower() or
            pat in f.get("id", "").lower() or
            pat in f.get("summary", "").lower()
        )]

    if not features:
        print(c(f"  No features found matching '{args.pattern or 'all'}'", "yellow"))
        return

    print(c(f"\n  {len(features)} features:\n", "bold"))

    rows = []
    for f in sorted(features, key=lambda x: (x["tier"], x["detector"])):
        status_icon = {"open": "○", "implemented": "●", "deferred": "◐", "out_of_scope": "◌"}.get(f["status"], "?")
        rows.append([
            f"T{f['tier']}",
            status_icon,
            f["detector"][:12],
            f["summary"][:60],
        ])

    print_table(
        ["Tier", "St", "Detector", "Summary"],
        rows,
        [4, 2, 12, 60],
    )
    print()


def cmd_next(args):
    """Suggest next features to implement."""
    from .state import load_state
    from .scoring import TIER_WEIGHTS

    sp = _get_state_path(args)
    state = load_state(sp)

    open_features = [f for f in state["features"].values() if f["status"] == "open"]

    if args.tier:
        open_features = [f for f in open_features if f["tier"] == args.tier]

    if not open_features:
        print(c("  All features implemented! 🎉", "green"))
        return

    # Sort by tier (lower first = easier wins), then by detector
    open_features.sort(key=lambda f: (f["tier"], f["detector"], f["name"]))

    count = min(args.count, len(open_features))
    print(c(f"\n  Next {count} features to implement:\n", "bold"))

    for i, f in enumerate(open_features[:count], 1):
        print(f"  {i}. [{c(f'T{f["tier"]}', 'cyan')}] {f['summary']}")
        print(c(f"     ID: {f['id']}", "dim"))
    print()


def cmd_resolve(args):
    """Mark features as implemented/deferred/out_of_scope."""
    from .state import load_state, save_state, resolve_feature

    sp = _get_state_path(args)
    state = load_state(sp)

    total_resolved = []
    for pattern in args.patterns:
        resolved = resolve_feature(state, pattern, args.status)
        total_resolved.extend(resolved)

    if total_resolved:
        save_state(state, sp)
        print(c(f"  Resolved {len(total_resolved)} feature(s) as {args.status}:", "green"))
        for fid in total_resolved:
            print(f"    {fid}")
    else:
        print(c("  No matching open features found.", "yellow"))
    print()


def cmd_match(args):
    """Match features against a codebase to auto-resolve implemented ones."""
    from .state import load_state, save_state
    from .codebase_matcher import match_codebase

    sp = _get_state_path(args)
    state = load_state(sp)

    if not state["features"]:
        print(c("  No scan data. Run: pen-audit scan <file>", "yellow"))
        return

    dry_run = getattr(args, "dry_run", False)
    results = match_codebase(
        state,
        project_dir=args.project_dir,
        app_subdir=getattr(args, "app_subdir", ""),
        dry_run=dry_run,
    )

    if "error" in results:
        print(c(f"  Error: {results['error']}", "red"))
        return

    print(c(f"\npen-audit match {'(dry run)' if dry_run else ''}\n", "bold"))

    if results["matched"]:
        print(c(f"  Implemented ({results['total_matched']}):", "green"))
        for m in results["matched"]:
            route_tag = " [+route]" if m.get("has_route") else ""
            print(f"    {m['screen_name']}{route_tag}")

    if results["stub"]:
        print(c(f"\n  Stubs ({results['total_stub']}):", "yellow"))
        for s in results["stub"]:
            print(f"    {s['screen_name']} -> {s['page_path']}")

    if results["missing"]:
        print(c(f"\n  Missing ({results['total_missing']}):", "red"))
        for m in results["missing"]:
            print(f"    {m['screen_name']} (expected: /app/{m['expected_slug']})")

    if not dry_run and results["total_matched"] > 0:
        save_state(state, sp)
        print(c(f"\n  Auto-resolved {results['total_matched']} features as implemented", "green"))
    print()


def cmd_plan(args):
    """Generate development artifacts."""
    from .state import load_state

    sp = _get_state_path(args)
    state = load_state(sp)

    if not state["features"]:
        print(c("  No scan data. Run: pen-audit scan <file>", "yellow"))
        return

    fmt = args.format
    output_dir = Path(args.output) if args.output else None

    if fmt in ("markdown", "all"):
        from .formatters.markdown import generate_markdown
        md = generate_markdown(state)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "feature-inventory.md").write_text(md)
            print(c(f"  Written: {output_dir / 'feature-inventory.md'}", "green"))
        else:
            print(md)

    if fmt in ("routes", "all"):
        from .formatters.routes import generate_routes
        routes = generate_routes(state)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "routes.json").write_text(json.dumps(routes, indent=2))
            print(c(f"  Written: {output_dir / 'routes.json'}", "green"))
        else:
            print(json.dumps(routes, indent=2))

    if fmt in ("jira", "all"):
        from .formatters.jira import generate_jira_tasks
        tasks = generate_jira_tasks(state)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "jira-tasks.json").write_text(json.dumps(tasks, indent=2, default=str))
            print(c(f"  Written: {output_dir / 'jira-tasks.json'} ({len(tasks)} tasks)", "green"))
        else:
            print(json.dumps(tasks, indent=2, default=str))

    if fmt in ("stubs", "all"):
        from .formatters.stubs import generate_stubs
        stubs = generate_stubs(state)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            stubs_dir = output_dir / "stubs"
            stubs_dir.mkdir(parents=True, exist_ok=True)
            for stub in stubs:
                stub_path = stubs_dir / stub["path"]
                stub_path.parent.mkdir(parents=True, exist_ok=True)
                stub_path.write_text(stub["content"])
            print(c(f"  Written: {len(stubs)} page stubs to {stubs_dir}/", "green"))
        else:
            for stub in stubs:
                print(c(f"\n--- {stub['path']} ---", "cyan"))
                print(stub["content"])

    if fmt in ("tests", "all"):
        from .formatters.tests import generate_test_skeletons
        test_files = generate_test_skeletons(state)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            tests_dir = output_dir / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            for tf in test_files:
                test_path = tests_dir / tf["path"]
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(tf["content"])
            print(c(f"  Written: {len(test_files)} test skeletons to {tests_dir}/", "green"))
        else:
            for tf in test_files:
                print(c(f"\n--- {tf['path']} ---", "cyan"))
                print(tf["content"])

    print()


def main():
    parser = create_parser()
    args = parser.parse_args()

    commands = {
        "scan": cmd_scan,
        "status": cmd_status,
        "show": cmd_show,
        "next": cmd_next,
        "resolve": cmd_resolve,
        "match": cmd_match,
        "plan": cmd_plan,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(c(f"  Error: {e}", "red"), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
