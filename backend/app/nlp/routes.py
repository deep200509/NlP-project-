"""API endpoints that expose the NLP pipeline (testable from /docs)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.nlp.intent_classifier import predict_intent
from app.nlp.preprocessor import preprocess

router = APIRouter(prefix="/nlp", tags=["NLP"])


class TextIn(BaseModel):
    text: str = Field(min_length=2, max_length=500,
                      examples=["Users should be able to remove a book"])


@router.post("/preprocess")
def preprocess_text(body: TextIn):
    """Shows every preprocessing step for a sentence."""
    return preprocess(body.text)


@router.post("/intent")
def classify_intent(body: TextIn):
    """Predicts the intent (CREATE, READ, ...) with a confidence score."""
    try:
        return predict_intent(body.text)
    except FileNotFoundError as err:
        raise HTTPException(status_code=503, detail=str(err))