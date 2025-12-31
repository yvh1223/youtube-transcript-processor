#!/usr/bin/env python3
# ABOUTME: Main entry point for YouTube Transcript Processor - orchestrates video processing pipeline
import os
import logging
import warnings
import time
from pathlib import Path
import shutil

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")

# Check if ffmpeg is available (needed for audio processing)
ffmpeg_path = shutil.which("ffmpeg")
ffprobe_path = shutil.which("ffprobe")

if ffmpeg_path and ffprobe_path:
    print(f"✅ FFmpeg found at: {ffmpeg_path}")
else:
    print("⚠️  Warning: ffmpeg not found in PATH. Audio processing will be skipped.")
    print("   Install ffmpeg with: brew install ffmpeg")

from src.config import Config
from src.youtube_processor import YouTubeProcessor
from src.summarizer import Summarizer
from src.tts import TextToSpeech
from src.drive_uploader import DriveUploader
from src.utils import sanitize_name, save_text_file


def process_channel_complete(
    channel_username, output_folder, youtube_processor, summarizer, tts, config
):
    """
    Process a single channel completely: extract transcripts, generate summaries,
    create audio files.
    """
    # Step 1: Get transcripts
    channel_folder = youtube_processor.process_channel(channel_username, output_folder)

    if not channel_folder:
        return None

    # Step 2: Process each video for summaries and audio
    channel_name = sanitize_name(channel_username)
    transcripts_folder = channel_folder / config.drive_transcripts_folder
    summaries_folder = channel_folder / config.drive_summaries_folder
    audio_folder = channel_folder / config.drive_audio_folder

    # Read channel data CSV to get list of successfully processed videos
    csv_path = channel_folder / "channel_data.csv"
    if not csv_path.exists():
        logging.info(f"No channel data CSV found for {channel_username}")
        return channel_folder

    import pandas as pd

    df = pd.read_csv(csv_path)
    successful_videos = df[df["Status"] == "SUCCESS"]

    for _, row in successful_videos.iterrows():
        video_id = row["Video ID"]
        video_url = row["Video URL"]

        # Find corresponding transcript file
        transcript_files = list(transcripts_folder.glob(f"*{video_id[:8]}*.txt"))
        if not transcript_files:
            # Try to match by any file in the transcripts folder
            transcript_files = list(transcripts_folder.glob("*.txt"))

        for transcript_file in transcript_files:
            # Read transcript
            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript_text = f.read()

            # Extract video title and date from filename
            file_stem = transcript_file.stem
            parts = file_stem.rsplit("_", 1)
            if len(parts) == 2:
                video_title = parts[0]
                date_suffix = parts[1]
            else:
                video_title = file_stem
                date_suffix = ""

            # Check if summary already exists
            summary_filename = f"{file_stem}_summary.txt"
            summary_file = summaries_folder / summary_filename
            audio_filename = f"{file_stem}.mp3"
            audio_file = audio_folder / audio_filename

            # Generate summary if it doesn't exist
            if not summary_file.exists():
                try:
                    channel_details = f"Channel: {channel_username}"
                    video_details = f"Title: {video_title}, URL: {video_url}"
                    summary_text = summarizer.generate_summary(
                        transcript_text, channel_details, video_details
                    )

                    # Save summary
                    with open(summary_file, "w", encoding="utf-8") as f:
                        f.write(summary_text)
                    logging.info(f"Summary generated: {summary_file}")
                except Exception as e:
                    logging.error(f"Error generating summary for {video_title}: {e}")
                    continue

            # Generate audio if it doesn't exist
            if not audio_file.exists() and summary_file.exists():
                try:
                    # Read summary for audio generation
                    with open(summary_file, "r", encoding="utf-8") as f:
                        summary_text = f.read()

                    tts.synthesize_text_to_audio(summary_text, str(audio_file))
                    logging.info(f"Audio generated: {audio_file}")
                except Exception as e:
                    logging.error(f"Error generating audio for {video_title}: {e}")
                    continue

    return channel_folder


def upload_channel_files(channel_folder, channel_username, drive_uploader, config):
    """Upload all files from a channel folder to Google Drive"""
    if not channel_folder or not channel_folder.exists():
        logging.info(f"Channel folder does not exist for {channel_username}")
        return

    channel_name = sanitize_name(channel_username)

    # Create base folder structure in Drive
    base_folder_id = drive_uploader.get_or_create_folder(config.drive_base_folder)
    channel_folder_id = drive_uploader.get_or_create_folder(
        channel_name, parent_folder_id=base_folder_id
    )

    # Create subfolders
    transcripts_folder_id = drive_uploader.get_or_create_folder(
        config.drive_transcripts_folder, parent_folder_id=channel_folder_id
    )
    summaries_folder_id = drive_uploader.get_or_create_folder(
        config.drive_summaries_folder, parent_folder_id=channel_folder_id
    )
    audio_folder_id = drive_uploader.get_or_create_folder(
        config.drive_audio_folder, parent_folder_id=channel_folder_id
    )

    # Upload files
    upload_configs = [
        (config.drive_transcripts_folder, transcripts_folder_id, "text/plain"),
        (config.drive_summaries_folder, summaries_folder_id, "text/plain"),
        (config.drive_audio_folder, audio_folder_id, "audio/mpeg"),
    ]

    for subfolder_name, drive_folder_id, mimetype in upload_configs:
        local_subfolder = channel_folder / subfolder_name
        if not local_subfolder.exists():
            logging.info(
                f"Local subfolder '{subfolder_name}' does not exist for channel {channel_username}."
            )
            continue

        for file in local_subfolder.iterdir():
            if file.is_file():
                file_id = drive_uploader.upload_file(
                    str(file), folder_id=drive_folder_id, mimetype=mimetype
                )
                # Delete local file after successful upload
                if file_id:
                    try:
                        os.remove(file)
                        logging.info(f"Deleted local file: {file}")
                    except Exception as e:
                        logging.error(f"Error deleting local file {file}: {e}")


def main():
    """Main application entry point"""
    # Initialize configuration
    config = Config()

    if not config.channels:
        logging.error("No channels found in the configuration file.")
        exit(1)

    # Initialize components
    youtube_processor = YouTubeProcessor(config)
    summarizer = Summarizer(config)
    tts = TextToSpeech(config)
    drive_uploader = DriveUploader(config)

    # Local output folder
    output_folder = Path("channels")
    output_folder.mkdir(exist_ok=True)

    # Process each channel
    for idx, username in enumerate(config.channels):
        print(f"\n{'='*60}")
        print(f"Processing channel: {username}")
        print(f"{'='*60}\n")

        # Complete processing: transcripts, summaries, audio
        channel_folder = process_channel_complete(
            username, output_folder, youtube_processor, summarizer, tts, config
        )

        # Upload to Google Drive and clean up local files
        if channel_folder:
            print(f"\nUploading files to Google Drive for channel: {username}")
            upload_channel_files(channel_folder, username, drive_uploader, config)

        # Add delay between channels (except after the last one)
        if idx < len(config.channels) - 1 and config.delay_between_channels > 0:
            print(f"\n⏱️  Waiting {config.delay_between_channels}s before processing next channel...\n")
            time.sleep(config.delay_between_channels)

    print(f"\n{'='*60}")
    print("All channels processed successfully!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
