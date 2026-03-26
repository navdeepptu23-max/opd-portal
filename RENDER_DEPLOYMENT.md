# Render Deployment Guide

## Step-by-Step Manual Deployment

### Part 1: Create PostgreSQL Database

1. Go to https://dashboard.render.com
2. Click **New +** (top right)
3. Select **PostgreSQL**
4. Fill in:
   - **Name**: `opd-portal-db`
   - **Database**: `opdportal`
   - **User**: `opdportal`
   - **Region**: Choose your region
   - **Plan**: Free
5. Click **Create Database**
6. Wait for it to finish (5-10 minutes)
7. Copy the **Internal Database URL** (starts with `postgres://`)

### Part 2: Create Web Service

1. Click **New +** (top right again)
2. Select **Web Service**
3. Click **Deploy from GitHub**
4. Search and select: `navdeepptu23-max/opd-portal`
5. Fill in:
   - **Name**: `opd-portal`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Build Command**: (leave empty)
   - **Start Command**: (leave empty)
   - **Runtime**: Node
6. Click **Create Web Service**
7. Wait for initial build (this should work now - just install npm packages)

### Part 3: Add Database Connection

1. In your web service dashboard:
2. Go to **Environment**
3. Click **Add Environment Variable**
4. Fill in:
   - **Key**: `DATABASE_URL`
   - **Value**: (paste the Internal URL you copied from the database)
5. Click **Save Changes**
6. The service will auto-redeploy

### Part 4: Wait for Deploy

- Watch the **Deploy Log** (bottom right)
- Should see: "Your service is live at https://opd-portal-xxx.onrender.com"

### Part 5: Test Your Portal

- Open the URL from the deploy complete message
- Login with:
  - Username: `admin`
  - Password: `admin123`

---

If it still fails, share the full error from the **Deploy Log** and I'll fix it.
