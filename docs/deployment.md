# Public deployment

Deployment pending. No authenticated Hugging Face Spaces, Render, Fly.io or Railway account was available in the workspace. The GitHub source and deployment files are published.

## Hugging Face Spaces

1. Sign in and open [Create a Space](https://huggingface.co/new-space).
2. Choose your owner account. Set **Space name** to **palimpsest** (or a unique variant), **License** to **MIT** for the project source, **SDK** to **Docker**, template to **Blank**, hardware to **CPU Basic** and visibility to **Public**.
3. Open the new Space's **Files** tab and copy its HTTPS Git URL. From the Palimpsest repository run the following, replacing the placeholder with that URL. Authenticate using a Hugging Face write token when prompted by Git's credential manager.

   ```sh
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/palimpsest
   git push space main
   ```

   If the Space initialized its own README commit, preserve both histories. Use a separate worktree or clone for the merge.

   ```sh
   git fetch space main
   git worktree add -b space-deploy ../palimpsest-space origin/main
   cd ../palimpsest-space
   git merge -s ours --allow-unrelated-histories space/main -m "Merge Space initialization"
   git push space HEAD:main
   ```

4. The repository README contains **sdk: docker** and **app_port: 7860**. Under **Settings → Variables and secrets**, set **PALIMPSEST_DEMO_ONLY=1**, **PALIMPSEST_DATA=/tmp/palimpsest** and **PORT=7860**. These are already the image defaults. The service requires no secrets.
5. Wait for **Running**. Open the app directly and copy its actual public HTTPS URL. Restarting the free container resets SQLite. Bundled files load again on startup. A sleeping Space may display its own wake screen before the application loads.

## Render alternative

1. Sign in to [Render](https://dashboard.render.com/) and connect your GitHub account.
2. Select **New → Blueprint**, then connect **hannielvinu/Palimpsest** and choose branch **main**. The file **render.yaml** declares one Docker web service on the free plan.
3. Confirm Dockerfile **./Dockerfile**, health path **/healthz**, and variables **PALIMPSEST_DEMO_ONLY=1** and **PALIMPSEST_DATA=/tmp/palimpsest**. Render supplies **PORT**.
4. Deploy, wait for the health check, then open the HTTPS URL shown in the dashboard. The free service can sleep and uses ephemeral storage.

[Docker Spaces setup](https://huggingface.co/docs/hub/spaces-sdks-docker) · [Render Docker](https://render.com/docs/docker) · [Render free service behavior](https://render.com/docs/free)

## Verify the published instance

```sh
python scripts/smoke_http.py https://YOUR-ACTUAL-HOST
python -m playwright install chromium
python scripts/capture_screens.py --url https://YOUR-ACTUAL-HOST --out .scratch/public-check
```

The smoke scripts exercise bundled cases, revision recovery, decision, dossier, audit and purge against the supplied URL. Verify the browser and copy the live link to README and the final slide. Pass the verified URL as **--live-url** to **presentation/build.py** to generate the QR. Re-export the PDF and re-upload both deck files after this update.

For a local single-user container, use **docker compose up --build** and open **http://127.0.0.1:7860**. The compose volume retains cases across restarts.
