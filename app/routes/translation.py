import json
import logging

from fastapi import APIRouter, HTTPException, Request

from app.limiter import limiter
from app.schemas.translation import TranslationRequest, TranslationResponse
from app.services.translation import translate_texts

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/translate", response_model=TranslationResponse)
@limiter.limit("8/minute")
async def translate_page(request: Request, payload: TranslationRequest):
    try:
        translations = await translate_texts(payload.language, payload.texts)
        return TranslationResponse(translations=translations)
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="Translation timed out") from error
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        logger.warning("Translation response error: %s", error)
        raise HTTPException(status_code=502, detail="Translation response was invalid") from error
    except Exception as error:
        logger.exception("Translation failed: %s", error)
        raise HTTPException(status_code=503, detail="Translation is temporarily unavailable") from error
