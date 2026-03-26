# Push to GitHub

Your local Git repository is ready. Follow these steps to push to GitHub:

## 1. Create a new repository on GitHub

- Go to https://github.com/new
- Set **Repository name** to `opd-portal`
- Choose **Public** or **Private**
- Do NOT initialize with README, .gitignore, or license (we have these already)
- Click **Create repository**

## 2. Add remote and push

Copy and run these commands in PowerShell:

```powershell
cd c:\opdipdreports
git remote add origin https://github.com/YOUR_USERNAME/opd-portal.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## 3. Verify

Open https://github.com/YOUR_USERNAME/opd-portal to confirm files are there.

## 4. Deploy on Render

Once the repo is public on GitHub:
1. Go to https://dashboard.render.com
2. Click **New +** → **Blueprint**
3. Paste your repo URL: `https://github.com/YOUR_USERNAME/opd-portal`
4. Click **Apply**
5. Wait for deploy to complete

The Render service will automatically:
- Install dependencies from [package.json](package.json)
- Create a PostgreSQL database
- Inject DATABASE_URL
- Start the server

Done! Your portal will be live at the Render URL.
