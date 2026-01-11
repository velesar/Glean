"""
Settings Router

Endpoints for managing user settings and API credentials.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.database import Database
from web.api.deps import get_db, get_current_user

router = APIRouter()


# Predefined setting schemas for validation and documentation
API_KEY_SETTINGS = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "description": "API key for Claude AI models used by analyzers",
        "placeholder": "sk-ant-...",
    },
    "openai": {
        "label": "OpenAI",
        "description": "API key for OpenAI models (optional)",
        "placeholder": "sk-...",
    },
    "reddit_client_id": {
        "label": "Reddit Client ID",
        "description": "OAuth client ID for Reddit API access",
        "placeholder": "Client ID",
    },
    "reddit_client_secret": {
        "label": "Reddit Client Secret",
        "description": "OAuth client secret for Reddit API",
        "placeholder": "Client Secret",
    },
    "reddit_username": {
        "label": "Reddit Username",
        "description": "Reddit account username for API authentication",
        "placeholder": "username",
    },
    "reddit_password": {
        "label": "Reddit Password",
        "description": "Reddit account password for API authentication",
        "placeholder": "password",
    },
}

SCOUT_SETTINGS = {
    "reddit_subreddits": {
        "label": "Reddit Subreddits",
        "description": "Comma-separated list of subreddits to scout",
        "placeholder": "salesautomation, artificial, startups",
        "default": "salesautomation, artificial, startups",
    },
    "reddit_post_limit": {
        "label": "Reddit Post Limit",
        "description": "Maximum posts to fetch per subreddit",
        "placeholder": "50",
        "default": "50",
    },
}

ANALYZER_SETTINGS = {
    "model": {
        "label": "AI Model",
        "description": "Model to use for analysis",
        "placeholder": "claude-sonnet-4-20250514",
        "default": "claude-sonnet-4-20250514",
        "options": [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "gpt-4o",
            "gpt-4o-mini",
        ],
    },
    "min_confidence": {
        "label": "Minimum Confidence",
        "description": "Minimum confidence score for extracted claims",
        "placeholder": "0.5",
        "default": "0.5",
    },
}


class SettingUpdate(BaseModel):
    """Request to update a setting."""
    value: str
    is_secret: bool = False


class SettingResponse(BaseModel):
    """Response for a single setting."""
    category: str
    key: str
    value: Optional[str]
    is_secret: bool
    label: str
    description: str
    placeholder: Optional[str] = None
    default: Optional[str] = None
    options: Optional[list[str]] = None


class SettingsSchemaResponse(BaseModel):
    """Response containing available settings schema."""
    api_keys: dict
    scouts: dict
    analyzers: dict


def mask_secret(value: str) -> str:
    """Mask a secret value for display."""
    if not value or len(value) < 8:
        return "••••••••"
    return value[:4] + "•" * (len(value) - 8) + value[-4:]


def get_setting_metadata(category: str, key: str) -> dict:
    """Get metadata for a setting."""
    schemas = {
        "api_keys": API_KEY_SETTINGS,
        "scouts": SCOUT_SETTINGS,
        "analyzers": ANALYZER_SETTINGS,
    }
    category_schema = schemas.get(category, {})
    return category_schema.get(key, {
        "label": key.replace("_", " ").title(),
        "description": "",
        "placeholder": "",
    })


@router.get("/schema")
async def get_settings_schema(current_user: dict = Depends(get_current_user)):
    """Get the schema of all available settings."""
    return {
        "api_keys": API_KEY_SETTINGS,
        "scouts": SCOUT_SETTINGS,
        "analyzers": ANALYZER_SETTINGS,
    }


@router.get("")
async def get_all_settings(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Get all settings for the current user."""
    settings = db.get_all_settings(current_user["id"])

    # Build response with metadata and masked secrets
    result = {}
    for category in ["api_keys", "scouts", "analyzers"]:
        result[category] = {}
        cat_settings = settings.get(category, {})

        # Get schema for this category
        schemas = {
            "api_keys": API_KEY_SETTINGS,
            "scouts": SCOUT_SETTINGS,
            "analyzers": ANALYZER_SETTINGS,
        }
        schema = schemas.get(category, {})

        # Include all defined settings, even if not set
        for key, meta in schema.items():
            setting = cat_settings.get(key)
            if setting:
                value = setting["value"]
                is_secret = setting["is_secret"]
                # Mask secret values
                display_value = mask_secret(value) if is_secret else value
            else:
                value = None
                is_secret = category == "api_keys"  # API keys are secret by default
                display_value = None

            result[category][key] = {
                "value": display_value,
                "is_set": value is not None,
                "is_secret": is_secret,
                **meta,
            }

    return result


