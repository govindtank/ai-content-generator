# AI Studio

AI-powered content generation platform with Google Gemini. Generate images and text using your own Gemini API key.

## Features

- **Google OAuth sign-in** — secure authentication with your Google account
- **Image generation** — powered by Gemini Flash Image (Nano Banana) models
- **Text generation** — powered by Gemini Flash models
- **Bring Your Own Key** — use your own Gemini API key with your free tier quota
- **Usage tracking** — free tier capped at 3 image generations per user
- **Modern UI** — clean, responsive dark-theme interface

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Google account
- Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- Google OAuth credentials from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

### 2. Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Copy `.env.example` to `.env` and fill in:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SECRET_KEY=generate-a-random-secret
```

**Getting Google OAuth credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an OAuth 2.0 Client ID (Web application)
3. Add `http://localhost:8080/auth/callback` as an Authorized redirect URI
4. Copy the Client ID and Client Secret

### 4. Run

```bash
python run.py
```

Open [http://localhost:8080](http://localhost:8080)

### 5. Use

1. Sign in with your Google account
2. Go to **Settings** and enter your Gemini API key
3. Start generating images and text from the Dashboard

## Docker

```bash
docker compose up --build
```

Set environment variables in a `.env` file (refer to `.env.example`).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | — | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8080/auth/callback` | OAuth callback URL |
| `SECRET_KEY` | random | Flask session secret |
| `PORT` | 8080 | HTTP port |
| `HOST` | 0.0.0.0 | Bind address |
| `DATABASE_PATH` | data/app.db | SQLite database path |
| `IMAGE_GENERATIONS_LIMIT` | 3 | Free tier image generation limit |
| `GEMINI_TEXT_MODEL` | gemini-2.0-flash | Model for text generation |
| `GEMINI_IMAGE_MODEL` | gemini-2.5-flash-image | Model for image generation |

## Architecture

```
app/
├── __init__.py       # Flask app factory
├── config.py         # Configuration
├── db.py             # SQLite database
├── auth.py           # Google OAuth
├── gemini.py         # Gemini API client
├── decorators.py     # Auth middleware
├── routes/
│   ├── dashboard.py  # Dashboard, settings, history
│   ├── text.py       # Text generation API
│   └── image.py      # Image generation API
├── templates/        # Jinja2 pages
└── static/           # CSS, JS
```

## License

MIT
