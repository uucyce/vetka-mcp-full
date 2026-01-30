# VETKA Commit Checklist

## Before Every Commit:

### Code Quality
- [ ] New files have `@status`, `@file`, `@lastAudit` headers
- [ ] No duplicate function names (`grep -rh "^def " src/ | sort | uniq -d`)
- [ ] If adding module - added proper imports
- [ ] If removing module - removed ALL references

### Testing
- [ ] `python3 -m py_compile main.py` passes
- [ ] Server starts: `python3 main.py`
- [ ] No console errors on `/3d` route
- [ ] Basic functionality works

### Documentation
- [ ] `docs/DEPENDENCY_MAP.md` updated (if changed routes/imports)
- [ ] Markers added for any TODO/DEPRECATED code
- [ ] Commit message follows format: `Phase X.Y: Description`

### Security (if applicable)
- [ ] No hardcoded credentials
- [ ] Input validation on new endpoints
- [ ] Rate limiting on expensive operations

---

## Commit Message Format
```
Phase X.Y: Short description

- Detail 1
- Detail 2

Verified by: [model names if AI-assisted]
```

---

## Quick Audit Before Commit
```bash
# Run the audit script
./scripts/audit.sh

# Check syntax
python3 -m py_compile main.py

# Count lines
wc -l main.py
```

---

## Emergency Rollback
```bash
# View recent commits
git log --oneline -10

# Revert last commit (keeps changes staged)
git reset --soft HEAD~1

# Hard reset (discards changes)
git reset --hard HEAD~1
```
