# OPD Portal

A login portal with dynamic UI, backend authentication, and role-based controls.

## Features

- Dynamic login page and responsive dashboard UI.
- Backend API with PostgreSQL persistence.
- Password hashing using PBKDF2 + unique salt per user.
- Role model: `super_admin`, `admin`, `sub`.
- Super admin can create/enable/disable admin accounts.
- Admins manage only their own sub-logins.
- Sub-login table includes username search and status filters.

## Default Login

- Username: `admin`
- Password: `admin123`
- Role: `super_admin`

## Run

From this folder run:

```powershell
npm start
```

Then open:

```text
http://127.0.0.1:3000
```

## Deploy On Render

1. Push this project to a GitHub repository.
2. In Render, click New +, then Blueprint.
3. Connect your GitHub repo.
4. Render will detect [render.yaml](render.yaml), create a web service, and provision PostgreSQL.
5. Click Apply and wait for deploy.
6. Open the generated Render URL.

### Database Note

- The server now requires `DATABASE_URL`.
- In Render Blueprint flow, this is injected automatically from the managed database.
- On first startup, the app creates the users table and seeds the default super admin.

## Data Storage

- Users are stored in PostgreSQL.
- Passwords are never stored in plain text.
- Session tokens are in-memory server-side and reset when server restarts.
