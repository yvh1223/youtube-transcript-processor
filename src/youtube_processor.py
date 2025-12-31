# ABOUTME: YouTube video scraping and transcript extraction functionality
import logging
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi, YouTubeRequestFailed
from youtube_transcript_api.formatters import TextFormatter
import scrapetube

from .utils import sanitize_name, save_text_file, append_to_csv, parse_relative_time


class YouTubeProcessor:
    """Handles YouTube channel scraping and transcript extraction"""

    def __init__(self, config):
        self.config = config
        self.formatter = TextFormatter()
        self.videos_processed_count = 0  # Track videos for rate limiting

    def process_channel(self, channel_username, output_folder):
        """
        Process a single YouTube channel: scrape videos and extract transcripts.
        Returns the channel folder path for further processing.
        """
        try:
            print(f"🔍 Fetching videos from channel: {channel_username}")
            logging.info(f"Fetching videos from channel: {channel_username}")

            videos = scrapetube.get_channel(channel_username=channel_username)

            channel_name = sanitize_name(channel_username)
            channel_folder = output_folder / channel_name

            # Create subfolders
            transcripts_folder = channel_folder / self.config.drive_transcripts_folder
            summaries_folder = channel_folder / self.config.drive_summaries_folder
            audio_folder = channel_folder / self.config.drive_audio_folder

            transcripts_folder.mkdir(parents=True, exist_ok=True)
            summaries_folder.mkdir(parents=True, exist_ok=True)
            audio_folder.mkdir(parents=True, exist_ok=True)

            csv_path = channel_folder / "channel_data.csv"

            processed_videos = []
            video_count = 0

            for video in videos:
                video_count += 1
                video_data = self._process_video(
                    video,
                    transcripts_folder,
                    csv_path,
                    channel_username
                )

                if video_data:
                    processed_videos.append(video_data)

                    # Add delay after processing each video to avoid rate limiting
                    if video_data.get("Status") == "SUCCESS":
                        self.videos_processed_count += 1
                        if self.config.delay_between_videos > 0:
                            print(f"      ⏱️  Waiting {self.config.delay_between_videos}s before next request...")
                            time.sleep(self.config.delay_between_videos)

                # Check if we should stop processing older videos
                if video_data and video_data.get("stop_processing"):
                    print(f"⏹️  Stopped processing - reached videos older than {self.config.days_back} days")
                    break

            print(f"📊 Total videos scanned: {video_count}")
            print(f"✅ Videos processed: {len([v for v in processed_videos if v.get('Status') == 'SUCCESS'])}")
            logging.info(f"Channel {channel_username}: Scanned {video_count} videos, processed {len(processed_videos)}")

            if video_count == 0:
                print(f"⚠️  No videos found for channel '{channel_username}'")
                print(f"   This could mean:")
                print(f"   - The channel username is incorrect")
                print(f"   - The channel has no public videos")
                print(f"   - Try using the channel ID instead (starts with 'UC')")
                logging.warning(f"No videos found for channel {channel_username}")

            return channel_folder

        except Exception as e:
            print(f"❌ Error processing channel '{channel_username}': {e}")
            logging.error(f"Error processing channel {channel_username}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _process_video(self, video, transcripts_folder, csv_path, channel_username):
        """Process a single video and extract transcript"""
        video_id = video["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_title = (
            video.get("title", {}).get("runs", [{}])[0].get("text", "No Title Available")
        )

        # Debug: Print video details
        print(f"   📹 Found: {video_title[:50]}... (ID: {video_id})")

        # Skip shorts
        if any(keyword in video_title.lower() for keyword in self.config.skip_keywords):
            print(f"      ⏭️  Skipped: Contains keyword from skip list")
            logging.info(f"Skipping shorts video: {video_id} (title: {video_title})")
            return None

        upload_date_text = video.get("publishedTimeText", {}).get("simpleText")
        if not upload_date_text:
            print(f"      ⚠️  Skipped: No upload date found")
            logging.info(f"Video {video_id} missing upload date. Skipping.")
            return None

        print(f"      📅 Upload date text: '{upload_date_text}'")

        time_delta = parse_relative_time(upload_date_text)
        if time_delta is None:
            print(f"      ⚠️  Could not parse date - stopping scan")
            return {"stop_processing": True}

        days_ago = time_delta.total_seconds() / 86400
        print(f"      ⏱️  Uploaded {days_ago:.1f} days ago (limit: {self.config.days_back} days)")

        # Stop if video is older than configured days
        if time_delta > timedelta(days=self.config.days_back):
            print(f"      ⏹️  Too old - stopping scan")
            return {"stop_processing": True}

        # Compute absolute publish date
        absolute_date = datetime.now() - time_delta
        date_suffix = absolute_date.strftime("%Y%m%d")

        # Check if already processed
        if self._is_already_processed(csv_path, video_id):
            print(f"      ⏭️  Already processed - skipping")
            return None

        print(f"      ✅ Within time window - processing...")

        video_data = {
            "Video URL": video_url,
            "Video ID": video_id,
            "Upload Date": upload_date_text,
            "Scrape Date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "PENDING",
            "video_title": video_title,
            "date_suffix": date_suffix,
            "channel_username": channel_username,
        }

        try:
            print(f"      📝 Fetching transcript...")
            # Fetch transcript using new API (youtube-transcript-api v1.2.3+)
            api = YouTubeTranscriptApi()

            if self.config.preferred_languages:
                # Get list of available transcripts and find preferred language
                transcript_list = api.list(video_id)
                transcript = transcript_list.find_transcript(self.config.preferred_languages)
                fetched = transcript.fetch()
            else:
                # Direct fetch (gets default language)
                fetched = api.fetch(video_id)

            # Format transcript to text (TextFormatter expects FetchedTranscript object)
            txt_formatted = self.formatter.format_transcript(fetched)
            video_data["Status"] = "SUCCESS"
            video_data["transcript"] = txt_formatted

            # Save transcript file
            transcript_file = save_text_file(
                transcripts_folder,
                video_title,
                date_suffix,
                txt_formatted,
                self.config.file_name_max_length
            )
            print(f"      💾 Transcript saved: {transcript_file.name}")
            logging.info(f"Transcript saved for video: {video_id}")

        except YouTubeRequestFailed as e:
            # Handle rate limiting and other request failures
            error_msg = str(e)
            if "429" in error_msg or "too many requests" in error_msg.lower():
                print(f"      ⚠️  Rate limit reached")
                logging.warning(f"Too many requests for video {video_id}. Rate limit reached.")
                video_data["Status"] = "FAILED"
                video_data["stop_processing"] = True
            elif "blocking requests from your IP" in error_msg or "IP" in error_msg:
                print(f"      ❌ Error: YouTube is blocking requests from your IP")
                print(f"      💡 Tip: Wait 24-48 hours, or increase delay_between_videos in config.yaml")
                logging.warning(f"IP blocked for video {video_id}: {error_msg}")
                video_data["Status"] = "FAILED"
                video_data["stop_processing"] = True
            else:
                print(f"      ❌ YouTube request failed: {error_msg}")
                logging.warning(f"YouTube request failed for video {video_id}: {error_msg}")
                video_data["Status"] = "FAILED"
        except Exception as e:
            error_msg = str(e)
            if "Subtitles are disabled for this video" in error_msg:
                print(f"      ⚠️  No subtitles available")
                logging.warning(f"Subtitles are disabled for video {video_id}")
                video_data["Status"] = "FAILED - Subtitles disabled"
            else:
                print(f"      ❌ Error: {error_msg}")
                logging.warning(f"Error processing video {video_id}: {error_msg}")
                video_data["Status"] = "FAILED"

        # Save to CSV
        csv_data = {
            k: v for k, v in video_data.items()
            if k in ["Video URL", "Video ID", "Upload Date", "Scrape Date", "Status"]
        }
        append_to_csv(csv_path, [csv_data])

        return video_data

    def _is_already_processed(self, csv_path, video_id):
        """Check if video has already been successfully processed"""
        if not csv_path.exists():
            return False

        existing_data = pd.read_csv(csv_path)
        if video_id in existing_data["Video ID"].values:
            existing_row = existing_data[existing_data["Video ID"] == video_id].iloc[0]
            # Only skip if successfully processed - retry failed ones
            if existing_row["Status"] == "SUCCESS":
                return True

        return False
