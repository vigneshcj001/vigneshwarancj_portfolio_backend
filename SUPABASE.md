# Using Supabase (free plan) as the database

The backend works with any PostgreSQL database through `DATABASE_URL`. This guide covers Supabase's free plan, including the settings that matter when the API runs on Render.

Without a database the assistant, résumé, job match, and public pages still work. A database adds durable chat sessions, the shared answer cache, contact and newsletter storage, testimonials, share links, and the admin funnel.

## 1. Create the project

1. Sign in at [supabase.com](https://supabase.com) and create a **new project** on the Free plan.
2. Pick the **region closest to your Render service**. Database round trips happen on every chat turn, so distance adds latency.
3. Choose a strong database password and keep it in your password manager. You need it in step 2.

## 2. Copy the right connection string

In the project, open **Connect** and copy the **Session pooler** URI. It looks like:

```text
postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Replace `[YOUR-PASSWORD]` with the database password. If the password contains `@`, `:`, `/`, `?`, `#`, or `%`, URL-encode those characters (for example `@` becomes `%40`).

**Use the Session pooler, not the Direct connection.** On the free plan the direct host (`db.<project-ref>.supabase.co`) is IPv6-only, and Render does not support outbound IPv6. The pooler accepts IPv4.

The **Transaction pooler** (port `6543`) also works: the backend detects it and turns off asyncpg's prepared-statement cache, which transaction pooling cannot keep. The session pooler is the simpler choice for this app.

## 3. Set it on Render

1. Render dashboard → your backend service → **Environment**.
2. Add `DATABASE_URL` with the connection string from step 2.
3. Save. Render redeploys the service.

Never commit the connection string, and never put it in the frontend. It contains the database password.

For local development, put the same line in the `.env` file in the parent workspace folder (the backend loads it automatically).

## 4. Check it worked

- Open `https://<your-backend>.onrender.com/api/health`: `"database"` should be `"connected"` and `"status"` should be `"ok"`.
- The website's `/status` page shows the same under **Database**.
- In Supabase, **Table Editor** lists eight `portfolio_*` tables, each marked **RLS enabled**.

If health shows `"database": "unreachable"`, the API is running without storage. Check the URL, the password encoding, and that you used the pooler host. The backend retries the connection at most once a minute (triggered by `/api/health`), so a fix in Supabase is picked up without a redeploy. Changing `DATABASE_URL` on Render redeploys automatically.

## What the backend does for Supabase

| Concern | Handling (`app/services/storage.py`) |
|---|---|
| IPv4 only on Render | Use the pooler host (step 2) |
| Transaction pooler and prepared statements | Port `6543` or `?pgbouncer=true` sets `statement_cache_size=0`; the `pgbouncer` flag is removed before connecting |
| Encryption in transit | Non-local hosts connect with TLS (`ssl=require`) unless the URL sets `sslmode` |
| Supabase's public REST and GraphQL APIs | Row Level Security is enabled on every table with no policies, so the `anon` and `authenticated` API roles can read and write nothing. The backend connects as the table owner, which RLS does not restrict |
| Paused or unreachable database | Startup continues without storage, health reports `unreachable`, and the connection is retried at most once a minute |
| Connection limits | The pool holds at most 3 connections |
| Secrets in logs | Connection errors log only the error type, never the URL |
| Database size | Chat sessions (30 days), cached answers (7 days), share links (30 days), and client errors (30 days) are purged at startup |

Tables are created automatically on first connection; there are no migrations to run.

## Free plan notes

- **Pausing:** free projects pause after a period of inactivity (about a week at the time of writing). Visitors loading the site call `/api/health`, which queries the database and counts as activity. If the project does pause, restore it from the Supabase dashboard; the backend reconnects on its own.
- **Limits:** storage, connections, and egress are capped on the free plan. This app's data is small (text rows, purged on schedule), but check [Supabase pricing](https://supabase.com/pricing) for current limits.
- **Backups:** the free plan's backup and recovery options are limited. Export anything you want to keep, such as contact messages and approved testimonials, with `pg_dump` or the Table Editor's CSV export.

## Data stored

| Table | Contents | Kept for |
|---|---|---|
| `portfolio_agent_sessions` | Chat history per browser session | 30 days idle, or until Clear chat |
| `portfolio_answer_cache` | Answers to opening questions (no session IDs) | 7 days |
| `portfolio_match_shares` | Shared job-match results (never the job description) | 30 days |
| `portfolio_contacts` | Contact form submissions | Until you delete them |
| `portfolio_subscribers` | Newsletter emails | Until unsubscribe |
| `portfolio_testimonials` | Recommendations and their review status | Until you delete them |
| `portfolio_events` | Analytics events (no personal fields) and client errors | Client errors 30 days |
| `portfolio_content_revisions` | Admin content revisions | Until you delete them |
