# 🏈 Daily Draft NFL Trivia

A daily NFL trivia game where players guess statistical leaders across different positions and seasons. Play once per day in Daily Challenge mode or practice unlimited rounds!

## 🎮 How to Play

1. **Daily Challenge**: One game per day with 5 questions. Everyone gets the same questions each day (resets at UTC midnight)
2. **Practice Mode**: Unlimited random games for practice

Each question asks: *"Who had the most [stat] in [year] for [position]s?"*

### Scoring
- Points awarded based on how close your guess is to the correct answer
- 🟩🟩🟩🟩🟩 = 10,000 points (100% match)
- Score decreases based on percentage of the leader's stat value
- Maximum: 50,000 points per round (5 questions × 10,000)

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone or download this repository**
   ```bash
   cd DailyDraft/claudecode
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Open your browser**
   - The app will automatically open at `http://localhost:8501`
   - If not, navigate to the URL shown in your terminal

## 📦 Project Structure

```
claudecode/
├── streamlit_app.py          # Main Streamlit web application
├── game_logic.py              # Core game logic and scoring
├── load_nfl_data.py           # NFL data loading utilities
├── requirements.txt           # Python dependencies
├── .streamlit/
│   └── config.toml           # Streamlit configuration
├── README.md                  # This file
└── IMPROVEMENTS.md            # Development notes
```

## 🌐 Deployment

### Deploy to Streamlit Community Cloud (Recommended)

1. **Push to GitHub**
   - Create a new GitHub repository
   - Push the `claudecode` folder contents to the repository

2. **Deploy on Streamlit**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository, branch, and set `streamlit_app.py` as the main file
   - Click "Deploy"

3. **Share with friends**
   - Your app will get a public URL like `yourapp.streamlit.app`
   - Share this URL with anyone!

### Other Deployment Options

- **Heroku**: Use the Streamlit buildpack
- **Docker**: Create a Dockerfile with Python 3.9+ and run with `streamlit run`
- **Local Network**: Run locally and share your local IP address

## 🎯 Features

- ✅ **Daily Challenge**: Same questions for everyone, resets at UTC midnight
- ✅ **Play Once Per Day**: Enforced daily limit for the challenge mode
- ✅ **Practice Mode**: Unlimited random games
- ✅ **Smart Player Selection**: Only shows players who were active in the selected year
- ✅ **Share Results**: Copy-paste your results to share (like Wordle!)
- ✅ **Responsive Design**: Works on desktop and mobile
- ✅ **Data Caching**: Fast performance with intelligent data caching
- ✅ **Error Handling**: Graceful handling of data issues
- ✅ **Loading States**: Visual feedback during data fetches

## 🔧 Configuration

### Streamlit Settings
Edit `.streamlit/config.toml` to customize:
- Theme colors
- Server settings
- Browser behavior

### Game Settings
Edit constants in `game_logic.py`:
- `MIN_YEAR` / `MAX_YEAR`: Year range for questions
- `QUESTIONS_PER_ROUND`: Number of questions per game
- `MAX_POINTS_PER_QUESTION`: Points for perfect answer
- `EMOJI_THRESHOLDS`: Scoring emoji mappings

## 📊 Data Source

This app uses the excellent [nfl_data_py](https://github.com/cooperdff/nfl_data_py) library, which provides:
- Player rosters (1999-2023)
- Seasonal statistics
- Snap counts
- And more!

Data is fetched on-demand and cached for performance.

## 🐛 Troubleshooting

### First load is slow
- The first time you load data for a year, it downloads from the NFL data API
- Subsequent loads are cached and much faster
- This is normal behavior

### "No eligible players" error
- Some older years may have limited data
- The app filters to only show players who were active (played snaps or had stats)
- If this persists, try a different year or refresh

### Daily challenge shows wrong date
- The app uses UTC time for consistency across time zones
- Midnight UTC may be different from your local midnight
- This ensures everyone worldwide gets the same daily challenge

### Connection errors
- Ensure you have internet connection (required for initial data fetch)
- The nfl_data_py library needs to download data from GitHub
- If issues persist, try clearing cache and restarting

## 🤝 Contributing

Found a bug or have a suggestion? Here's how to contribute:

1. **Issues**: Report bugs or request features
2. **Pull Requests**: Submit improvements
3. **Testing**: Help test with different scenarios

## 📝 License

This project is open source and available for personal use.

## 🙏 Acknowledgments

- **nfl_data_py**: For providing comprehensive NFL data
- **Streamlit**: For making web app development simple
- **NFL**: For the awesome sport and statistics

## 📞 Support

Having issues or questions?
- Check the troubleshooting section above
- Review the instructions in the app (click "📖 Show Instructions")
- Open an issue on GitHub

---

**Enjoy the game! 🏈**

Share your daily scores with friends and see who knows their NFL stats best!
