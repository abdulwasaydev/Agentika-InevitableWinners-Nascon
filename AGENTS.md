# Hackathon collaboration

- This repository is `abdulwasaydev/Agentika-InevitableWinners-Nascon`.
- Arman works on `arman/backend-foundation`; Abdul Wasay works on his own frontend branch. Change branches only when the user explicitly directs it.
- Treat `main` as the shared integration branch. Do not push or merge into it without explicit user direction.
- Before a substantial task, inspect the working tree and fetch the latest changes from `origin`.
- When `origin/main` exists, update local `main` by fast-forward only, then bring those changes into the active work branch safely.
- If a merge conflict appears, explain the conflicting changes before resolving it. Do not guess or overwrite files blindly.
- Preserve existing working code. Ask before deleting or rewriting teammate code.
- Never force push, reset away commits, or discard someone else's changes.
- Make small, logical commits with clear messages. Keep the repository buildable where possible and run appropriate checks.
- Push work branches to `origin` with their matching upstream branches when appropriate.
- For integration, commit and push the intended work first, then report the commits and files changed. Merge into `main` only with explicit user approval.
- Keep explanations to the user within 20 lines unless the user asks for a concept to be explained.
- Arman now integrates backend and frontend on `arman/backend-foundation` at the user's direction. Credit Wasay's imported frontend foundation; his original checkpoint commit is recoverable at tag `archive/wasay-frontend-foundation-20261017` after the user-requested branch cleanup.
- Build locally first. Do not deploy, create cloud resources, access SocietyOS, or apply Supabase migrations automatically. Store credentials only in local environment variables.
- The decisions in the pasted backend task override conflicting stack and deployment suggestions in `docs/VERITAS_CODEX_CONTEXT.md`.

## Current handoff (2026-10-17)

- Continue on `arman/backend-foundation`, the integration branch. The requested long-term branch set is `main`, `arman/backend-foundation`, and `wasay-work`. The old `arman-work` branch is still GitHub's default until the user changes it to `main`; only then may it be deleted. Its unique commit is preserved at tag `archive/arman-work-20261017`. Do not switch branches, merge into `main`, or force push to accomplish cleanup.
- The current branch has a locally verified React/Vite frontend, FastAPI backend, separate Supabase PostgreSQL database, Gemini-assisted GitHub policy scan, full pasted-policy input, citation-bound support/challenge assessments, durable human review, and strict Guardian release decisions. The default UI mode is Live API; Synthetic demo is explicitly labeled. See `README.md` and `docs/DEMO_READINESS.md` for verified limits.
- The local setup uses ignored `backend/.env` for `DATABASE_URL` and Gemini settings. Never print, copy into Git, or request its secrets. The GitHub policy snapshot lives in ignored `backend/data/`; run `backend/scripts/download_github_policy.py` to refresh it. A full pasted document does not need the snapshot. No new schema migration is needed beyond `0003_comparison`.
- Deployment to Clouds by Alternate Futures has **not** happened. There is no Dockerfile or production frontend serving arrangement yet, and the API has no user authentication. Follow the ordered deployment handoff in `README.md`; implement and verify packaging and access control before exposing the service. Do not invent provider-specific dashboard steps or claim a public link until the provider is configured and tested.
- The user will enter secrets only in ignored local files and manually apply reviewed Supabase SQL. Never apply remote migrations, create cloud resources, deploy, or spend credits without their explicit instruction. On a new agent/session, first inspect `git status`, fetch `origin`, confirm the active/upstream branch, read this file and `README.md`, then check `/health` without revealing environment values.
