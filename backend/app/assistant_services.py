import json
import logging
import os
from typing import Any

import httpx


logger = logging.getLogger(__name__)

ASSISTANT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "candidate_profile_assistant",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "profile_updates": {
                    "type": "object",
                    "properties": {
                        "full_name": {"type": ["string", "null"]},
                        "phone": {"type": ["string", "null"]},
                        "location": {"type": ["string", "null"]},
                        "education": {"type": ["string", "null"]},
                        "experience": {"type": ["string", "null"]},
                        "skills": {
                            "type": ["array", "null"],
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "full_name",
                        "phone",
                        "location",
                        "education",
                        "experience",
                        "skills",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": ["reply", "profile_updates"],
            "additionalProperties": False,
        },
    },
}


class AssistantServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


def _authorization_header(variable: str) -> dict[str, str]:
    api_key = os.getenv(variable, "").strip()
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _configured_url(variable: str, path: str) -> str:
    base_url = os.getenv(variable, "").strip().rstrip("/")
    if not base_url:
        raise AssistantServiceError(
            f"{variable} is not configured. Configure the local service or continue by text."
        )
    try:
        endpoint = httpx.URL(f"{base_url}{path}")
    except httpx.InvalidURL as error:
        raise AssistantServiceError(f"{variable} must be a valid HTTP service URL.") from error
    if endpoint.scheme not in {"http", "https"} or not endpoint.host:
        raise AssistantServiceError(f"{variable} must be a valid HTTP service URL.")
    return str(endpoint)


async def generate_assistant_reply(messages: list[dict[str, str]]) -> dict[str, Any]:
    endpoint = _configured_url(
        "MAHARA_LLM_BASE_URL", "/v1/chat/completions"
    )
    payload: dict[str, Any] = {
        "model": os.getenv("MAHARA_LLM_MODEL", "qwen2.5-7b-instruct-1m"),
        "messages": messages,
        "temperature": 0.2,
        "response_format": ASSISTANT_RESPONSE_FORMAT,
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=_authorization_header("MAHARA_LLM_API_KEY"),
            )
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException as error:
        logger.warning("Local assistant model timed out.")
        raise AssistantServiceError("The assistant took too long to respond.") from error
    except httpx.HTTPStatusError as error:
        logger.error("Local assistant model returned HTTP %s.", error.response.status_code)
        raise AssistantServiceError("The assistant service rejected the request.") from error
    except (httpx.RequestError, json.JSONDecodeError) as error:
        logger.error(
            "Could not reach or decode the local assistant model (%s).",
            type(error).__name__,
        )
        raise AssistantServiceError("The assistant service is unavailable.") from error

    try:
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("Assistant response content is not text.")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise TypeError("Assistant response is not a JSON object.")
        return parsed
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        logger.error("Local assistant model returned an invalid response shape.")
        raise AssistantServiceError(
            "The assistant returned an invalid response. Please retry.",
            status_code=502,
        ) from error


async def generate_career_assistant_reply(messages: list[dict[str, str]]) -> str:
    endpoint = _configured_url("MAHARA_LLM_BASE_URL", "/v1/chat/completions")
    payload: dict[str, Any] = {
        "model": os.getenv("MAHARA_LLM_MODEL", "qwen2.5-7b-instruct-1m"),
        "messages": messages,
        "temperature": 0.4,
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=_authorization_header("MAHARA_LLM_API_KEY"),
            )
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException as error:
        logger.warning("Local career assistant model timed out.")
        raise AssistantServiceError("The assistant took too long to respond.") from error
    except httpx.HTTPStatusError as error:
        logger.error("Local career assistant model returned HTTP %s.", error.response.status_code)
        raise AssistantServiceError("The assistant service rejected the request.") from error
    except (httpx.RequestError, json.JSONDecodeError) as error:
        logger.error(
            "Could not reach or decode the local career assistant model (%s).",
            type(error).__name__,
        )
        raise AssistantServiceError("The assistant service is unavailable.") from error

    try:
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise TypeError("Assistant response content is not non-empty text.")
        return content.strip()
    except (KeyError, IndexError, TypeError) as error:
        logger.error("Local career assistant model returned an invalid response shape.")
        raise AssistantServiceError(
            "The assistant returned an invalid response. Please retry.",
            status_code=502,
        ) from error


async def transcribe_audio(audio: bytes, filename: str, content_type: str) -> str:
    endpoint = _configured_url(
        "MAHARA_WHISPER_BASE_URL", "/v1/audio/transcriptions"
    )
    data = {
        "model": os.getenv("MAHARA_WHISPER_MODEL", "whisper-large-v3-turbo"),
        "prompt": "Tunisian Arabic (Derja), French, and Arabic speech.",
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                endpoint,
                data=data,
                files={"file": (filename, audio, content_type)},
                headers=_authorization_header("MAHARA_WHISPER_API_KEY"),
            )
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException as error:
        logger.warning("Local Whisper service timed out.")
        raise AssistantServiceError("Voice transcription took too long.") from error
    except httpx.HTTPStatusError as error:
        logger.error("Local Whisper service returned HTTP %s.", error.response.status_code)
        raise AssistantServiceError("The voice transcription service rejected the audio.") from error
    except (httpx.RequestError, json.JSONDecodeError) as error:
        logger.error(
            "Could not reach or decode the local Whisper service (%s).",
            type(error).__name__,
        )
        raise AssistantServiceError("Voice transcription is unavailable.") from error

    if not isinstance(result, dict):
        logger.error("Local Whisper service returned an invalid response shape.")
        raise AssistantServiceError(
            "The voice transcription service returned an invalid response.",
            status_code=502,
        )
    transcript = result.get("text")
    if not isinstance(transcript, str) or not transcript.strip():
        raise AssistantServiceError(
            "No speech was recognized. You can enter your answer by text.",
            status_code=422,
        )
    return transcript.strip()


async def synthesize_speech(text: str) -> tuple[bytes, str]:
    endpoint = _configured_url("MAHARA_TTS_BASE_URL", "/v1/audio/speech")
    payload = {
        "model": os.getenv("MAHARA_TTS_MODEL", "tts-1"),
        "voice": os.getenv("MAHARA_TTS_VOICE", "alloy"),
        "input": text,
        "response_format": "mp3",
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers=_authorization_header("MAHARA_TTS_API_KEY"),
            )
            response.raise_for_status()
    except httpx.TimeoutException as error:
        logger.warning("Local TTS service timed out.")
        raise AssistantServiceError("Spoken audio took too long to generate.") from error
    except httpx.HTTPStatusError as error:
        logger.error("Local TTS service returned HTTP %s.", error.response.status_code)
        raise AssistantServiceError("The spoken-response service rejected the request.") from error
    except httpx.RequestError as error:
        logger.error("Could not reach the local TTS service (%s).", type(error).__name__)
        raise AssistantServiceError("Spoken responses are unavailable.") from error

    if not response.content:
        logger.error("Local TTS service returned an empty audio response.")
        raise AssistantServiceError(
            "The spoken-response service returned empty audio.",
            status_code=502,
        )
    return response.content, response.headers.get("content-type", "audio/mpeg")
