# ABOUTME: Configuration loader and environment setup for the application
import os
import yaml
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager for YouTube Transcript Processor"""

    def __init__(self, config_file="config.yaml"):
        self.config_file = config_file
        self._load_config()
        self._setup_logging()
        self._setup_credentials()

    def _load_config(self):
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file {self.config_file} is missing.")

        with open(self.config_file, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        # Extract common settings
        self.channels = self.data.get("channels", [])
        self.preferred_languages = self.data.get("preferred_languages", None)
        self.html_formatting = self.data.get("html_formatting", True)
        self.file_name_max_length = self.data.get("file_name_max_length", 30)
        self.file_name_timestamp = self.data.get("file_name_timestamp", True)

        # Processing settings
        processing = self.data.get("processing", {})
        self.days_back = processing.get("days_back", 3)
        self.skip_keywords = processing.get("skip_keywords", ["short", "shorts"])
        self.max_retries = processing.get("max_retries", 3)

        # Rate limiting settings
        rate_limiting = processing.get("rate_limiting", {})
        self.delay_between_videos = rate_limiting.get("delay_between_videos", 3)
        self.delay_between_channels = rate_limiting.get("delay_between_channels", 5)

        # OpenAI settings
        openai_config = self.data.get("openai", {})
        self.openai_model = openai_config.get("model", "gpt-4.1-nano")
        self.max_tokens = openai_config.get("max_tokens", 4000)
        self.temperature = openai_config.get("temperature", 0.5)

        # TTS settings
        tts_config = self.data.get("tts", {})
        self.tts_language_code = tts_config.get("language_code", "en-US")
        self.tts_voice_name = tts_config.get("voice_name", "en-US-Standard-B")
        self.tts_voice_gender = tts_config.get("voice_gender", "NEUTRAL")
        self.tts_speaking_rate = tts_config.get("speaking_rate", 1.0)

        tts_audio_config = tts_config.get("audio", {})
        self.tts_sample_rate = tts_audio_config.get("sample_rate", 24000)
        self.tts_volume_gain = tts_audio_config.get("volume_gain", 0.0)

        # Drive settings
        drive_config = self.data.get("drive", {})
        self.drive_base_folder = drive_config.get("base_folder", "YTTranscript")

        drive_subfolders = drive_config.get("subfolders", {})
        self.drive_transcripts_folder = drive_subfolders.get("transcripts", "Transcripts")
        self.drive_summaries_folder = drive_subfolders.get("summaries", "Summaries")
        self.drive_audio_folder = drive_subfolders.get("audio", "Audio")

    def _setup_logging(self):
        """Set up logging configuration"""
        log_file = "logs/app.log"
        os.makedirs("logs", exist_ok=True)

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def _setup_credentials(self):
        """Set up Google Cloud credentials from environment"""
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not credentials_path:
            raise Exception(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. "
                "Please set it in your .env file."
            )

        # Expand user path if needed
        credentials_path = os.path.expanduser(credentials_path)

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Google credentials file not found at: {credentials_path}"
            )

        # Set the environment variable with the expanded path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        # Validate OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise Exception(
                "OPENAI_API_KEY is not set. Please set it in your .env file."
            )
