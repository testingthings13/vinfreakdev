# VINFREAK

## Configuration

The backend uses a SQLite database stored at `backend/cars.db` by default.
You can override this by setting the `DATABASE_URL` environment variable
to point to a different database.

## Import Jobs

Admins can queue import jobs from `/admin/imports`. Each job links to a detail
page at `/admin/imports/{id}` showing progress and any log output. Jobs that
are still queued or running expose a **Cancel** action which marks the job as
`cancelled`.
