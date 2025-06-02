import os
import re
import time
import logging
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # For Python 3.9+; for older versions consider pytz
import dateutil.parser
import re
import warnings

# Suppress warnings at the top
warnings.filterwarnings('ignore', category=UserWarning, module='urllib3')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='pydub')

# Transcript and scraping libraries
from youtube_transcript_api import YouTubeTranscriptApi, TooManyRequests
from youtube_transcript_api.formatters import TextFormatter
import scrapetube
from dotenv import load_dotenv

# OpenAI for summarization
from openai import OpenAI

load_dotenv()

client = OpenAI()
# client.api_key = os.getenv("OPENAI_API_KEY")
# client.api_key='sk-proj---'

if not client.api_key:
    raise Exception("OPENAI_API_KEY is not set. Please set it to your valid OpenAI API key.")
# print(client.api_key)

# Google Cloud libraries for TTS and Drive API
from google.cloud import texttospeech
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configure pydub for macOS
from pydub import AudioSegment
import shutil

# Check if ffmpeg is available in PATH
ffmpeg_path = shutil.which("ffmpeg")
ffprobe_path = shutil.which("ffprobe")

if ffmpeg_path and ffprobe_path:
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffprobe = ffprobe_path
    print(f"Using ffmpeg at: {ffmpeg_path}")
else:
    print("Warning: ffmpeg not found in PATH. Audio processing may not work.")
    print("Install ffmpeg with: brew install ffmpeg")
    # Optionally, you can set explicit paths if you know where ffmpeg is installed
    # AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"  # For Apple Silicon Macs
    # AudioSegment.ffprobe = "/opt/homebrew/bin/ffprobe"   # For Apple Silicon Macs

# ------------------ Configuration ------------------
CONFIG_FILE = "config.yaml"
LOG_FILE = "logs/app.log"

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

if not os.path.exists(CONFIG_FILE):
    logging.error(f"Configuration file {CONFIG_FILE} is missing.")
    exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

PREFERRED_LANGUAGES = config.get("preferred_languages", None)
HTML_FORMATTING = config.get("html_formatting", True)
FILE_NAME_MAX_LENGTH = config.get("file_name_max_length", 30)
FILE_NAME_TIMESTAMP = config.get("file_name_timestamp", True)

# Set the Google Cloud credentials environment variable (adjust path if needed)
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\yhuchchannavar\python\for_fun\google.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.expanduser("~/Python/personal/YT/google.json")
# ------------------ Helper Functions ------------------
def sanitize_name(name):
    """Sanitize folder or file names by removing special characters and spaces."""
    return re.sub(r"[^\w\s\u4e00-\u9fff]", "", name.strip().replace(" ", "_"))

def append_to_csv(file_path, data):
    """Append data to a CSV file, creating it if it doesn't exist."""
    columns = ["Video URL", "Video ID", "Upload Date", "Scrape Date", "Status"]
    df = pd.DataFrame(data, columns=columns)
    if not os.path.exists(file_path):
        df.to_csv(file_path, index=False)
    else:
        existing = pd.read_csv(file_path)
        combined = pd.concat([existing, df]).drop_duplicates(subset=["Video ID", "Upload Date"])
        combined.to_csv(file_path, index=False)

def save_text_file(folder, base_name, suffix, text):
    """
    Save text content to a file in the specified folder.
    The file will be named as: {sanitized_base_name}_{suffix}.txt,
    where 'suffix' is the computed published date (e.g., YYYYMMDD).
    """
    file_name = sanitize_name(base_name)[:FILE_NAME_MAX_LENGTH]
    if suffix:
        file_name += f"_{suffix}"
    file_path = folder / f"{file_name}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    return file_path



