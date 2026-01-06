# 🚀 Deployment Guide

## Quick Deployment to Streamlit Community Cloud

This is the easiest and recommended way to share your app with friends!

### Step 1: Prepare Your Repository

1. **Create a GitHub account** (if you don't have one)
   - Go to [github.com](https://github.com) and sign up

2. **Create a new repository**
   - Click "+" in top right → "New repository"
   - Name it `daily-draft-nfl` (or any name you like)
   - Make it **Public**
   - Don't initialize with README (we already have one)
   - Click "Create repository"

### Step 2: Push Your Code

Open a terminal in the `claudecode` folder and run:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit - Daily Draft NFL Trivia"

# Link to your GitHub repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/daily-draft-nfl.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 3: Deploy on Streamlit Cloud

1. **Go to Streamlit Community Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Click "Sign up" or "Sign in with GitHub"
   - Authorize Streamlit to access your GitHub

2. **Create New App**
   - Click "New app" button
   - Fill in the form:
     - **Repository**: Select your `daily-draft-nfl` repository
     - **Branch**: `main`
     - **Main file path**: `streamlit_app.py`
     - **App URL**: Choose a custom URL (optional)

3. **Deploy!**
   - Click "Deploy"
   - Wait 2-3 minutes for initial deployment
   - Your app will be live at `https://your-app-name.streamlit.app`

### Step 4: Share with Friends

Your app is now live! Share the URL with anyone:
- `https://your-app-name.streamlit.app`

Everyone who visits will be able to play the same daily challenge!

---

## Alternative: Deploy to Heroku

### Prerequisites
- Heroku account ([heroku.com](https://heroku.com))
- Heroku CLI installed

### Files Needed

Create `Procfile` in the claudecode folder:
```
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
```

Create `setup.sh`:
```bash
mkdir -p ~/.streamlit/

echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

### Deploy Steps

```bash
# Login to Heroku
heroku login

# Create new app
heroku create your-daily-draft-app

# Push code
git push heroku main

# Open app
heroku open
```

---

## Alternative: Local Network Sharing

Want to share on your local network only?

1. **Find your local IP address**
   - Windows: `ipconfig` (look for IPv4 Address)
   - Mac/Linux: `ifconfig` or `ip addr`

2. **Run Streamlit with network access**
   ```bash
   streamlit run streamlit_app.py --server.address=0.0.0.0
   ```

3. **Share your local URL**
   - Share `http://YOUR_IP:8501` with people on same network
   - Example: `http://192.168.1.100:8501`

**Note**: Only works for devices on the same WiFi/network!

---

## Alternative: Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build and Run

```bash
# Build image
docker build -t daily-draft-nfl .

# Run container
docker run -p 8501:8501 daily-draft-nfl
```

Access at `http://localhost:8501`

---

## Monitoring Your Deployed App

### Streamlit Cloud
- View logs: Click "Manage app" → "Logs"
- Restart app: Click "Reboot app"
- View analytics: Check the dashboard

### Tips for Production
1. **Monitor usage**: Check Streamlit Cloud dashboard for user stats
2. **Update regularly**: Push updates to GitHub, app auto-deploys
3. **Check logs**: If users report issues, check logs for errors
4. **Data limits**: Streamlit Cloud has usage limits (usually generous for small apps)

### Updating Your App

After deployment, to push updates:

```bash
# Make your changes to the code
git add .
git commit -m "Description of changes"
git push origin main
```

Streamlit Cloud will automatically detect changes and redeploy!

---

## Troubleshooting Deployment

### App won't start
- Check logs for error messages
- Verify all files are committed to GitHub
- Ensure `requirements.txt` has all dependencies

### Slow performance
- First load of each year's data will be slow (data download)
- Subsequent loads are cached
- Consider adding a warming script if needed

### Data loading errors
- Ensure internet connection on server
- nfl_data_py requires access to GitHub for data
- Check if GitHub is accessible from your deployment platform

### Daily challenge not resetting
- Verify server is using UTC time
- Check system time on deployment platform
- May need to restart app at midnight UTC

---

## Security Considerations

### Public Deployment
- This app has no user authentication
- Anyone with the URL can access it
- No personal data is collected or stored
- All game state is session-based (not persistent)

### Private Deployment
- Use Streamlit's authentication features (paid plans)
- Deploy behind a VPN or firewall
- Use password protection at web server level

---

## Cost

### Streamlit Community Cloud
- **Free tier**: Perfect for this app!
- Includes: 1 app, unlimited viewers
- Limitations: Resource limits (usually fine for this app)

### Heroku
- **Free tier** (Eco): $0 (sleeps after 30min inactivity)
- **Hobby**: $7/month (always on)

### Other Platforms
- **Render**: Free tier available
- **Railway**: Free tier with limits
- **AWS/GCP/Azure**: Pay-as-you-go (can be more complex)

---

**Recommendation**: Start with Streamlit Community Cloud (free, easy, fast)

Need help? Check the main README.md or open an issue!
