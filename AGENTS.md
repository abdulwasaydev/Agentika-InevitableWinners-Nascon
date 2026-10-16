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
- Arman now integrates backend and frontend on `arman/backend-foundation` at the user's direction. Preserve Wasay's original `wasay/frontend-foundation` branch and give credit for his imported frontend foundation.
- Build locally first. Do not deploy, create cloud resources, access SocietyOS, or apply Supabase migrations automatically. Store credentials only in local environment variables.
- The decisions in the pasted backend task override conflicting stack and deployment suggestions in `docs/VERITAS_CODEX_CONTEXT.md`.
