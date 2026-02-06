from fastapi import APIRouter, Request, Depends, HTTPException, status
from ..services.search import search_jobs
from ..services.recommend import transitions_for
from ..services.lmi import get_weekly_insights, get_attachment_companies
from ..normalization.titles import get_careers_for_degree
from ..db.database import get_db
from ..core.config import settings
from ..core.rate_limiter import rate_limit
from sqlalchemy.orm import Session
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


async def send_whatsapp_message(to_number: str, message: str) -> bool:
    """
    Send a WhatsApp message via Twilio API.

    Args:
        to_number: Recipient phone number (with country code)
        message: Message text to send

    Returns:
        True if message was sent successfully, False otherwise
    """
    if not all(
        [
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_WHATSAPP_FROM,
        ]
    ):
        logger.warning("Twilio WhatsApp credentials not configured")
        return False

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Ensure phone numbers are in WhatsApp format
        from_number = settings.TWILIO_WHATSAPP_FROM
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        message_obj = client.messages.create(
            body=message, from_=from_number, to=to_number
        )

        logger.info(f"WhatsApp message sent successfully. SID: {message_obj.sid}")
        return True

    except ImportError:
        logger.error("Twilio package not installed. Run: pip install twilio")
        return False
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        return False


def parse_intent(text: str) -> dict:
    """Parse user intent from WhatsApp message"""
    text_lower = text.lower().strip()

    # Degree/study patterns
    degree_patterns = [
        r"i studied (\w+(?:\s+\w+)*)",
        r"degree in (\w+(?:\s+\w+)*)",
        r"(\w+(?:\s+\w+)*) graduate",
        r"background in (\w+(?:\s+\w+)*)",
    ]

    for pattern in degree_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return {"intent": "degree_careers", "degree": match.group(1).strip()}

    # Transition patterns
    if "transition" in text_lower:
        current_role = (
            text.split("transition", 1)[1].strip() if "transition" in text else ""
        )
        return {"intent": "transition", "current_role": current_role or "data analyst"}

    # Attachment/internship patterns
    if any(
        word in text_lower
        for word in ["attachment", "intern", "internship", "graduate program"]
    ):
        location = extract_location(text)
        return {"intent": "attachments", "location": location}

    # Market insights patterns
    if any(word in text_lower for word in ["market", "trends", "insights", "hiring"]):
        location = extract_location(text)
        return {"intent": "market_insights", "location": location}

    # Salary inquiry patterns
    if any(
        word in text_lower for word in ["salary", "pay", "compensation", "earnings"]
    ):
        role = extract_role_from_salary_query(text)
        location = extract_location(text)
        return {"intent": "salary", "role": role, "location": location}

    # Default to job search
    location = extract_location(text)
    return {"intent": "search", "query": text, "location": location}


def extract_location(text: str) -> str | None:
    """Extract location from text"""
    kenyan_locations = [
        "nairobi",
        "mombasa",
        "kisumu",
        "nakuru",
        "eldoret",
        "thika",
        "malindi",
        "kitale",
        "garissa",
        "kakamega",
        "machakos",
        "meru",
        "nyeri",
        "kericho",
    ]

    text_lower = text.lower()
    for location in kenyan_locations:
        if location in text_lower:
            return location.title()

    return None


def extract_role_from_salary_query(text: str) -> str | None:
    """Extract role from salary query"""
    # Look for patterns like "data analyst salary" or "salary for accountant"
    patterns = [
        r"(\w+(?:\s+\w+)*)\s+salary",
        r"salary\s+for\s+(\w+(?:\s+\w+)*)",
        r"how much do (\w+(?:\s+\w+)*) earn",
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1).strip()

    return None


def format_whatsapp_message(content: str, max_length: int = 1500) -> str:
    """Format message for WhatsApp with length limits"""
    if len(content) <= max_length:
        return content

    # Truncate and add continuation message
    truncated = content[: max_length - 50]
    return f"{truncated}...\n\n📱 Visit our web app for full details!"


def _webhook_validation_url(request: Request) -> str:
    # Prefer explicit config to avoid proxy/host mismatches.
    if settings.TWILIO_WEBHOOK_URL:
        return settings.TWILIO_WEBHOOK_URL

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return str(request.url.replace(scheme=forwarded_proto, netloc=forwarded_host))

    return str(request.url)