@router.get("/{category}")
async def get_category_settings(
    category: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Get all settings in a category."""
    if category not in ["api_keys", "scouts", "analyzers"]:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    settings = db.get_settings_by_category(current_user["id"], category)

    # Get schema
    schemas = {
        "api_keys": API_KEY_SETTINGS,
        "scouts": SCOUT_SETTINGS,
        "analyzers": ANALYZER_SETTINGS,
    }
    schema = schemas.get(category, {})

    result = {}
    for key, meta in schema.items():
        setting = settings.get(key)
        if setting:
            value = setting["value"]
            is_secret = setting["is_secret"]
            display_value = mask_secret(value) if is_secret else value
        else:
            value = None
            is_secret = category == "api_keys"
            display_value = None

        result[key] = {
            "value": display_value,
            "is_set": value is not None,
            "is_secret": is_secret,
            **meta,
        }

    return result


@router.put("/{category}/{key}")
async def update_setting(
    category: str,
    key: str,
    update: SettingUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Update a setting value."""
    if category not in ["api_keys", "scouts", "analyzers"]:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    # Validate key exists in schema
    schemas = {
        "api_keys": API_KEY_SETTINGS,
        "scouts": SCOUT_SETTINGS,
        "analyzers": ANALYZER_SETTINGS,
    }
    if key not in schemas.get(category, {}):
        raise HTTPException(status_code=400, detail=f"Invalid setting: {category}/{key}")

    # API keys are always secret
    is_secret = update.is_secret or category == "api_keys"

    db.set_setting(
        user_id=current_user["id"],
        category=category,
        key=key,
        value=update.value,
        is_secret=is_secret,
    )

    meta = get_setting_metadata(category, key)
    display_value = mask_secret(update.value) if is_secret else update.value

    return {
        "success": True,
        "setting": {
            "category": category,
            "key": key,
            "value": display_value,
            "is_set": True,
            "is_secret": is_secret,
            **meta,
        },
    }


@router.delete("/{category}/{key}")
async def delete_setting(
    category: str,
    key: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Delete a setting."""
    deleted = db.delete_setting(current_user["id"], category, key)

    if not deleted:
        raise HTTPException(status_code=404, detail="Setting not found")

    return {"success": True, "message": f"Deleted {category}/{key}"}


@router.post("/test/{category}/{key}")
async def test_setting(
    category: str,
    key: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Test a setting (e.g., validate an API key)."""
    value = db.get_setting(current_user["id"], category, key)

    if not value:
        raise HTTPException(status_code=400, detail="Setting not configured")

    # Test specific integrations
    if category == "api_keys":
        if key == "anthropic":
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=value)
                # Make a minimal API call to verify
                client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}],
                )
                return {"success": True, "message": "Anthropic API key is valid"}
            except anthropic.AuthenticationError:
                return {"success": False, "message": "Invalid API key"}
            except Exception as e:
                return {"success": False, "message": f"Error: {str(e)}"}

        elif key == "openai":
            try:
                import openai
                client = openai.OpenAI(api_key=value)
                client.models.list()
                return {"success": True, "message": "OpenAI API key is valid"}
            except Exception as e:
                return {"success": False, "message": f"Error: {str(e)}"}

    return {"success": True, "message": "Setting is configured"}
