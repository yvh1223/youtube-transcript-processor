# ABOUTME: OpenAI-powered text summarization for video transcripts
import re
import logging
import certifi
import httpx
from openai import OpenAI


class Summarizer:
    """Handles text summarization using OpenAI API"""

    def __init__(self, config):
        self.config = config

        # Create httpx client with explicit SSL certificate verification using venv's certifi
        import os

        # Set SSL_CERT_FILE to point to venv's certifi bundle
        # This fixes Python 3.13 SSL verification issues in virtual environments
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

        http_client = httpx.Client(
            verify=certifi.where(),
            timeout=60.0
        )

        self.client = OpenAI(http_client=http_client)

        if not self.client.api_key:
            raise Exception(
                "OPENAI_API_KEY is not set. Please set it to your valid OpenAI API key."
            )

    def generate_summary(self, transcript_text, channel_details, video_details):
        """
        Generate a comprehensive and detailed summary from the transcript text
        using OpenAI's ChatCompletion API.
        """
        prompt = (
            "Using the details provided below, generate a comprehensive and detailed summary that thoroughly covers all key insights and nuances present in the transcript. "
            "Provide a detailed explanation including any critical analysis or observations that are relevant. "
            "Explain with examples from the transcript where applicable."
            "Explain Technical steps being explained where applicable."
            "Include Channel Name and Video details in beginning."
            "Do not use any markdown formatting (avoid symbols like asterisks, hashes, underscores, or backticks).\n\n"
            f"Channel Details:\n{channel_details}\n\n"
            f"Video Details:\n{video_details}\n\n"
            f"Transcript:\n{transcript_text}\n\n"
            "Detailed Summary:"
        )

        response = self.client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a detailed and analytical summarization assistant. Do not use any markdown formatting in your output.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        summary = response.choices[0].message.content.strip()
        cleaned_summary = self._clean_summary_text(summary)
        return cleaned_summary

    def _clean_summary_text(self, summary):
        """
        Remove markdown formatting symbols and extra whitespace from the summary.
        """
        # Remove symbols such as *, #, _, `
        cleaned = re.sub(r"[*#_`]", "", summary)
        # Remove extra spaces and newlines
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()
