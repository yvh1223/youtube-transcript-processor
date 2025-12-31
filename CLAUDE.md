# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Transcript Processor is a Python application that automates the extraction of YouTube transcripts, generates AI summaries via OpenAI, creates audio versions using Google Cloud TTS, and uploads everything to Google Drive in an organized folder structure.

**Main script**: `main.py` - Entry point that orchestrates modular components in `src/`

## Development Commands

### Environment Setup
```bash
# Quick setup (recommended for first-time setup)
python setup.py

# Manual setup
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Running the Application
```bash
# Use wrapper script (recommended)
./run.sh         # Run main processor with venv activated

# Manual (activate venv first)
source venv/bin/activate  # macOS/Linux
python main.py
```

### Configuration
- Copy `config.yaml.example` to `config.yaml` and edit channel list
- Create `.env` file with:
  - `OPENAI_API_KEY` - OpenAI API key
  - `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google service account JSON (currently: `./archive/gen-lang-client-0074099179-3b8f73266f6f.json`)
- Google Cloud credentials are in `archive/` directory

## Architecture

### Modular Design
The application uses a modular architecture with components in `src/`:

**Core Modules**:
- `src/config.py` - Configuration loading and validation
- `src/youtube_processor.py` - Video scraping and transcript extraction
- `src/summarizer.py` - OpenAI-powered summarization
- `src/tts.py` - Text-to-speech conversion
- `src/drive_uploader.py` - Google Drive upload management
- `src/utils.py` - Helper functions

**Processing Flow**:
1. **Video Discovery**: `YouTubeProcessor` uses `scrapetube` to scrape recent videos
2. **Transcript Extraction**: Uses `youtube-transcript-api` with language preferences
3. **AI Summarization**: `Summarizer` calls OpenAI API to generate summaries
4. **Text-to-Speech**: `TextToSpeech` uses Google Cloud TTS to create MP3 files
5. **Cloud Storage**: `DriveUploader` uploads files to Google Drive
6. **Duplicate Prevention**: Tracks processed videos in CSV files

### Data Flow
```
YouTube Channels → Scrape Recent Videos → Extract Transcripts →
Generate AI Summaries → Create Audio Files → Upload to Drive →
Clean Local Files
```

### Google Drive Organization
```
YTTranscript/
├── Channel1/
│   ├── Transcripts/
│   ├── Summaries/
│   └── Audio/
└── Channel2/
    ├── Transcripts/
    ├── Summaries/
    └── Audio/
```

### Local File Structure
```
project/
├── main.py              # Entry point
├── run.sh               # Wrapper to run with venv
├── src/                 # Source modules
├── config.yaml          # Configuration
├── .env                 # Environment variables (not committed)
├── channels/            # Temporary processing (deleted after upload)
├── logs/app.log         # Application logs
├── archive/             # Archived old code, credentials, and dev files (not committed)
└── venv/                # Virtual environment
```

## Key Implementation Details

### Time Window Filtering
Videos are filtered based on `config.days_back` setting in `src/youtube_processor.py`:
```python
if time_delta > timedelta(days=self.config.days_back):
    return {"stop_processing": True}
```

### FFmpeg Configuration
The script auto-detects FFmpeg for audio processing via `shutil.which()`. If not found, audio processing will fail. Required for pydub/AudioSegment functionality.

### API Rate Limiting
**Intelligent rate limiting prevents YouTube IP bans** by adding configurable delays between requests:
- `delay_between_videos`: Wait time after each transcript fetch (default: 3s, recommended: 3-5s)
- `delay_between_channels`: Wait time between processing channels (default: 5s)
- Automatic detection and handling of IP bans with helpful recovery suggestions
- Failed videos are automatically retried on next run (tracked in `channel_data.csv`)

Uses `YouTubeRequestFailed` exception to handle rate limits and request failures. The processor checks for 429 status codes and IP ban messages, then stops processing when detected.

### Credential Management
Credentials are managed through environment variables in `.env`:
- `GOOGLE_APPLICATION_CREDENTIALS` points to: `./archive/gen-lang-client-0074099179-3b8f73266f6f.json`
- `OPENAI_API_KEY` must be set with valid API key
- Configuration is validated on startup via `src/config.py`

