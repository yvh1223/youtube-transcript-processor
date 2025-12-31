# ABOUTME: Text-to-speech conversion using Google Cloud TTS API
import os
import re
import time
import logging
from google.cloud import texttospeech
from google.oauth2 import service_account


class TextToSpeech:
    """Handles text-to-speech conversion using Google Cloud TTS"""

    def __init__(self, config):
        self.config = config
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
        self.tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

    def synthesize_text_to_audio(self, text, output_filename, max_bytes=4900):
        """
        Converts long text into an MP3 audio file by chunking the text,
        synthesizing each chunk, and concatenating the resulting MP3 audio content.
        """
        text_chunks = self._chunk_text(text, max_bytes=max_bytes)

        audio_buffers = []
        for idx, chunk in enumerate(text_chunks):
            logging.info(f"Processing audio chunk {idx + 1}/{len(text_chunks)}...")
            audio_content = self._synthesize_chunk(chunk)
            audio_buffers.append(audio_content)
            if idx < len(text_chunks) - 1:
                time.sleep(0.1)

        final_audio_content = b"".join(audio_buffers)
        with open(output_filename, "wb") as out:
            out.write(final_audio_content)
            logging.info(f'Audio content written to file "{output_filename}".')

        return output_filename

    def _chunk_text(self, text, max_bytes=4900):
        """
        Splits input text into chunks so that each chunk's UTF-8 byte length
        is below max_bytes. Splitting is done at sentence boundaries.
        """
        sentences = re.findall(r"[^.!?]+[.!?]+", text)
        if not sentences:
            sentences = [text]

        chunks = []
        current_chunk = ""
        for sentence in sentences:
            next_chunk = current_chunk + sentence
            if len(next_chunk.encode("utf8")) <= max_bytes:
                current_chunk = next_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _synthesize_chunk(self, text, retry_count=0):
        """
        Synthesizes a text chunk into MP3 audio content using Google Cloud TTS.
        Retries up to 3 times on temporary connection errors.
        """
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Map gender string to enum
            gender_map = {
                "NEUTRAL": texttospeech.SsmlVoiceGender.NEUTRAL,
                "MALE": texttospeech.SsmlVoiceGender.MALE,
                "FEMALE": texttospeech.SsmlVoiceGender.FEMALE,
            }
            voice_gender = gender_map.get(
                self.config.tts_voice_gender,
                texttospeech.SsmlVoiceGender.NEUTRAL
            )

            voice = texttospeech.VoiceSelectionParams(
                language_code=self.config.tts_language_code,
                name=self.config.tts_voice_name,
                ssml_gender=voice_gender,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.config.tts_speaking_rate,
                pitch=0.0,
                volume_gain_db=self.config.tts_volume_gain,
                sample_rate_hertz=self.config.tts_sample_rate,
            )

            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            return response.audio_content

        except Exception as error:
            if retry_count < 3 and (
                hasattr(error, "code")
                and error.code in ["ECONNRESET", "ETIMEDOUT"]
            ):
                time.sleep(1 * (2**retry_count))
                return self._synthesize_chunk(text, retry_count + 1)
            else:
                raise error
