# 🚀 Railway Deployment Guide for Solixa Django App

## ✅ Prerequisites

Your app is now **Railway-ready** with these files:
- ✅ `Procfile` - Tells Railway how to run your app
- ✅ `runtime.txt` - Specifies Python version
- ✅ `requirements_django.txt` - All dependencies including gunicorn
- ✅ `settings.py` - Updated for production with WhiteNoise & PostgreSQL support
- ✅ `.gitignore` - Prevents committing sensitive files

---

## 📦 Step 1: Install Railway CLI

### Option A: Using npm (Recommended)
```bash
npm install -g @railway/cli
```

### Option B: Using curl (Mac/Linux)
```bash
curl -fsSL https://railway.app/install.sh | sh
```

### Option C: Using Homebrew (Mac)
```bash
brew install railway
```

**Verify installation:**
```bash
railway --version
```

---

## 🔐 Step 2: Login to Railway

```bash
railway login
```

This will open a browser window. Sign up or log in with:
- GitHub (recommended)
- Google
- Email

---

## 📂 Step 3: Initialize Git Repository (if not already done)

```bash
# Initialize git if you haven't
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for Railway deployment"
```

---

## 🚂 Step 4: Create Railway Project

```bash
# Initialize Railway project
railway init
```

**You'll be asked:**
1. "What is the name of your project?" → Type: `solixa-django`
2. "Starting point?" → Select: `Empty project`

This creates a new project on Railway and links it to your local directory.

---

## 🗄️ Step 5: Add PostgreSQL Database

```bash
# Add PostgreSQL service
railway add --database postgres
```

Railway will automatically:
- Create a PostgreSQL database
- Set the `DATABASE_URL` environment variable
- Connect it to your Django app

---

## ⚙️ Step 6: Set Environment Variables

```bash
# Set Django secret key (generate a new one for production)
railway variables set SECRET_KEY="your-super-secret-key-here-$(openssl rand -hex 32)"

# Set DEBUG to False for production
railway variables set DEBUG="False"

# Set allowed hosts (Railway will add their domain automatically)
railway variables set DJANGO_SETTINGS_MODULE="solixa_django.settings"
```

**Optional: Set custom domain later in Railway dashboard**

---

## 🚀 Step 7: Deploy to Railway

```bash
# Deploy your application
railway up
```

This will:
1. ✅ Upload your code to Railway
2. ✅ Install dependencies from `requirements_django.txt`
3. ✅ Start your app with gunicorn
4. ✅ Assign you a public URL

**Wait for deployment to complete** (usually 2-5 minutes)

---

## 🔧 Step 8: Run Database Migrations

```bash
# Run migrations on Railway
railway run python manage.py migrate

# Create superuser (for admin access)
railway run python manage.py createsuperuser
```

**When creating superuser:**
- Username: `admin` (or your choice)
- Email: your email
- Password: strong password

---

## 🎉 Step 9: Access Your Application

```bash
# Open your deployed app in browser
railway open
```

Or get your URL:
```bash
railway status
```

Your app will be at: `https://solixa-django-production.up.railway.app`

---

## 📊 Step 10: Test Your Application

1. **Login page** - Go to your Railway URL
2. **Login** with the superuser credentials you created
3. **Upload** the `Anomaly_Data.csv` file
4. **Test all pages:**
   - 🏠 Home
   - 📊 Data Overview
   - 🔍 Anomalies
   - 📈 Forecasting

---

## 🔄 Making Updates

After making changes to your code:

```bash
# 1. Commit your changes
git add .
git commit -m "Your update message"

# 2. Deploy to Railway
railway up

# 3. If you changed models, run migrations
railway run python manage.py migrate
```

---

## 📝 Useful Railway Commands

```bash
# View logs (see what's happening)
railway logs

# Open Railway dashboard
railway open

# Check deployment status
railway status

# View environment variables
railway variables

# Connect to PostgreSQL database
railway connect postgres

# Run any Django command
railway run python manage.py <command>

# Restart your service
railway restart
```

---

## 🐛 Troubleshooting

### Problem: Static files not loading
```bash
# Collect static files
railway run python manage.py collectstatic --noinput
```

### Problem: Database connection error
```bash
# Check if DATABASE_URL is set
railway variables

# If not set, add PostgreSQL again
railway add --database postgres
```

### Problem: Application won't start
```bash
# Check logs for errors
railway logs

# Common fixes:
# 1. Ensure Procfile exists
# 2. Check requirements_django.txt has all dependencies
# 3. Verify Python version in runtime.txt matches your local version
```

### Problem: Import errors
```bash
# Make sure all dependencies are in requirements_django.txt
railway run pip list

# If missing, add to requirements and redeploy
```

---

## 💰 Pricing

Railway pricing:
- **Free Tier**: $5 in credits per month (enough for testing)
- **Usage-based**: ~$5-10/month for a small app
- **Included**: PostgreSQL database, SSL/HTTPS, automatic deploys

**Your Solixa app will likely cost $5-10/month in production**

---

## 🔒 Security Notes

1. **Never commit sensitive data:**
   - ✅ `.gitignore` is configured
   - ✅ Secret keys are environment variables
   - ✅ Database credentials are auto-managed

2. **In production, set:**
   ```bash
   railway variables set DEBUG="False"
   railway variables set ALLOWED_HOSTS="your-domain.railway.app"
   ```

3. **Backup your database regularly:**
   ```bash
   railway run python manage.py dumpdata > backup.json
   ```

---

## 🌐 Custom Domain (Optional)

1. Go to Railway dashboard: https://railway.app/dashboard
2. Click on your project
3. Go to "Settings" → "Domains"
4. Add your custom domain
5. Update DNS settings as instructed

---

## 📱 Mobile Access

Your Railway app is accessible from anywhere:
- ✅ Desktop browsers
- ✅ Mobile browsers
- ✅ Tablets
- ✅ Any device with internet

Share the URL with your team!

---

## ✅ Deployment Checklist

Before going live:

- [ ] `railway up` completed successfully
- [ ] `railway run python manage.py migrate` completed
- [ ] Created superuser with `railway run python manage.py createsuperuser`
- [ ] Tested login at your Railway URL
- [ ] Uploaded test CSV file (Anomaly_Data.csv)
- [ ] Verified all 4 pages work (Home, Data Overview, Anomalies, Forecasting)
- [ ] Set `DEBUG=False` in Railway variables
- [ ] Static files loading correctly
- [ ] Database persisting data between visits

---

## 🎊 Success!

Your Solixa Django application is now:
- ✅ **Live** on the internet
- ✅ **Secure** with HTTPS
- ✅ **Scalable** with Railway
- ✅ **Persistent** with PostgreSQL
- ✅ **Professional** with proper hosting

**Share your Railway URL with anyone to let them use your solar analytics platform!**

---

## 📞 Support

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Django Docs**: https://docs.djangoproject.com

---

**Created by:** AI Assistant  
**Date:** December 26, 2025  
**Ready to deploy:** YES ✅

