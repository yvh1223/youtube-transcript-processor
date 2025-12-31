# ABOUTME: Utility functions for file operations, naming, and data management
import re
import os
import pandas as pd
from pathlib import Path
from datetime import timedelta


def sanitize_name(name):
    """Sanitize folder or file names by removing special characters and spaces."""
    return re.sub(r"[^\w\s\u4e00-\u9fff]", "", name.strip().replace(" ", "_"))


def append_to_csv(file_path, data):
    """Append data to a CSV file, creating it if it doesn't exist.
    Updates existing rows if Video ID and Upload Date match."""
    columns = ["Video URL", "Video ID", "Upload Date", "Scrape Date", "Status"]
    df = pd.DataFrame(data, columns=columns)
    if not os.path.exists(file_path):
        df.to_csv(file_path, index=False)
    else:
        existing = pd.read_csv(file_path)
        combined = pd.concat([existing, df]).drop_duplicates(
            subset=["Video ID", "Upload Date"],
            keep='last'  # Keep the most recent entry (new data)
        )
        combined.to_csv(file_path, index=False)


def save_text_file(folder, base_name, suffix, text, max_length=30):
    """
    Save text content to a file in the specified folder.
    The file will be named as: {sanitized_base_name}_{suffix}.txt,
    where 'suffix' is the computed published date (e.g., YYYYMMDD).
    """
    file_name = sanitize_name(base_name)[:max_length]
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
    match = re.match(
        r"(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)", text
    )
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
