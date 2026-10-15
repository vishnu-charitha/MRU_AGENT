import re
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, StudentRegistration
from ..models import (
    StudentRegisterRequest,
    StudentRegisterResponse,
    SessionValidateResponse,
)
from ..auth import create_access_token, require_student_session

router = APIRouter()
logger = logging.getLogger("api")

ALLOWED_COURSES = {"B.Tech", "M.Tech", "Not sure yet"}
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
INDIAN_MOBILE_DIGITS_REGEX = re.compile(r"^[6-9]\d{9}$")


def normalize_and_validate_mobile(mobile: str) -> str:
    cleaned = re.sub(r"[\s\-\(\)]", "", mobile.strip())
    if cleaned.startswith("+91"):
        national = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        national = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        national = cleaned[1:]
    else:
        national = cleaned

    if not INDIAN_MOBILE_DIGITS_REGEX.match(national):
        raise HTTPException(
            status_code=422,
            detail="Please provide a valid 10-digit Indian mobile number."
        )

    return f"+91{national}"


def validate_registration_payload(request: StudentRegisterRequest) -> dict:
    name = request.full_name.strip()
    if len(name) < 2 or len(name) > 100:
        raise HTTPException(
            status_code=422,
            detail="Full name must be between 2 and 100 characters."
        )
    if not any(c.isalpha() for c in name):
        raise HTTPException(
            status_code=422,
            detail="Full name must contain alphabetic characters."
        )

    email = request.email.strip().lower()
    if len(email) > 255 or not EMAIL_REGEX.match(email):
        raise HTTPException(
            status_code=422,
            detail="Please provide a valid email address."
        )

    normalized_mobile = normalize_and_validate_mobile(request.mobile_number)

    course = request.interested_course.strip()
    if course not in ALLOWED_COURSES:
        raise HTTPException(
            status_code=422,
            detail=f"Interested course must be one of: {', '.join(sorted(ALLOWED_COURSES))}."
        )

    if not request.consent:
        raise HTTPException(
            status_code=422,
            detail="Consent is mandatory to continue."
        )

    return {
        "full_name": name,
        "email": email,
        "mobile_number": normalized_mobile,
        "interested_course": course,
    }


@router.post("/students/register", response_model=StudentRegisterResponse)
def register_student(request: StudentRegisterRequest, db: Session = Depends(get_db)):
    validated = validate_registration_payload(request)
    now = datetime.now(timezone.utc)
    student_id = str(uuid.uuid4())

    new_student = StudentRegistration(
        id=student_id,
        full_name=validated["full_name"],
        email=validated["email"],
        mobile_number=validated["mobile_number"],
        interested_course=validated["interested_course"],
        consent_at=now,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(new_student)
        db.commit()
        db.refresh(new_student)
    except Exception as e:
        db.rollback()
        # Strictly avoid logging student personal data (PII)
        logger.error(f"Failed to persist student registration record to database: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save registration. Please try again later."
        )

    logger.info(f"Student successfully registered: student_id={student_id}")

    try:
        token = create_access_token(student_id=student_id)
    except Exception as e:
        logger.error(f"Failed to generate access token for student: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate session token."
        )

    return StudentRegisterResponse(
        success=True,
        student_id=student_id,
        token=token,
        message="Registration successful. Welcome to MRDU Assistant!"
    )


@router.get("/students/session", response_model=SessionValidateResponse)
def validate_student_session(
    student_id: str = Depends(require_student_session),
):
    return SessionValidateResponse(
        valid=True,
        student_id=student_id,
    )
