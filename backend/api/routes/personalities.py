"""
Personalities discovery endpoint.

Provides an endpoint to list available personalities by reading
from the prompts directory.
"""

from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# System personalities that are excluded from debate participation
SYSTEM_PERSONALITIES = {"consensus_check", "synthesizer"}

# Path to prompts directory (relative to backend root)
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PersonalityInfo(BaseModel):
    """Information about an available personality."""

    name: str
    description: str
    is_system: bool


class PersonalitiesResponse(BaseModel):
    """Response containing available personalities."""

    personalities: list[PersonalityInfo]
    total: int


def get_available_personalities() -> list[PersonalityInfo]:
    """
    Get list of available personalities from the prompts directory.

    Reads all .txt files from the prompts/ directory and extracts
    the first line as the description.

    Returns:
        List of PersonalityInfo objects
    """
    personalities = []

    if not PROMPTS_DIR.exists():
        return personalities

    for prompt_file in sorted(PROMPTS_DIR.glob("*.txt")):
        name = prompt_file.stem  # filename without extension

        # Read first line as description
        try:
            content = prompt_file.read_text()
            first_line = content.split("\n")[0].strip()
            # Truncate long descriptions
            description = first_line[:200] + "..." if len(first_line) > 200 else first_line
        except Exception:
            description = ""

        personalities.append(
            PersonalityInfo(
                name=name,
                description=description,
                is_system=name in SYSTEM_PERSONALITIES,
            )
        )

    return personalities


@router.get("", response_model=PersonalitiesResponse)
async def list_personalities() -> PersonalitiesResponse:
    """
    List available personalities.

    Reads personality prompt files from the prompts/ directory.
    Returns name, description (first line of prompt), and whether
    it's a system personality (excluded from default debate participants).

    System personalities (consensus_check, synthesizer) are used internally
    for debate orchestration and should not be selected as debate participants.
    """
    personalities = get_available_personalities()
    return PersonalitiesResponse(
        personalities=personalities,
        total=len(personalities),
    )


@router.get("/debate", response_model=PersonalitiesResponse)
async def list_debate_personalities() -> PersonalitiesResponse:
    """
    List personalities available for debate participation.

    Same as /personalities but excludes system personalities
    (consensus_check, synthesizer).
    """
    all_personalities = get_available_personalities()
    debate_personalities = [p for p in all_personalities if not p.is_system]
    return PersonalitiesResponse(
        personalities=debate_personalities,
        total=len(debate_personalities),
    )
