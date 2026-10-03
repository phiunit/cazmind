# Contributing

Thanks for taking a look. A few ground rules keep this small and trustworthy.

## The bar

- **Standard library only.** No runtime dependencies. If a change needs one, open an issue first so we can talk it through.
- **Tests with every change.** Run `python3 -m unittest discover -s tests -v` before you push. Anything touching `access.py`, `search.py`, or `session.py` needs a test that fails without your change.
- **Privacy property stays intact.** A passage a role can't see must never appear in its results and must never change the scores of passages it can see. The tests in `tests/test_search.py` guard this. Don't weaken them to get a change through.
- **Small pull requests.** One idea per PR is easiest to review.

## Sign your commits (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/) instead of a contributor license agreement. It's a one-line statement that you wrote the change, or otherwise have the right to submit it under this project's license.

Add it by committing with `-s`:

```sh
git commit -s -m "Fix chunking for long headings"
```

That appends a line like `Signed-off-by: Your Name <you@example.com>` to the commit. PRs without it can't be merged.

## Reporting security issues

Not in public issues, please. See [SECURITY.md](SECURITY.md).