### Configuration Options
See `config.yaml.example` for all available settings:
- `processing.days_back` - How many days back to scan for videos (default: 7)
- `processing.rate_limiting.delay_between_videos` - Seconds between transcript requests (default: 3)
- `processing.rate_limiting.delay_between_channels` - Seconds between channels (default: 5)
- `openai.model` - OpenAI model for summaries (default: "gpt-4o-mini")
- `tts.voice_name` - Google TTS voice selection (default: "en-US-Standard-B" - cheapest option with 4M free chars/month)
- `file_name_max_length` - Maximum filename length (default: 30)

## Critical Dependencies

### External Services Required
1. **OpenAI API** - For transcript summarization
2. **Google Cloud Project** with:
   - Text-to-Speech API enabled
   - Drive API enabled
   - Service account with JSON credentials
   - Drive folder shared with service account email

### System Dependencies
- **FFmpeg** - Required for audio processing (pydub backend)
- **Python 3.9 to 3.13 (Python 3.14 is not supported)** - Uses `zoneinfo` for timezone handling

### Important Library Notes
- **youtube-transcript-api v1.2.3+** - Uses instance-based API (NOT static `get_transcript()`)
  - Correct usage: `api = YouTubeTranscriptApi()` then `api.fetch(video_id)`
  - See `API_FIX_NOTES.md` for migration details from older API versions
  - May encounter rate limiting with frequent requests (IP blocks from YouTube)

## Common Modifications

### Changing Processing Window
Update `config.yaml`:
```yaml
processing:
  days_back: 7  # Change from 3 to desired days
```

### Adjusting OpenAI Settings
Update in `config.yaml`:
```yaml
openai:
  model: "gpt-4o"  # Change model
  max_tokens: 8000  # Adjust token limit
  temperature: 0.7  # Adjust creativity
```

### Changing TTS Voice
Update in `config.yaml`:
```yaml
tts:
  voice_name: "en-US-Neural2-A"  # Different voice (Neural2 = $16/M, Standard = $4/M)
  voice_gender: "MALE"  # MALE, FEMALE, or NEUTRAL
  speaking_rate: 1.2  # Speed adjustment
```

**Note**: Standard voices (`en-US-Standard-*`) provide 4M free characters/month at $4/M after. Neural2 voices cost $16/M with only 1M free/month. For personal use, Standard voices are recommended.

### Adjusting Rate Limiting
Update in `config.yaml`:
```yaml
processing:
  rate_limiting:
    delay_between_videos: 5      # Increase if experiencing IP bans
    delay_between_channels: 10   # More conservative for multiple channels
```

## Logging and Debugging

- All logs written to `logs/app.log`
- Log level controlled via `logging.INFO` in script (no config option)
- Warnings suppressed for urllib3 and pydub at script startup
- Check logs for processing status, errors, and upload confirmations

## Testing

### Verification
To verify the setup is working:

1. **Test configuration loading**:
   ```bash
   python -c "from src.config import Config; c = Config(); print('Config loaded successfully')"
   ```

2. **Run the main script**:
   ```bash
   ./run.sh
   ```
   The script will fail early with helpful error messages if anything is misconfigured.

3. **Check logs**:
   ```bash
   tail -f logs/app.log
   ```

## Recent Changes

**2025-12-30**: Implemented intelligent rate limiting and cleaned up project structure
- Added configurable delays between video requests and channel processing
- Enhanced error detection for IP bans with helpful recovery suggestions
- Verified audio generation working (Google Cloud TTS Standard voice)
- Confirmed optimal TTS pricing: Standard voices = 4M free chars/month
- Consolidated documentation into README.md and CLAUDE.md
- Archived intermediate files, test scripts, and development notes

**2025-12-29**: Refactored from monolithic `new_main.py` to modular architecture
- Original code archived in `archive/2025-12-29/new_main.py`
- New entry point: `main.py`
- Components separated into `src/` modules
- Test scripts organized in `tests/` folder
- Added wrapper scripts: `run.sh` and `run_test.sh` for easy execution
- Added `tests/setup_env.py` for environment configuration
- Added `tests/test_setup.py` for verification
- Fixed `TooManyRequests` import (now uses `YouTubeRequestFailed`)
