# spec-driven-dev

A skill-driven development framework for spec-driven development workflow.

## Overview

This project provides a structured approach to development through specification-first methodology, featuring evaluation prompts, scripts, and comprehensive references.

## Project Structure

```
spec-driven-dev/
├── SKILL.md              # Main skill definitions
├── CHANGELOG.md          # Version changelog
├── assets/               # Templates and assets
│   ├── agents-md-template.md
│   ├── change-spec-template.md
│   ├── constitution-template.md
│   ├── execution-plan-template.md
│   ├── feature-spec-template.md
│   ├── project-spec-template.md
│   ├── spec-skeleton-template.md
│   └── tasks-template.md
├── demo-video/           # Demo videos and voiceovers
├── evals/                # Evaluation datasets
├── references/           # Development guides
│   ├── anti-spec-slop.md
│   ├── calibration-guide.md
│   ├── code-consistency-guide.md
│   ├── golden-combo-guide.md
│   ├── openspec-guide.md
│   ├── spec-drift-detection.md
│   ├── spec-first-guide.md
│   ├── spec-kit-guide.md
│   ├── spec-to-code-bridge.md
│   ├── spec-writing-guide.md
│   └── superpowers-guide.md
├── scripts/              # Utility scripts
│   ├── check-code-consistency.py
│   ├── check-env.py
│   ├── detect-spec-drift.py
│   ├── generate-execution-plan.py
│   ├── peer-review-spec.py
│   ├── run-evals.py
│   └── validate-spec.py
b��── test-prompts.json     # Test prompts for evaluation
```

## Features

- **Spec-First Development**: Write specifications before writing code
- **Spec Drift Detection**: Automatically detect deviations from specifications
- **Code Consistency Checking**: Ensure code consistency across the project
- **Evaluation Framework**: Built-in evaluation prompts and test datasets
- **Peer Review Support**: Scripts for spec peer review workflow

## Getting Started

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Check environment:
```bash
python scripts/check-env.py
```

3. Validate your spec:
```bash
python scripts/validate-spec.py
```

## Scripts

| Script | Description |
|--------|-------------|
| `check-env.py` | Check development environment setup |
| `validate-spec.py` | Validate specification documents |
| `detect-spec-drift.py` | Detect drift between spec and implementation |
| `check-code-consistency.py` | Check code consistency |
| `generate-execution-plan.py` | Generate execution plan from spec |
| `peer-review-spec.py` | Run peer review on specifications |
| `run-evals.py` | Run evaluation tests |

## License

MIT License
