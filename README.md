# AI Brief — free Instagram publisher

This starter implementation prepares one original, image-only AI news card each morning and schedules it for Instagram at 8:05 p.m. India Standard Time. **AI Brief** is a provisional name.

## $0 operating design

- Public GitHub repository, GitHub Actions standard hosted runners, and GitHub Pages for public image hosting.
- Python, Pillow, and PyNaCl are free open-source packages.
- Public official RSS feeds and arXiv provide the candidate stories.
- Instagram publishing uses Meta's official API. No paid scheduler, paid AI model, Cloudflare account, or other paid service is part of this design.
- No LLM is called: the headline comes from the source, and the caption is built from the source excerpt and link. This keeps the recurring cost at $0 but makes the writing more templated. The image is drawn from scratch; no internet photo is reused.

The repository and generated cards/captions must be public for GitHub Pages to host the JPEG on GitHub Free. That is appropriate for a public Instagram post. Keep all Meta tokens and the GitHub secret-management token in GitHub Actions secrets. Never commit them or paste them into chat. Use standard runners only. GitHub documents standard runner use as free for public repositories and Pages as available on GitHub Free public repositories ([Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [Pages setup](https://docs.github.com/en/pages/getting-started-with-github-pages)). Scheduled workflows can run late during GitHub load, so 8:05 p.m. is a target rather than an exact-time guarantee ([schedule event limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)).

## Daily workflow

1. **06:05 IST:** read the source feeds in `sources.json`; consider new items from the last three days and skip links already published.
2. Select the newest eligible item, favoring primary lab announcements on timestamp ties. If no new source item is available, publish nothing that day.
3. Generate a 1080 × 1350 JPEG in the consistent dark, minimalist design; write the headline, short feed excerpt, accessible alt text, and source link into `docs/current.json`.
4. Deploy the image and package to GitHub Pages so Meta can fetch a public HTTPS JPEG.
5. **20:05 IST:** refresh the long-lived Instagram token, create an image container with Meta's API, wait for image processing, publish it, and record the media ID. A published-state file prevents duplicate posts on retries.
6. Use Instagram Insights to adjust the posting window after four weeks. The starting time is a test; no generic timing chart can promise maximum engagement.

Instagram's official API accepts professional accounts and uses a create-container-then-publish flow. Instagram Login does not require a linked Facebook Page; this setup asks only for `instagram_business_basic` and `instagram_business_content_publish` ([Meta Instagram API collection](https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00)).

## One-time setup to activate it

1. Create a **public** GitHub repository and upload this project. Enable GitHub Actions and set Pages to deploy with GitHub Actions.
2. In Meta for Developers, create an app, add Instagram API with Instagram Login, and configure the redirect URL `https://GITHUB-OWNER.github.io/REPOSITORY/oauth-callback/` using your actual repository owner and name. Add your Instagram profile as an app tester if Meta requires it in development mode, then accept the invitation.
3. Run `python auth.py` on your computer. It prints a Meta sign-in URL, exchanges the temporary code locally, asks for your app secret without echoing it, and prints the long-lived token and Instagram user ID. Add `IG_ACCESS_TOKEN` and `IG_USER_ID` in repository Settings → Secrets and variables → Actions. The helper does not save credentials to disk. Do not share them here.
4. Create a fine-grained GitHub token restricted to this repository with permission to write Actions secrets, and store it as `GH_SECRETS_TOKEN`. The publisher uses it only to replace a refreshed Instagram token when Meta returns a different value.
5. Manually run the `prepare` workflow, verify the preview at the Pages URL, then run the `publish` workflow for a one-time authorized test post. Scheduled posting is active once the workflow is on the default branch and enabled.

The daily runs need no manual approval once enabled. A $0 service cannot guarantee immediate recovery if GitHub/Meta changes, rate-limits, or disables an account; failures appear in GitHub Actions and the workflow should be set to notify you on failure. GitHub scheduled work may be delayed. Keep spending disabled in billing settings; the plan relies on public-repository standard runners and GitHub Free Pages.

## Files

- `pipeline.py` — feed selection, original JPEG composition, caption, token refresh, and Instagram publishing.
- `auth.py` — one-time local OAuth helper; keeps the app secret and returned token out of chat and does not save them to disk.
- `sources.json` — editable public RSS source list.
- `.github/workflows/instagram-daily.yml` — 06:05 IST prepare and 20:05 IST publish schedules.
- `assets/ai-brief-template.svg` — editable design reference.

## Still needed

The project is ready for a public GitHub repository and account authorization. This workspace has no connected GitHub or Meta account, so it cannot create the external repository, accept Meta OAuth, or activate the schedule. Those are one-time setup steps; daily posting will be automatic after they are complete.
