# Security and publication checklist

## Never commit

- `.env`
- API keys or tokens
- temporary workshop credentials
- raw secrets copied from terminal/browser screenshots
- private Langfuse user/session identifiers
- private Slack/Linear/customer data
- local database volumes

## Screenshots

Before publishing any screenshot:

1. crop or redact API keys and tokens
2. crop or redact user/session identifiers
3. remove local usernames or paths when unnecessary
4. remove private company/workshop data
5. confirm the screenshot contains no hidden browser autofill or account information

## Credential incident note

A workshop Anthropic key appeared visibly in one captured screenshot. That screenshot must never be published. Treat any visible credential as compromised and revoke/rotate it when possible.

## Git hygiene

Run before every public push:

```bash
git status
git diff --cached
```

Optional secret scan:

```bash
gitleaks detect --source .
```
