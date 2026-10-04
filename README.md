# AI Brief — free Instagram publisher

A free, image-only daily AI developments channel for Instagram Professional accounts. The workflow selects 2–5 fresh stories from public RSS feeds, creates one consistent minimalist 1080 × 1350 image per story, writes a source-linked caption, hosts the images on GitHub Pages, and publishes them as one carousel with Meta's official Instagram API.

The initial publishing target is **8:05 a.m. India Standard Time**. There is no account Insights history yet, so this is a starting time rather than a claim that it is optimal. Review Instagram Insights after four weeks and adjust the schedule to when your followers are most active.

## Free operating plan

- Public GitHub repository, GitHub Actions standard hosted runners, and GitHub Pages for public image hosting.
- Python, Pillow, and PyNaCl are free open-source packages. No paid AI API, scheduler, image service, or Cloudflare account.
- Headlines and excerpts come directly from public RSS feeds; the image is composed from original shapes and typography. No third-party web photos are scraped or republished.
- The repository, cards, captions, and source links are public. Do not put credentials or private data in repository files.
- This design uses public-repository Actions and Pages. Keep paid features and billing upgrades disabled. The plan does not require a paid service.

## What it does each day

1. At **7:05 a.m. IST**, check the feeds listed in [sources.json](sources.json) for eligible items from the last three days. Select up to five newest unseen stories; skip if fewer than two qualify.
2. Create one uniform 4:5 minimalist image for each story and a caption with story summaries and links, then deploy the images to the public Pages site.
3. At **8:05 a.m. IST**, publish the images together as one carousel using Meta's official Instagram API. Record all included stories to prevent duplicate coverage on retries.
4. Refresh the long-lived Instagram token during the publishing run. If it changes, a repo-scoped GitHub token updates the stored Actions secret.

GitHub schedule events can be delayed during high load, so the schedule is not an exact-time guarantee. The publisher skips the day if fewer than two fresh stories are available or no current carousel package is ready.


## Music limitation

Instagram supports adding music to photo carousels in its app ([Meta announcement](https://about.fb.com/news/2023/08/music-and-collabs-on-instagram/)). The Instagram Login publishing API used here documents carousel publishing but no way to attach a licensed or trending music-library track ([Meta content-publishing docs](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing)). Therefore, scheduled carousels will publish as images without music. Adding a track from Instagram's music library would require a manual in-app step, so this cannot be fully automated with the current setup.

## One-time account connection

The public repository is already created at [github.com/avinashkempi/ai-brief-instagram](https://github.com/avinashkempi/ai-brief-instagram), and its project files are uploaded.

1. GitHub Pages is configured to use **GitHub Actions**. After the first prepare run deploys it, the public site will be at https://avinashkempi.github.io/ai-brief-instagram/.
2. In Meta for Developers, create an app, add **Instagram API with Instagram Login**, and register this redirect URI exactly: https://avinashkempi.github.io/ai-brief-instagram/oauth-callback/. Add your professional Instagram account as a tester if Meta requires it in development mode, then accept the invitation.
3. On your own computer, run **python auth.py** from this project folder. When prompted, enter the **Instagram App ID** and **Instagram App Secret** shown under **Set up Instagram business login** in the Instagram API setup. These are different from the main Meta App ID and secret. The helper prints an Instagram authorization URL, checks the returned OAuth state, requests the Instagram App Secret without echoing it, and exchanges the temporary authorization code locally. It does not save credentials to disk.
4. In the repository, open **Settings → Secrets and variables → Actions**. Add **IG_USER_ID** and **IG_ACCESS_TOKEN** using the values printed by the helper.
5. Create a fine-grained GitHub token restricted to this repository with **Actions secrets: read and write**, then save it as the **GH_SECRETS_TOKEN** Actions secret. The workflow uses it only if Meta rotates the Instagram token.
6. Once the Actions secrets are set, scheduled preparation and publishing run automatically. The first carousel will be built at the next 7:05 a.m. IST preparation run, then published at 8:05 a.m. IST if at least two new eligible stories are available. Check the public preview at https://avinashkempi.github.io/ai-brief-instagram/current.json after deployment.
7. No daily approval is required for scheduled posts. If you manually run **Actions → AI Brief daily Instagram publishing → Run workflow → prepare**, it prepares and deploys the image, then publishes it automatically. Choose **publish** only to publish today's ready package without rebuilding it. The publisher checks for an already-recorded post for the date to avoid duplicates.

Instagram Login supports Professional Business and Creator accounts and does not require a linked Facebook Page. This project requests **instagram_business_basic** and **instagram_business_content_publish**. See [Meta's Instagram API documentation](https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00).

## Tune the time

Use Instagram Insights to identify follower activity after four weeks of posts. Change the two cron expressions in [the workflow](.github/workflows/instagram-daily.yml) together, keeping the image preparation one hour before publishing. GitHub's schedule runner may start late.

## Files

- **pipeline.py** — RSS selection, carousel card generation, source-linked caption, token refresh, and Instagram publishing.
- **auth.py** — one-time local OAuth helper; does not save the app secret or access token to disk.
- **sources.json** — public RSS feeds.
- **.github/workflows/instagram-daily.yml** — daily preparation and publication schedule.
- **assets/ai-brief-template.svg** — editable visual reference for the generated card.

## Cost and limits

The planned services and packages are available at $0 with this public-repository setup. The site and Instagram posts are public. This cannot guarantee uninterrupted posting: GitHub or Meta may change availability, scheduling, API limits, or account requirements. Workflow failures will appear in the repository's Actions tab. Scheduled runs may be late.
