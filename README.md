# VINFREAK

## Configuration

The backend reads its database connection string from the
`DATABASE_URL` environment variable.  For local development it falls back
to a SQLite file at `backend/cars.db` (which is ignored by git).  To keep
data such as dealerships between deployments, point `DATABASE_URL` to a
location on a persistent volume, e.g.:

```
DATABASE_URL=sqlite:////data/cars.db
```

or use an external database service like PostgreSQL.

Admin-related data such as site settings and audit logs live in a separate
database controlled by `ADMIN_DATABASE_URL` (defaulting to
`backend/admin.db`).  In production, point both `DATABASE_URL` and
`ADMIN_DATABASE_URL` at persistent storage locations.

## Import Jobs

Admins can queue import jobs from `/admin/imports`. Each job links to a detail
page at `/admin/imports/{id}` showing progress and any log output. Jobs that
are still queued or running expose a **Cancel** action which marks the job as
`cancelled`.
