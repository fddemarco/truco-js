# Deployment

The app runs on free tiers. The database is **Neon** Postgres. **Vercel** serves both the SPA (static files) and the API (FastAPI as a Python function). Since Vercel's free plan has no password protection, the app has its own password gate.

```
browser ──▶ Vercel ─┬─ /*      static SPA (frontend/build)
                    └─ /api/*  api/index.py → FastAPI (backend/app) ──▶ Neon Postgres
```

`vercel.json` holds the Vercel side:
- the build: `pnpm build` in `frontend/`;
- the Python function: `api/index.py`, which bundles `backend/app/`;
- the rewrites: `/api/*` goes to the function, and everything else falls back to `index.html`;
- the headers: `/avatars/*` and `/cards/*` are cached for a year. Their URLs carry a hash of the art (`?v=`), so new art from `pnpm import-art` reaches players on the next deploy.

Python dependencies come from the root `requirements.txt` (`make gen-reqs`), and the Python version from `.python-version`.

The API is stateless (see `backend/CLAUDE.md`). Nothing is kept in memory between requests, and clients poll, so each request can run on a fresh serverless instance.

## 1. Database (Neon)

The repo is linked to the Neon project `muddy-morning-01990588` (branch `production`) through `.neon`, which is gitignored. `neon.ts` declares what the project needs: Postgres only, which every Neon branch already has, plus a policy that makes new branches expire after 7 days.

```sh
pnpm add -g neon@latest   # the Neon CLI
neon login                # in WSL, open the printed URL in the Windows browser if none opens
neon deploy               # applies neon.ts and writes the branch's env vars to .env.local
```

`.env.local` gets the branch's `DATABASE_URL`. The app doesn't read that file, so `make dev` keeps using local SQLite. The file only gives you the connection string.

**Use the pooled connection string** for Vercel. Its host contains `-pooler`. You can also find it in the Neon console under **Connect**, with connection pooling on. Serverless functions open a connection per request, and the pooler absorbs that.

Tables are created on the first request, and there are no migrations:
- A new nullable column, or a NOT NULL one with a constant default, is added automatically.
- Any other schema change needs the table dropped. Locally, `make clean` does that.

The analytics tables (`GET /api/analytics/win-rates`) are filled by an experiment, not by the app. Load them once into the branch the deploy uses, and again after the engine or the bots' card play changes:

```sh
DATABASE_URL='<the pooled URL>' make win-rates   # about 10 minutes; replaces the previous results
```

## 2. Hosting (Vercel)

1. **Import the repo** in Vercel (Add New → Project). Keep the repo root as the root directory: `vercel.json` sets everything else.
2. **Add the environment variables** in Settings → Environment Variables, for both **Preview** and **Production**:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon's pooled connection string for the `production` branch. `postgres://` URLs work as they are. |
   | `STATE_KEY` | `openssl rand -base64 32`. It signs the game state stored in the database, and the API won't start without it. A new key drops the running games and logs everyone out. |
   | `ACCESS_PASSWORD` | The one password players enter (see below). |
   | `LOG_FILE` | `false` (the function's filesystem is read-only) |
   | `LOG_FORMAT` | `json` |

3. **Deploy:**
   - Every push to a branch other than the production branch (`main` by default) makes a **preview** deployment with its own URL.
   - A push to `main` deploys **production**.
   - With the Vercel CLI: `vercel deploy` makes a preview, and `vercel deploy --prod` deploys production.
4. **Check it:**
   - `https://<deployment>/api/health` returns `{"status": "ok"}`.
   - Opening the site shows the password screen.
   - After the password, create a game against bots.

Environment variable changes only apply to new deployments, so redeploy after changing one.

## 3. Access: the password gate

With `ACCESS_PASSWORD` set:
- the API answers `401 access_required` to everything except `/api/health` and `/api/access`;
- the browser enters the password on the password screen (`POST /api/access`), which sets an HttpOnly cookie for 30 days;
- password attempts are limited to 10 per 10 minutes per address.

Changing `ACCESS_PASSWORD` (or `STATE_KEY`) logs everyone out. If it's unset, there is no gate, which is how local dev runs.

The static SPA itself loads for anyone, but it can't do anything without the API. The gate covers previews and production alike. Vercel's own options were left out on purpose:
- Password Protection isn't on the free plan.
- Vercel Authentication lets in only Vercel users you invite.

Real accounts can replace the gate later. The code is in `backend/app/access.py`.

## 4. Testing against Postgres

The test suite **drops its tables**, so never point it at `production`. Use a throwaway branch instead:

```sh
neon checkout dev --create        # a branch of production, expires in 7 days
cd backend && TEST_DATABASE_URL='<dev branch pooled URL>' uv run pytest
```

To run the whole app locally on that branch:

```sh
DATABASE_URL='<dev URL>' STATE_KEY="$(openssl rand -base64 32)" ACCESS_PASSWORD=test make dev
```

## 5. Logs

On Vercel, the API logs JSON lines to stdout. Read them in the project's **Logs** tab, filtering by `request_id` or `game_id`.

The free plan keeps them only for a short time, so look soon after a problem. Locally, logs go to `data/logs/app.jsonl` (see `backend/CLAUDE.md`).

## Troubleshooting

- **The API fails at startup with "STATE_KEY must be set":** `STATE_KEY` is missing for that environment. Preview and Production each need their own copy.
- **Everything answers 401:** the browser hasn't entered the password, or the password or `STATE_KEY` changed. Reload the page to get the password screen.
- **Connection errors under load:** check that `DATABASE_URL` is the pooled (`-pooler`) one.
- **A deploy fails on Python dependencies:** `requirements.txt` is stale. Run `make gen-reqs` and commit it; `make lint` catches this.