def _validate_twilio_signature(request: Request, form: dict) -> None:
    """Validate inbound webhook came from Twilio (if configured)."""
    if not settings.TWILIO_VALIDATE_WEBHOOK_SIGNATURE:
        return

    if not settings.TWILIO_AUTH_TOKEN:
        logger.warning(
            "TWILIO_VALIDATE_WEBHOOK_SIGNATURE=true but TWILIO_AUTH_TOKEN is not set; skipping signature validation"
        )
        return

    signature = request.headers.get("x-twilio-signature") or ""
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Missing Twilio signature"
        )

    try:
        from twilio.request_validator import RequestValidator

        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        url = _webhook_validation_url(request)

        # Twilio expects a mapping of str -> str values.
        params = {k: v for k, v in form.items()}

        if not validator.validate(url, params, signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature"
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Fail closed when validation is enabled.
        logger.error(f"Twilio signature validation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook signature validation failed",
        )


@router.post("/webhook")
@rate_limit(max_requests=120, window_seconds=60)  # Twilio may retry; allow bursts.
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 100_000:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Request too large",
                )
        except ValueError:
            pass

    form_data = await request.form()
    # Flatten form values (Starlette returns form items as strings already for Twilio).
    form = dict(form_data)
    _validate_twilio_signature(request, form)

    body = (form.get("Body") or "").strip()

    if not body:
        return {
            "message": "👋 Hi! I'm your Career Advisor. Try:\n• 'I studied economics'\n• 'transition data analyst'\n• 'attachments Nairobi'\n• 'market insights'"
        }

    # Parse user intent
    intent_data = parse_intent(body)
    intent = intent_data["intent"]

    try:
        if intent == "degree_careers":
            degree = intent_data["degree"]
            careers = get_careers_for_degree(degree)

            msg = f"🎓 *{degree.title()} Career Paths:*\n\n"
            for i, career in enumerate(careers[:5], 1):
                msg += f"{i}. {career.title()}\n"

            msg += f"\n💡 Try: 'search {careers[0]} jobs' for opportunities!"

        elif intent == "transition":
            current_role = intent_data["current_role"]
            recs = transitions_for(db, current_role)

            if not recs:
                msg = f"🔄 No specific transitions found for '{current_role}'. Try a more common role title."
            else:
                msg = f"🔄 *Career Transitions from {current_role.title()}:*\n\n"
                for i, rec in enumerate(recs[:3], 1):
                    skills_text = (
                        f"Learn: {', '.join(rec['gap_skills'])}"
                        if rec["gap_skills"]
                        else "Good skill match!"
                    )
                    msg += f"{i}. *{rec['target_role']}* ({rec['overlap']}% match)\n   {skills_text}\n\n"

        elif intent == "attachments":
            location = intent_data.get("location")
            companies = get_attachment_companies(db, location=location)

            if not companies["companies_with_attachments"]:
                msg = "🎯 No attachment programs found"
                if location:
                    msg += f" in {location}"
                msg += ". Try broader search or check back later."
            else:
                msg = "🎯 *Attachment Opportunities"
                if location:
                    msg += f" in {location}"
                msg += ":*\n\n"

                for i, company in enumerate(
                    companies["companies_with_attachments"][:5], 1
                ):
                    msg += f"{i}. *{company['company']}*\n"
                    msg += f"   {company['sector'] or 'Various sectors'}\n"
                    msg += f"   {company['attachment_postings']} programs\n\n"

                msg += f"💡 {companies['application_timing']}"

        elif intent == "market_insights":
            location = intent_data.get("location")
            insights = get_weekly_insights(db, location=location)

            msg = "📊 *Market Insights"
            if location:
                msg += f" - {location}"
            msg += ":*\n\n"

            msg += f"📈 {insights['total_postings']} new jobs this week"
            if insights["week_over_week_change"] != 0:
                change_emoji = "📈" if insights["week_over_week_change"] > 0 else "📉"
                msg += f" ({change_emoji}{insights['week_over_week_change']:+d})"
            msg += "\n\n"

            if insights["top_hiring_companies"]:
                msg += "*Top Hiring:*\n"
                for company in insights["top_hiring_companies"][:3]:
                    msg += f"• {company['company']} ({company['postings']} jobs)\n"
                msg += "\n"

            if insights["trending_skills"]:
                msg += "*Trending Skills:*\n"
                for skill in insights["trending_skills"][:3]:
                    msg += f"• {skill['skill']} (+{skill['growth_rate']}%)\n"

        elif intent == "salary":
            role = intent_data.get("role")
            location = intent_data.get("location")

            if not role:
                msg = "💰 Please specify a role. Try: 'data analyst salary' or 'accountant salary Nairobi'"
            else:
                from ..services.recommend import get_salary_insights_for_transition

                salary_data = get_salary_insights_for_transition(db, role)

                if salary_data["sample_size"] == 0:
                    msg = f"💰 Limited salary data for {role.title()}. Try a more common role title."
                else:
                    msg = f"💰 *{role.title()} Salary Insights:*\n\n"
                    if salary_data["median_salary_min"]:
                        msg += f"Median: KES {salary_data['median_salary_min']:,.0f}"
                        if salary_data["median_salary_max"]:
                            msg += f" - {salary_data['median_salary_max']:,.0f}"
                        msg += "\n"
                    msg += f"\n{salary_data['coverage']}"

        else:  # Default search
            query = intent_data["query"]
            location = intent_data.get("location")
            results = search_jobs(db, q=query, location=location, seniority="entry")

            if not results or (len(results) == 1 and results[0].get("is_suggestion")):
                msg = "🔍 No matches found. Try:\n• 'I studied [your degree]'\n• 'transition [current role]'\n• 'attachments [location]'"
            else:
                msg = "🔍 *Job Matches:*\n\n"
                for i, job in enumerate(results[:3], 1):
                    if job.get("is_suggestion"):
                        continue
                    msg += f"{i}. *{job['title']}*\n"
                    msg += f"   @ {job['organization']}\n"
                    if job.get("location"):
                        msg += f"   📍 {job['location']}\n"
                    if job.get("why_match"):
                        msg += f"   ✨ {job['why_match']}\n"
                    msg += "\n"

                msg += "💡 Reply with company name for more details!"

    except Exception as e:
        msg = "⚠️ Something went wrong. Please try again or rephrase your question."
        logger.error(f"WhatsApp webhook error: {e}")

    # Format and return response
    formatted_msg = format_whatsapp_message(msg)
    return {"message": formatted_msg}
