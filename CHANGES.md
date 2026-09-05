# Profile Intelligence system — what changed and why

## Removed
- `dashboard/` + `.github/workflows/deploy-dashboard.yml` — GitHub Pages static site (a separate user-facing app).
- `live-dashboard/` — Express + WebSocket server, GitHub App webhook receiver, Dockerfile. Required standing hosting; was also the only source of real cross-repo event detection.
- `scripts/generate_profile_dashboard.py` + `.github/workflows/profile-dashboard.yml` — superseded by the modular `scripts/collect_stats.py` / `scripts/render_dashboard.py` pair and `.github/workflows/profile-intelligence.yml`.

## Added
- `scripts/lib/github_client.py` — REST + GraphQL client, layered token resolution (App token → PAT → default token).
- `scripts/lib/stats.py` — pure computation: language aggregation, streak math, multi-year lifetime totals, activity diffing.
- `scripts/collect_stats.py` — cheap-phase/expensive-phase orchestration. Most ticks cost one API call and exit.
- `scripts/render_dashboard.py` — glassmorphism v2 renderer, reads `data/stats.json`, writes `assets/widgets/profile-dashboard.svg`.
- `.github/workflows/profile-intelligence.yml` — the one workflow. schedule + repository_dispatch + workflow_dispatch + push.
- `templates/notify-profile.yml` — copy-paste reusable workflow for other repos, for instant (seconds, not minutes) dispatch.
- `data/stats.json` — committed snapshot of the last recalculation. Human-readable, doubles as a small stats API.
- `.state/` — event cursor + per-year contribution cache.
- `docs/PROFILE_INTELLIGENCE.md` — architecture, security model, setup runbook.

## Fixed
- `assets/widgets/profile-dashboard.svg` was being generated and committed every run but was **never referenced anywhere in `README.md`** — the whole pipeline was rendering into a void. It's now embedded directly under the header.
- The "current period" contribution figure (a rolling ~1 year GraphQL default) is now genuinely recalculated lifetime totals across every year of the account, plus current/longest streak — neither of which the old script computed.

## Left alone (out of scope, flagged in docs/PROFILE_INTELLIGENCE.md)
- `scripts/generate_widgets.py`, `scripts/wrap_snake.py`, and the non-dashboard SVGs under `assets/widgets/` (`github-snake*.svg`, `top-languages.svg`, `tech-stack.svg`, `profile-stats.svg`) — also generated, also not referenced by `README.md` in the repo state this was built from. Worth a follow-up pass.

## Before merging
- `data/stats.json` currently ships with your last known real numbers (repos, followers, languages, lifetime commit/PR counts) reshaped into the new format — but the streak figures (4d current / 27d longest) are **placeholders**; the old system never computed streaks, so there was nothing real to carry over. The first workflow run replaces this file with a fully live, recalculated snapshot.
- Nothing here required a token to build or test. Optional upgrades (private-repo contribution counts, instant cross-repo dispatch) are documented in `docs/PROFILE_INTELLIGENCE.md` and require no code changes — only secrets.
