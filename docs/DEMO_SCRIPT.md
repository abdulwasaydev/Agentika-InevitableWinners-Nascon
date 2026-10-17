# Six-minute local demo walkthrough

## Real GitHub privacy statement

1. In ignored `backend/.env`, set `LLM_PROVIDER=gemini`, `LLM_API_KEY`, and `LLM_MODEL=gemini-3.8-flash` as described in [backend setup](../backend/README.md), then restart FastAPI. Confirm `/health` reports `database_ready: true`.
2. Open [GitHub's published privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). At `http://127.0.0.1:5173/`, choose **Live API**, tick **Scan GitHub's privacy statement**, and paste the entire document into the full-policy field. The UI saves this draft for this browser session. It labels your paste as user supplied, so its authenticity and completeness are not verified by Veritas.
3. Select **"GitHub never uses personal data to train AI models."** and choose **Scan pasted policy**. Open the claim and inspect the **In favor** and **Against** notes, exact quotes, and pending review. The local run on 2026-10-17 found a cited challenge. Record a **Disputed** human review; Guardian should continue to hold.
4. Return to **Policy Check**; the pasted text should still be present. Select **"GitHub collects email addresses when users create an account."** and scan again. The local run found cited support. Approve it with a written rationale only if the fresh quote directly supports it; Guardian should change from hold to pass.
5. Return again and scan **"GitHub shares personal data with service providers."**. The local run found cited support and left it pending human review. Check both agent notes and the backend release gate. Fresh model output can vary; inspect each new result rather than assuming these outcomes.

If the model call fails, show the explicit failure. Do not switch to synthetic results while describing a real-policy scan. Leave the paste field empty to scan the locally downloaded GitHub Docs snapshot instead; refresh it first with `.\.venv\Scripts\python backend\scripts\download_github_policy.py` from the repository root. That option can show an authenticated GitHub source link.

## Explicit simulation

Select **Synthetic demo** in the top bar only when you want to show an interface rehearsal without Gemini or Supabase. This mode labels its sources and results as fictional. It does not replace a failed Live API scan. The Live API form accepts manually supplied policy text but no longer offers fictional subscription prefills.
