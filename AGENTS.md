# Repository working instructions

## Scope

- Edit only this engineering-document-acceptance project. The adjacent ai-dzpp project is a read-only reference.
- `main` is Skill + scripts only (AGH Agent reads Skills for audit spot-check and document drafting).
- The full evidence-pipeline system lives on branch `system` (v1.0.x). Do not reintroduce `app/` unless the user asks.
- Never commit API keys, .env files, virtual environments, runtime databases, model payload caches, or generated output documents.

## Version updates and Git

- The user prefers updates on main. When asked to push, append the current round of changes to main using a separate, descriptive commit.
- Keep each completed implementation/fix round independently reviewable; do not combine unrelated future rounds into a single catch-all commit.
- Do not create a feature branch by default. Create another branch only if the user asks.
- Preserve published commits. Do not amend, rebase, squash, or force-push published history unless the user explicitly requests that operation.
- Fetch before pushing, incorporate remote updates without discarding them, and verify the pushed commit on the remote.
- Record meaningful versions in CHANGELOG.md; version tags point to actual snapshots. Do not fabricate intermediate development commits retroactively.
- Run checks appropriate to code changes. Skill-only rounds: smoke `audit_prepare.py` and document `prepare` when scripts change.
