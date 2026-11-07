import logging
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.assistant_services import AssistantServiceError, transcribe_audio
from app.models import (
    CandidateInterviewTranscription,
    InterviewTranscriptionStatus,
)


logger = logging.getLogger(__name__)


async def process_interview_transcription(
    transcription_id: str,
    audio: bytes,
    content_type: str,
    session_factory: Callable[[], Session],
) -> None:
    with session_factory() as session:
        transcription = session.get(CandidateInterviewTranscription, transcription_id)
        if transcription is None:
            logger.error("Queued interview transcription %s no longer exists.", transcription_id)
            return
        if transcription.status != InterviewTranscriptionStatus.QUEUED:
            logger.warning(
                "Interview transcription %s was not queued when processing began.",
                transcription_id,
            )
            return
        transcription.status = InterviewTranscriptionStatus.PROCESSING
        session.commit()

    try:
        transcript = await transcribe_audio(
            audio,
            "interview-answer",
            content_type,
        )
    except AssistantServiceError as error:
        logger.warning(
            "Interview transcription %s failed with service status %s.",
            transcription_id,
            error.status_code,
        )
        with session_factory() as session:
            transcription = session.get(CandidateInterviewTranscription, transcription_id)
            if transcription is not None:
                transcription.status = InterviewTranscriptionStatus.FAILED
                transcription.error_message = str(error)[:500]
                session.commit()
        return
    except Exception:
        logger.exception("Interview transcription %s failed unexpectedly.", transcription_id)
        with session_factory() as session:
            transcription = session.get(CandidateInterviewTranscription, transcription_id)
            if transcription is not None:
                transcription.status = InterviewTranscriptionStatus.FAILED
                transcription.error_message = (
                    "Transcription processing failed. Please retry or enter your answer by text."
                )
                session.commit()
        return

    if len(transcript) > 10000:
        logger.error(
            "Interview transcription %s exceeded the supported transcript length.",
            transcription_id,
        )
        with session_factory() as session:
            transcription = session.get(CandidateInterviewTranscription, transcription_id)
            if transcription is not None:
                transcription.status = InterviewTranscriptionStatus.FAILED
                transcription.error_message = (
                    "The recognized response is too long. Please record a shorter answer."
                )
                session.commit()
        return

    with session_factory() as session:
        transcription = session.get(CandidateInterviewTranscription, transcription_id)
        if transcription is None:
            logger.error("Interview transcription %s disappeared after processing.", transcription_id)
            return
        transcription.status = InterviewTranscriptionStatus.COMPLETED
        transcription.transcript = transcript
        transcription.error_message = None
        session.commit()
