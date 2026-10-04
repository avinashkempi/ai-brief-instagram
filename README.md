# AI Brief — free Instagram publisher

A free, image-only daily AI developments channel for Instagram Professional accounts. The workflow prepares a minimalist 1080 × 1350 card from public AI research and company RSS feeds, writes a source-linked caption, hosts the image on GitHub Pages, and publishes it with Meta's official Instagram API.

The initial publishing target is **8:05 a.m. India Standard Time**. There is no account Insights history yet, so this is a starting time rather than a claim that it is optimal. Review Instagram Insights after four weeks and adjust the schedule to when your followers are most active.

## Free operating plan

- Public GitHub repository, GitHub Actions standard hosted runners, and GitHub Pages for public image hosting.
- Python, Pillow, and PyNaCl are free open-source packages. No paid AI API, scheduler, image service, or Cloudflare account.
- Headlines and excerpts come directly from public RSS feeds; the image is composed from original shapes and typography. No third-party web photos are scraped or republished.
- The repository, cards, captions, and source links are public. Do not put credentials or private data in repository files.
- This design uses public-repository Actions and Pages. Keep paid features and billing upgrades disabled. The plan does not require a paid service.

## What it does each day

1. At **7:05 a.m. IST**, check the feeds listed in [sources.json](sources.json) for an eligible item from the last three days. Select the newest unseen item; if none qualifies, skip that day.
2. Create a consistent, minimalist image and a source-linked caption, then publish the image and metadata to the public Pages site.
3. At **8:05 a.m. IST**, publish that image using Meta's official Instagram API. Record the posted story to prevent duplicate posts on retries.
4. Refresh the long-lived Instagram token during the publishing run. If it changes, a repo-scoped GitHub token updates the stored Actions secret.

GitHub schedule events can be delayed during high load, so the schedule is not an exact-time guarantee. The publishing job skips the day if no current image package is available.

## One-time account connection

The public repository is already created at [github.com/avinashkempi/ai-brief-instagram](https://github.com/avinashkempi/ai-brief-instagram), and its project files are uploaded.

1. GitHub Pages is configured to use **GitHub Actions**. After the first prepare run deploys it, the public site will be at https://avinashkempi.github.io/ai-brief-instagram/.
2. In Meta for Developers, create an app, add **Instagram API with Instagram Login**, and register this redirect URI exactly: https://avinashkempi.github.io/ai-brief-instagram/oauth-callback/. Add your professional Instagram account as a tester if Meta requires it in development mode, then accept the invitation.
3. On your own computer, run **python auth.py** from this project folder. When prompted, enter the **Instagram App ID** and **Instagram App Secret** shown under **Set up Instagram business login** in the Instagram API setup. These are different from the main Meta App ID and secret. The helper prints an Instagram authorization URL, checks the returned OAuth state, requests the Instagram App Secret without echoing it, and exchanges the temporary authorization code locally. It does not save credentials to disk.
4. In the repository, open **Settings → Secrets and variables → Actions**. Add **IG_USER_ID** and **IG_ACCESS_TOKEN** using the values printed by the helper.
5. Create a fine-grained GitHub token restricted to this repository with **Actions secrets: read and write**, then save it as the **GH_SECRETS_TOKEN** Actions secret. The workflow uses it only if Meta rotates the Instagram token.
6. Once the Actions secrets are set, scheduled preparation and publishing run automatically. The first image will be built at the next 7:05 a.m. IST preparation run, then published at 8:05 a.m. IST if a new eligible story is available. Check the public preview at https://avinashkempi.github.io/ai-brief-instagram/current.json after the first deployment.
7. No daily approval or manual publish step is required. You may optionally run **Actions → AI Brief daily Instagram publishing → Run workflow → prepare** to prepare a preview sooner; do not choose **publish** unless you want to publish immediately.

Instagram Login supports Professional Business and Creator accounts and does not require a linked Facebook Page. This project requests **instagram_business_basic** and **instagram_business_content_publish**. See [Meta's Instagram API documentation](https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00).

## Tune the time

Use Instagram Insights to identify follower activity after four weeks of posts. Change the two cron expressions in [the workflow](.github/workflows/instagram-daily.yml) together, keeping the image preparation one hour before publishing. GitHub's schedule runner may start late.

## Files

- **pipeline.py** — RSS selection, card generation, caption, token refresh, and Instagram publishing.
- **auth.py** — one-time local OAuth helper; does not save the app secret or access token to disk.
- **sources.json** — public RSS feeds.
- **.github/workflows/instagram-daily.yml** — daily preparation and publication schedule.
- **assets/ai-brief-template.svg** — editable visual reference for the generated card.

## Cost and limits

The planned services and packages are available at $0 with this public-repository setup. The site and Instagram posts are public. This cannot guarantee uninterrupted posting: GitHub or Meta may change availability, scheduling, API limits, or account requirements. Workflow failures will appear in the repository's Actions tab. Scheduled runs may be late.
