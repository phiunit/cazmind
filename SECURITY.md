# Security

CazMind decides who can see what inside a company's knowledge, so permission and session bugs are the ones we care about most.

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's private reporting instead: the **Security** tab of this repo, then **Report a vulnerability**. If that isn't available, email phi@phiunit.com with "CazMind security" in the subject.

Include what you found, how to reproduce it, and what an attacker could see or do. You'll get a reply within 5 business days. Once a fix ships, we'll credit you in the release notes unless you'd rather we didn't.

## What counts

The things we most want to hear about:

- A role seeing a passage above its clearance, or a hidden passage changing the ranking of visible ones.
- A forged, tampered, or expired session token being accepted.
- Any path that ends up signing tokens with a predictable secret.

## Supported versions

Only the latest release gets security fixes while the project is pre-1.0.
