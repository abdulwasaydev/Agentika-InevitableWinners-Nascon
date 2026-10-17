# Six-minute local demo walkthrough

## Real GitHub privacy statement

1. In ignored `backend/.env`, set `LLM_PROVIDER=gemini`, `LLM_API_KEY`, and `LLM_MODEL=gemini-3.5-flash-lite` as described in [backend setup](../backend/README.md), then restart FastAPI. Confirm `/health` reports `database_ready: true`.
2. Open [GitHub's published privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). At `http://127.0.0.1:5173/`, choose **Live API**. Type your own claim, then paste the entire document into **Full privacy policy**. There is no GitHub preset or claim suggestion in the interface. The UI saves the pasted draft for this browser session. It labels your paste as user supplied, so its authenticity and completeness are not verified by Veritas.
3. Choose **Scan pasted policy**. Open the claim and inspect the **In favor** and **Against** notes, exact quotes, and pending review. A prior local run on 2026-10-17 with a no-training claim found a cited challenge. Record a **Disputed** human review if the fresh evidence supports that decision; Guardian should continue to hold.
4. Return to **Policy Check**; the pasted text should still be present. Type a second claim about account email collection and scan again. A prior local run found cited support. Approve it with a written rationale only if the fresh quote directly supports it; Guardian should change from hold to pass.
5. Return again and type a third claim about sharing data with service providers. The prior local run found cited support and left it pending human review. Check both agent notes and the backend release gate. Fresh model output can vary; inspect each new result rather than assuming these outcomes.

If the model call fails, show the explicit failure. Do not switch to synthetic results while describing a real-policy scan. Leaving the paste field empty submits a general text check; it does not scan the locally downloaded GitHub snapshot.

## Explicit simulation

Select **Synthetic demo** in the top bar only when you want to show an interface rehearsal without Gemini or Supabase. This mode labels its sources and results as fictional. It does not replace a failed Live API scan. The Live API form accepts manually supplied policy text but no longer offers fictional subscription prefills.