def parse_relative_time(text):
    """
    Parse a relative time string (e.g., "3 days ago", "1 week ago", "4 hours ago")
    and return a timedelta object. Returns None if the string cannot be parsed.
    """
    text = text.lower().replace("streamed", "").strip()
    match = re.match(r"(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)", text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if "minute" in unit:
            return timedelta(minutes=value)
        elif "hour" in unit:
            return timedelta(hours=value)
        elif "day" in unit:
            return timedelta(days=value)
        elif "week" in unit:
            return timedelta(weeks=value)
    return None

def get_drive_service(scopes):
    """Helper to create a Google Drive service instance."""
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise Exception("GOOGLE_APPLICATION_CREDENTIALS is not set.")
    credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return build('drive', 'v3', credentials=credentials)

def process_channel(channel_username, output_folder):
    """
    Process a single YouTube channel: scrape videos, get transcripts,
    generate summaries via OpenAI, and convert summaries to audio.
    Files are saved locally in structured subfolders, with filenames suffixed 
    by the absolute publish date (YYYYMMDD). Only videos from the last 7 days
    are processed.
    """
    from datetime import datetime, timedelta
    formatter = TextFormatter()
    try:
        videos = scrapetube.get_channel(channel_username=channel_username)
        if not videos:
            logging.warning(f"No videos found for channel {channel_username}. Skipping.")
            return

        channel_name = sanitize_name(channel_username)
        channel_folder = output_folder / channel_name
        # Create subfolders for Transcripts, Summaries, and Audio
        transcripts_folder = channel_folder / "Transcripts"
        summaries_folder = channel_folder / "Summaries"
        audio_folder = channel_folder / "Audio"
        transcripts_folder.mkdir(parents=True, exist_ok=True)
        summaries_folder.mkdir(parents=True, exist_ok=True)
        audio_folder.mkdir(parents=True, exist_ok=True)

        csv_path = channel_folder / "channel_data.csv"

        for video in videos:
            video_id = video["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            video_title = video.get("title", {}).get("runs", [{}])[0].get("text", "No Title Available")
            
            # Skip shorts (if the title contains "short" or "shorts")
            if "short" in video_title.lower() or "shorts" in video_title.lower():
                logging.info(f"Skipping shorts video: {video_id} (title: {video_title})")
                continue

            upload_date_text = video.get("publishedTimeText", {}).get("simpleText")
            if not upload_date_text:
                logging.info(f"Video {video_id} missing upload date. Skipping.")
                continue

            time_delta = parse_relative_time(upload_date_text)
            if time_delta is None:
                # logging.info(f"Video {video_id} has unrecognized date format '{upload_date_text}'. Skipping.")
                break
            
            # If a video is older than 7 days, assume all following videos are older and stop processing.
            if time_delta > timedelta(days=3):
                # logging.info(f"Encountered video {video_id} older than 7 days (uploaded {upload_date_text}). Stopping further processing.")
                break

            # Compute the absolute publish date as a suffix (YYYYMMDD)
            absolute_date = datetime.now() - time_delta
            date_suffix = absolute_date.strftime("%Y%m%d")

            # Check for previously processed videos via CSV log
            if os.path.exists(csv_path):
                existing_data = pd.read_csv(csv_path)
                if video_id in existing_data["Video ID"].values:
                    existing_row = existing_data[existing_data["Video ID"] == video_id].iloc[0]
                    if existing_row["Status"] in ["FAILED", "SUCCESS"]:
                        # logging.info(f"Skipping previously processed video: {video_id}")
                        continue

            video_data = {
                "Video URL": video_url,
                "Video ID": video_id,
                "Upload Date": upload_date_text,
                "Scrape Date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Status": "PENDING",
            }

            try:
                # Fetch transcript
                if PREFERRED_LANGUAGES:
                    transcript_text = YouTubeTranscriptApi.get_transcript(
                        video_id,
                        languages=PREFERRED_LANGUAGES,
                        preserve_formatting=HTML_FORMATTING,
                    )
                else:
                    transcript_text = YouTubeTranscriptApi.get_transcript(
                        video_id, preserve_formatting=HTML_FORMATTING
                    )
                txt_formatted = formatter.format_transcript(transcript_text)
                video_data["Status"] = "SUCCESS"
                
                # Save transcript file using the computed absolute date as suffix
                transcript_file = save_text_file(transcripts_folder, video_title, date_suffix, txt_formatted)
                logging.info(f"Transcript saved for video: {video_id}")

                # Generate summary using OpenAI
                channel_details = f"Channel: {channel_username}"
                video_details = f"Title: {video_title}, URL: {video_url}"
                summary_text = generate_summary(txt_formatted, channel_details, video_details)
                # Save summary file with _summary appended to the absolute date suffix
                summary_file = save_text_file(summaries_folder, video_title, f"{date_suffix}_summary", summary_text)
                logging.info(f"Summary generated for video: {video_id}")

                # Convert summary text to audio and save to audio folder
                base_audio_name = sanitize_name(video_title)[:FILE_NAME_MAX_LENGTH] + f"_{date_suffix}"
                # base_audio_name += f"_{date_suffix}"
                audio_output_path = str(audio_folder / f"{base_audio_name}.mp3")
                synthesize_text_to_audio_long(summary_text, output_filename=audio_output_path)
                logging.info(f"Audio generated for video: {video_id}")

            except TooManyRequests:
                logging.warning(f"Too many requests for video {video_id}. Rate limit reached.")
                video_data["Status"] = "FAILED"
                break  # Exit loop to avoid too many retries
            except Exception as e:
                error_msg = str(e)
                if "Subtitles are disabled for this video" in error_msg:
                    logging.warning(f"Subtitles are disabled for video {video_id}")
                    video_data["Status"] = "FAILED - Subtitles disabled"
                else:
                    logging.warning(f"Error processing video {video_id}: {error_msg}")
                    video_data["Status"] = "FAILED"
            append_to_csv(csv_path, [video_data])
    except Exception as e:
        logging.error(f"Error processing channel {channel_username}: {e}")


def clean_summary_text(summary):
    """
    Remove markdown formatting symbols (e.g., asterisks, hashes, underscores, backticks)
    and extra whitespace from the summary.
    """
    # Remove symbols such as *, #, _, `
    cleaned = re.sub(r'[*#_`]', '', summary)
    # Remove extra spaces and newlines
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def generate_summary(transcript_text, channel_details, video_details, max_tokens=4000):
    """
    Generate a comprehensive and detailed summary from the transcript text using OpenAI's ChatCompletion API.
    The summary will cover all key insights and nuances, providing an in-depth explanation.
    """
    prompt = (
        "Using the details provided below, generate a comprehensive and detailed summary that thoroughly covers all key insights and nuances present in the transcript. "
        "Provide a detailed explanation including any critical analysis or observations that are relevant. "
        "Explain with examples from the transcript where applicable."
        "Explain Technical steps being explained where applicable."
        "Include Channel Name and Video details in begening."
        "Do not use any markdown formatting (avoid symbols like asterisks, hashes, underscores, or backticks).\n\n"
        f"Channel Details:\n{channel_details}\n\n"
        f"Video Details:\n{video_details}\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        "Detailed Summary:"
    )
    response = client.chat.completions.create(
        model="gpt-4.1-nano",  # Adjust as needed
        messages=[
            {"role": "system", "content": "You are a detailed and analytical summarization assistant. Do not use any markdown formatting in your output."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.5,
    )
    summary = response.choices[0].message.content.strip()
    # Clean the summary to remove unwanted markdown symbols
    cleaned_summary = clean_summary_text(summary)
    return cleaned_summary


def upload_to_drive(file_path, folder_id, mimetype=None, drive_service=None):
    """
    Uploads a file to Google Drive into the specified folder.
    If a file with the same name already exists, it skips the upload.
    Optionally accepts an existing drive_service to avoid reinitialization.
    """
    if drive_service is None:
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        drive_service = build('drive', 'v3', credentials=credentials)

    file_name = os.path.basename(file_path)
    # Build the query to check for an existing file with exactly the same name in the folder.
    query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    logging.info(f"Querying Drive with: {query}")
    
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        fields="files(id, name)"
    ).execute()
    existing_files = results.get("files", [])
    logging.info(f"Query returned {len(existing_files)} result(s) for file '{file_name}'.")
    
    if existing_files:
        logging.info(f"File '{file_name}' already exists in folder ID {folder_id}. Skipping upload.")
        return existing_files[0]["id"]

    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype=mimetype) if mimetype else MediaFileUpload(file_path)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')
    logging.info(f"Uploaded '{file_path}' to Drive folder ID: {folder_id} as file ID: {file_id}")
    return file_id

# ------------------ Step 3: Convert Summary to Audio ------------------
def chunk_text(text, max_bytes=4900):
    """
    Splits input text into chunks so that each chunk's UTF-8 byte length is below max_bytes.
    Splitting is done at sentence boundaries.
    """
    sentences = re.findall(r'[^.!?]+[.!?]+', text)
    if not sentences:
        sentences = [text]
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        next_chunk = current_chunk + sentence
        if len(next_chunk.encode('utf8')) <= max_bytes:
            current_chunk = next_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def synthesize_chunk(tts_client, text, retry_count=0):
    """
    Synthesizes a text chunk into MP3 audio content using Google Cloud TTS.
    Retries up to 3 times on temporary connection errors.
    """
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Standard-B",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0,
            sample_rate_hertz=24000,
        )
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except Exception as error:
        if retry_count < 3 and (hasattr(error, 'code') and error.code in ['ECONNRESET', 'ETIMEDOUT']):
            time.sleep(1 * (2 ** retry_count))
            return synthesize_chunk(tts_client, text, retry_count + 1)
        else:
            raise error

def synthesize_text_to_audio_long(text, output_filename="summary.mp3", max_bytes=4900):
    """
    Converts long text into an MP3 audio file by chunking the text, synthesizing each chunk,
    and concatenating the resulting MP3 audio content.
    """
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
    
    text_chunks = chunk_text(text, max_bytes=max_bytes)
    # logging.info(f"Split text into {len(text_chunks)} chunk(s).")
    
    audio_buffers = []
    for idx, chunk in enumerate(text_chunks):
        logging.info(f"Processing chunk {idx + 1}/{len(text_chunks)}...")
        audio_content = synthesize_chunk(tts_client, chunk)
        audio_buffers.append(audio_content)
        if idx < len(text_chunks) - 1:
            time.sleep(0.1)
    
    final_audio_content = b"".join(audio_buffers)
    with open(output_filename, "wb") as out:
        out.write(final_audio_content)
        logging.info(f'Audio content written to file "{output_filename}".')
    
    return output_filename

# ------------------ Step 4: Upload Files to Google Drive ------------------
def get_or_create_drive_folder(drive_service, folder_name, parent_folder_id=None):
    """
    Checks if a folder with the given name exists in Drive (optionally under a parent folder);
    if not, creates it.
    """
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if files:
        print(f"Folder '{folder_name}' found with ID: {files[0]['id']}")
        return files[0]['id']
    else:
        print(f"Folder '{folder_name}' not found. Creating new folder.")
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        print(f"Folder '{folder_name}' created with ID: {folder_id}")
        return folder_id




def main():
    # Local base folder for channels
    output_folder = Path("channels")
    output_folder.mkdir(exist_ok=True)
    
    channels = config.get("channels", [])
    if not channels:
        logging.error("No channels found in the configuration file.")
        exit(1)
    
    # Step 1: Process each channel locally (transcripts, summaries, audio)
    for username in channels:
        process_channel(username, output_folder)
    
    # Initialize Google Drive service (using drive.file scope)
    drive_service = get_drive_service(['https://www.googleapis.com/auth/drive.file'])
    base_folder_name = "YTTranscript"
    base_folder_id = get_or_create_drive_folder(drive_service, base_folder_name)
    
    # For each channel, create a subfolder in Drive and subfolders for Transcripts, Summaries, Audio
    for username in channels:
        channel_name = sanitize_name(username)
        local_channel_folder = output_folder / channel_name
        if not local_channel_folder.exists():
            logging.info(f"Local folder for channel {username} does not exist. Skipping upload.")
            continue
        
        # Create channel folder on Drive under base folder
        channel_drive_folder_id = get_or_create_drive_folder(drive_service, channel_name, parent_folder_id=base_folder_id)
        
        # Create subfolders on Drive for each type
        transcripts_drive_folder = get_or_create_drive_folder(drive_service, "Transcripts", parent_folder_id=channel_drive_folder_id)
        summaries_drive_folder = get_or_create_drive_folder(drive_service, "Summaries", parent_folder_id=channel_drive_folder_id)
        audio_drive_folder = get_or_create_drive_folder(drive_service, "Audio", parent_folder_id=channel_drive_folder_id)
        
        # Upload files from local subfolders to corresponding Drive folders and delete local files after upload
        for subfolder_name, drive_folder_id, mimetype in [
            ("Transcripts", transcripts_drive_folder, "text/plain"),
            ("Summaries", summaries_drive_folder, "text/plain"),
            ("Audio", audio_drive_folder, "audio/mpeg")
        ]:
            local_subfolder = local_channel_folder / subfolder_name
            if not local_subfolder.exists():
                logging.info(f"Local subfolder '{subfolder_name}' does not exist for channel {username}.")
                continue
            for file in local_subfolder.iterdir():
                if file.is_file():
                    file_id = upload_to_drive(str(file), folder_id=drive_folder_id, mimetype=mimetype, drive_service=drive_service)
                    # If upload succeeded (file_id is returned), delete the local file
                    if file_id:
                        try:
                            os.remove(file)
                            logging.info(f"Deleted local file: {file}")
                        except Exception as e:
                            logging.error(f"Error deleting local file {file}: {e}")

if __name__ == "__main__":
    main()