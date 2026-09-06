# Contributing to Company AI Workbench

Thank you for contributing to **Company AI Workbench**! To ensure enterprise-grade reliability, local-first safety, and compliance with our **14 Engine Constitution Invariants**, we enforce a formal Git development workflow:

```
[Upstream: master]  <--- Protected Mainline
       │
     (Fork)
       │
[Origin: your-fork]
       │
  (Branch: feat/xxx) ───> [Push to Fork] ───> [Create PR] ───> [GitHub Actions CI/CD] ───> [Review & Merge]
```

---

## 1. Formal Workflow Standards

1. **`master` Mainline Protection**:
   - Direct `git push` to `master` is strictly prohibited.
   - All code enters `master` exclusively via Pull Requests (PRs) originating from forks or isolated branches.
2. **Fail-Closed Verification**:
   - Invariant 9: No unaccepted or unverified code reaches the `master` branch.
   - Invariant 11: Verifiers must be independent of builders (no same-provider collusion).
   - Invariant 14: Automated acceptance is limited to `low` risk tickets.
3. **CI/CD Quality Gate**:
   - All 135 automated unit, integration, and extreme penetration tests must pass 100% on both Linux and Windows.

---

## 2. Step-by-Step Development Guide

### Step 1: Fork the Repository
Fork `Josh404DR/company-ai-workbench` to your GitHub account:
```bash
gh repo fork Josh404DR/company-ai-workbench --clone=true
cd company-ai-workbench
```

Ensure upstream remote is configured:
```bash
git remote -v
# origin   https://github.com/<your-username>/company-ai-workbench.git (fetch/push)
# upstream https://github.com/Josh404DR/company-ai-workbench.git (fetch/push)
```

If `upstream` is missing:
```bash
git remote add upstream https://github.com/Josh404DR/company-ai-workbench.git
```

### Step 2: Create a Feature Branch
Always sync with upstream `master` before branching:
```bash
git checkout master
git pull upstream master
git checkout -b feat/your-feature-name
```
Branch naming conventions:
- `feat/<feature-description>`
- `fix/<bug-description>`
- `test/<test-description>`
- `docs/<doc-update>`

### Step 3: Implement & Test Locally
Set up your local environment and run the test suite:
```bash
# Windows
$env:PYTHONPATH="src;prototype"
python -m pytest tests -v

# Linux / macOS
export PYTHONPATH="src:prototype"
python -m pytest tests -v
```

All 135 tests must pass before opening a PR:
```bash
# Also run the Architecture Council extreme penetration test suite:
python -m pytest tests/test_extreme_council.py -v
```

### Step 4: Commit Your Changes
Write clear, conventional commit messages:
```bash
git add .
git commit -m "feat(module): descriptive explanation of changes"
```

### Step 5: Push to Your Fork
```bash
git push -u origin feat/your-feature-name
```

### Step 6: Create a Pull Request (PR)
Create a PR against `upstream/master`:
```bash
gh pr create --base master --title "feat: your feature title" --body-file .github/pull_request_template.md
```
Or open the PR via the GitHub Web UI.

### Step 7: CI/CD Pipeline & Invariant Gate
Upon opening a PR, the GitHub Actions CI/CD pipeline triggers automatically:
1. **`test-and-verify`**: Runs the 135-test suite across Ubuntu and Windows on Python 3.12 and 3.13.
2. **`invariant-gate`**: Audits compliance with Invariants 9, 11, and 14.

### Step 8: Review & Merge
- Pull Requests require review and approval from **Josh** (`Josh404DR`) and Architecture Council sign-off.
- Once CI is green and approvals are recorded, the PR is merged into `master`.

---

## 3. Need Help?
- File an Issue: [GitHub Issues](https://github.com/Josh404DR/company-ai-workbench/issues)
- Read Architecture Constitution: [`docs/COUNCIL_REVIEW.md`](docs/COUNCIL_REVIEW.md)
