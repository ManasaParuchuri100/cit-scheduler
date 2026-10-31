# Third-party software

| Library | Used for | Licence |
|---|---|---|
| Google OR-Tools (CP-SAT) | Weekly timetable, minimal-move repair, exam scheduling (`cit/timetable.py`, `cit/exams.py`) | Apache-2.0 |
| FastAPI | Web API (`cit/api.py`) | MIT |
| Uvicorn | Web server | BSD-3-Clause |
| Anthropic Python SDK | Optional: reading plain-language room requests when `ANTHROPIC_API_KEY` is set (`cit/parser.py`) | MIT |
| Source Serif 4 (variable) | Display typeface, bundled in `web/fonts/` (no network needed) | SIL OFL 1.1 |
| DM Sans (variable) | Body typeface, bundled in `web/fonts/` | SIL OFL 1.1 |
| Playwright (tests only) | Click-through tests in `tests/` | Apache-2.0 |

The website has no JavaScript framework and no build step. Icons are hand-written inline SVG paths.
`validator.py` is the organisers' official checker, included unchanged.
