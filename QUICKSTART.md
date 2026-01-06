# 🚀 Quick Start Guide

Get Daily Draft NFL Trivia running in 3 minutes!

## Local Testing (For You)

```bash
# 1. Navigate to the folder
cd claudecode

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run streamlit_app.py
```

That's it! The app opens at `http://localhost:8501`

---

## Share with Friends (Deploy to Internet)

### Option 1: Streamlit Cloud (Recommended - FREE & EASY)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Daily Draft NFL Trivia"
   git remote add origin https://github.com/YOUR_USERNAME/daily-draft-nfl.git
   git push -u origin main
   ```

2. **Deploy**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repo and `streamlit_app.py`
   - Click "Deploy"

3. **Share the URL**
   - Get URL like `your-app.streamlit.app`
   - Share with friends!

---

## Testing the Daily Logic

Want to verify the daily challenge works?

```bash
python test_daily_logic.py
```

This tests:
- ✅ Daily seed consistency
- ✅ Deterministic question generation
- ✅ Date formatting
- ✅ Random vs. daily modes

---

## Key Features Implemented

### ✅ Daily Challenge
- Same questions for everyone each day
- Resets at UTC midnight
- "Play once per day" enforced
- Share your results!

### ✅ Practice Mode
- Unlimited random games
- Different questions every time
- No daily limit

### ✅ Professional UI
- Loading states
- Instructions modal
- Progress indicators
- Error handling
- Mobile-responsive

### ✅ Smart Data
- Only shows eligible players
- Caches data for performance
- Graceful error recovery

---

## File Structure

```
claudecode/
├── streamlit_app.py       # ⭐ Main app (run this)
├── game_logic.py          # Game engine
├── load_nfl_data.py       # Data loader
├── requirements.txt       # Dependencies
├── test_daily_logic.py    # Tests
└── .streamlit/
    └── config.toml        # Theme config
```

---

## Troubleshooting

**First load is slow?**
- Normal! Downloads NFL data first time
- Cached after that

**Want to test a new day?**
- Click "🔄 Refresh" in sidebar
- Or wait until UTC midnight

**Deploy issues?**
- Check DEPLOYMENT.md for detailed guide
- Ensure all files are committed to GitHub

---

## Next Steps

1. **Test locally** - Run and play a game
2. **Customize** - Edit colors in `.streamlit/config.toml`
3. **Deploy** - Follow Option 1 above
4. **Share** - Send URL to friends!

---

**Need more help?** Check README.md or DEPLOYMENT.md

**Ready to play?** Run `streamlit run streamlit_app.py` 🏈
