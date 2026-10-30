"""Calls the Gemini API to generate short health remarks from blood test values."""
import logging
from datetime import date

from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Stored in Remarks when the API cannot be reached. The views check for this text.
REMARKS_UNAVAILABLE = 'Remarks unavailable, please retry.'

TIMEOUT_SECONDS = 20


def calculate_age(date_of_birth):
    """Return age in whole years as of today."""
    today = date.today()
    had_birthday = (today.month, today.day) >= (date_of_birth.month, date_of_birth.day)
    return today.year - date_of_birth.year - (0 if had_birthday else 1)


def build_prompt(age, glucose, haemoglobin, cholesterol):
    """Build the text sent to Gemini."""
    return (
        "You are a health screening assistant. Based on these blood test results, "
        "state the possible health condition or disease risk in 2 to 3 plain sentences.\n\n"
        f"Age: {age} years\n"
        f"Glucose: {glucose:g} mg/dL\n"
        f"Haemoglobin: {haemoglobin:g} g/dL\n"
        f"Cholesterol: {cholesterol:g} mg/dL\n\n"
        "Rules:\n"
        "- Name the likely risk for each abnormal value (for example diabetes, "
        "anaemia, polycythaemia, high cholesterol).\n"
        "- If everything is within normal range, say so.\n"
        "- No markdown, no bullet points, no headings.\n"
        "- End with: This is not medical advice."
    )


def get_health_remarks(date_of_birth, glucose, haemoglobin, cholesterol):
    """Return AI-generated remarks, or REMARKS_UNAVAILABLE if anything goes wrong.

    This function never raises, so a failed API call cannot stop a record
    from being saved.
    """
    if not settings.GEMINI_API_KEY:
        logger.error('GEMINI_API_KEY is not set.')
        return REMARKS_UNAVAILABLE

    try:
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000),  # milliseconds
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=build_prompt(calculate_age(date_of_birth),
                                  glucose, haemoglobin, cholesterol),
        )
        text = (response.text or '').strip()
        return text if text else REMARKS_UNAVAILABLE
    except Exception:
        logger.exception('Gemini API call failed.')
        return REMARKS_UNAVAILABLE