"""
Settings Router

Endpoints for managing user settings and API credentials.
"""

from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.database import Database
from web.api.deps import get_current_user, get_db

router = APIRouter()


# Service groups for the new grouped architecture
SERVICE_GROUPS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "description": "AI analysis API",
        "fields": [
            {
                "key": "api_key",
                "label": "API Key",
                "placeholder": "sk-ant-...",
                "required": True,
            },
        ],
    },
    "openai": {
        "name": "OpenAI",
        "description": "Alternative AI API (optional)",
        "fields": [
            {
                "key": "api_key",
                "label": "API Key",
                "placeholder": "sk-...",
                "required": True,
            },
        ],
    },
    "reddit": {
        "name": "Reddit",
        "description": "OAuth credentials for Reddit scout",
        "fields": [
            {
                "key": "client_id",
                "label": "Client ID",
                "placeholder": "Client ID",
                "required": True,
            },
            {
                "key": "client_secret",
                "label": "Client Secret",
                "placeholder": "Client Secret",
                "required": True,
            },
            {
                "key": "username",
                "label": "Username",
                "placeholder": "username",
                "required": True,
            },
            {
                "key": "password",
                "label": "Password",
                "placeholder": "password",
                "required": True,
            },
        ],
    },
    "twitter": {
        "name": "Twitter/X",
        "description": "Bearer token for Twitter scout",
        "fields": [
            {
                "key": "bearer_token",
                "label": "Bearer Token",
                "placeholder": "Bearer token",
                "required": True,
            },
        ],
    },
    "producthunt": {
        "name": "Product Hunt",
        "description": "OAuth credentials for Product Hunt scout",
        "fields": [
            {
                "key": "api_key",
                "label": "API Key",
                "placeholder": "Client ID",
                "required": True,
            },
            {
                "key": "api_secret",
                "label": "API Secret",
                "placeholder": "Client Secret",
                "required": True,
            },
        ],
    },
    "websearch": {
        "name": "Web Search",
        "description": "Search API (SerpAPI or Google Custom Search)",
        "has_provider_choice": True,
        "providers": {
            "serpapi": {
                "name": "SerpAPI",
                "fields": [
                    {
                        "key": "api_key",
                        "label": "API Key",
                        "placeholder": "SerpAPI key",
                        "required": True,
                    },
                ],
            },
            "google": {
                "name": "Google Custom Search",
                "fields": [
                    {
                        "key": "api_key",
                        "label": "API Key",
                        "placeholder": "Google API key",
                        "required": True,
                    },
                    {
                        "key": "cx",
                        "label": "Search Engine ID",
                        "placeholder": "Custom Search Engine ID",
                        "required": True,
                    },
                ],
            },
        },
    },
}

# Predefined setting schemas for validation and documentation
# (Legacy format for backwards compatibility)
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
    "producthunt_api_key": {
        "label": "Product Hunt API Key",
        "description": "OAuth client ID for Product Hunt API access",
        "placeholder": "Client ID",
    },
    "producthunt_api_secret": {
        "label": "Product Hunt API Secret",
        "description": "OAuth client secret for Product Hunt API",
        "placeholder": "Client Secret",
    },
    "twitter_bearer_token": {
        "label": "Twitter Bearer Token",
        "description": "Bearer token for Twitter API access",
        "placeholder": "Bearer token",
    },
    "websearch_provider": {
        "label": "Web Search Provider",
        "description": "Search provider (serpapi or google)",
        "placeholder": "serpapi",
    },
    "websearch_serpapi_api_key": {
        "label": "SerpAPI Key",
        "description": "API key for SerpAPI",
        "placeholder": "SerpAPI key",
    },
    "websearch_google_api_key": {
        "label": "Google API Key",
        "description": "API key for Google Custom Search",
        "placeholder": "Google API key",
    },
    "websearch_google_cx": {
        "label": "Google Search Engine ID",
        "description": "Custom Search Engine ID (cx)",
        "placeholder": "Search Engine ID",
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

        elif key in ("producthunt_api_key", "producthunt_api_secret"):
            # Test Product Hunt credentials (need both key and secret)
            api_key = db.get_setting(current_user["id"], "api_keys", "producthunt_api_key")
            api_secret = db.get_setting(current_user["id"], "api_keys", "producthunt_api_secret")

            if not api_key or not api_secret:
                return {
                    "success": False,
                    "message": "Both API Key and API Secret must be configured to test"
                }

            try:
                import requests
                response = requests.post(
                    "https://api.producthunt.com/v2/oauth/token",
                    json={
                        "client_id": api_key,
                        "client_secret": api_secret,
                        "grant_type": "client_credentials",
                    },
                    timeout=10,
                )
                if response.status_code == 200 and response.json().get("access_token"):
                    return {"success": True, "message": "Product Hunt credentials are valid"}
                else:
                    error = response.json().get("error", "Unknown error")
                    return {"success": False, "message": f"Invalid credentials: {error}"}
            except Exception as e:
                return {"success": False, "message": f"Error: {str(e)}"}

    return {"success": True, "message": "Setting is configured"}


def _get_service_setting_key(service_id: str, field_key: str,
                             provider_id: Optional[str] = None) -> str:
    """Convert service field to setting key."""
    if service_id == "anthropic":
        return "anthropic" if field_key == "api_key" else f"anthropic_{field_key}"
    elif service_id == "openai":
        return "openai" if field_key == "api_key" else f"openai_{field_key}"
    elif service_id == "reddit":
        return f"reddit_{field_key}"
    elif service_id == "twitter":
        return f"twitter_{field_key}"
    elif service_id == "producthunt":
        return f"producthunt_{field_key}"
    elif service_id == "websearch":
        if provider_id:
            return f"websearch_{provider_id}_{field_key}"
        return f"websearch_{field_key}"
    return f"{service_id}_{field_key}"


def _build_service_field(field_def: dict, value: Optional[str],
                         is_set: bool) -> dict:
    """Build a service field response."""
    return {
        "key": field_def["key"],
        "label": field_def["label"],
        "placeholder": field_def.get("placeholder", ""),
        "required": field_def.get("required", False),
        "is_set": is_set,
        "value": mask_secret(value) if is_set and value else None,
    }


@router.get("/services")
async def get_services(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Get all services with their configuration status."""
    user_id = current_user["id"]
    services = []

    for service_id, service_def in SERVICE_GROUPS.items():
        service = {
            "id": service_id,
            "name": service_def["name"],
            "description": service_def["description"],
        }

        if service_def.get("has_provider_choice"):
            # Handle provider-based services (like websearch)
            service["has_provider_choice"] = True
            selected_provider = db.get_setting(
                user_id, "api_keys", "websearch_provider"
            ) or "serpapi"
            service["selected_provider"] = selected_provider

            providers = []
            for provider_id, provider_def in service_def["providers"].items():
                provider_fields = []
                provider_configured = True

                for field_def in provider_def["fields"]:
                    setting_key = _get_service_setting_key(
                        service_id, field_def["key"], provider_id
                    )
                    value = db.get_setting(user_id, "api_keys", setting_key)
                    is_set = value is not None

                    if field_def.get("required") and not is_set:
                        provider_configured = False

                    provider_fields.append(
                        _build_service_field(field_def, value, is_set)
                    )

                providers.append({
                    "id": provider_id,
                    "name": provider_def["name"],
                    "fields": provider_fields,
                    "is_configured": provider_configured,
                })

            service["providers"] = providers
            # Service is configured if the selected provider is configured
            selected = next(
                (p for p in providers if p["id"] == selected_provider), None
            )
            service["is_configured"] = selected["is_configured"] if selected else False
        else:
            # Handle simple services
            fields = []
            is_configured = True

            for field_def in service_def.get("fields", []):
                setting_key = _get_service_setting_key(service_id, field_def["key"])
                value = db.get_setting(user_id, "api_keys", setting_key)
                is_set = value is not None

                if field_def.get("required") and not is_set:
                    is_configured = False

                fields.append(_build_service_field(field_def, value, is_set))

            service["fields"] = fields
            service["is_configured"] = is_configured

        services.append(service)

    return {"services": services}


@router.put("/services/{service_id}/field")
async def update_service_field(
    service_id: str,
    field_key: str,
    value: str,
    provider_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Update a service field value."""
    if service_id not in SERVICE_GROUPS:
        raise HTTPException(status_code=400, detail=f"Invalid service: {service_id}")

    setting_key = _get_service_setting_key(service_id, field_key, provider_id)

    db.set_setting(
        user_id=current_user["id"],
        category="api_keys",
        key=setting_key,
        value=value,
        is_secret=True,
    )

    return {"success": True, "key": setting_key}


@router.put("/services/{service_id}/provider")
async def set_service_provider(
    service_id: str,
    provider_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Set the active provider for a service."""
    if service_id not in SERVICE_GROUPS:
        raise HTTPException(status_code=400, detail=f"Invalid service: {service_id}")

    service_def = SERVICE_GROUPS[service_id]
    if not service_def.get("has_provider_choice"):
        raise HTTPException(
            status_code=400, detail=f"Service {service_id} does not have providers"
        )

    if provider_id not in service_def["providers"]:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider_id}")

    db.set_setting(
        user_id=current_user["id"],
        category="api_keys",
        key=f"{service_id}_provider",
        value=provider_id,
        is_secret=False,
    )

    return {"success": True, "provider": provider_id}


async def _test_anthropic(api_key: str) -> dict:
    """Test Anthropic API key."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
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


async def _test_openai(api_key: str) -> dict:
    """Test OpenAI API key."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        client.models.list()
        return {"success": True, "message": "OpenAI API key is valid"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


async def _test_reddit(client_id: str, client_secret: str,
                       username: str, password: str) -> dict:
    """Test Reddit OAuth credentials."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(client_id, client_secret),
                data={
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                },
                headers={"User-Agent": "Glean/1.0"},
                timeout=10,
            )
            if response.status_code == 200 and response.json().get("access_token"):
                return {"success": True, "message": "Reddit credentials are valid"}
            else:
                error = response.json().get("error", "Unknown error")
                return {"success": False, "message": f"Invalid credentials: {error}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


async def _test_twitter(bearer_token: str) -> dict:
    """Test Twitter bearer token."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "message": "Twitter bearer token is valid"}
            elif response.status_code == 401:
                return {"success": False, "message": "Invalid bearer token"}
            else:
                return {
                    "success": False,
                    "message": f"Twitter API error: {response.status_code}"
                }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


async def _test_producthunt(api_key: str, api_secret: str) -> dict:
    """Test Product Hunt OAuth credentials."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.producthunt.com/v2/oauth/token",
                json={
                    "client_id": api_key,
                    "client_secret": api_secret,
                    "grant_type": "client_credentials",
                },
                timeout=10,
            )
            if response.status_code == 200 and response.json().get("access_token"):
                return {"success": True, "message": "Product Hunt credentials are valid"}
            else:
                error = response.json().get("error", "Unknown error")
                return {"success": False, "message": f"Invalid credentials: {error}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


async def _test_serpapi(api_key: str) -> dict:
    """Test SerpAPI key."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://serpapi.com/account",
                params={"api_key": api_key},
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "message": "SerpAPI key is valid"}
            else:
                return {"success": False, "message": "Invalid SerpAPI key"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


async def _test_google_cse(api_key: str, cx: str) -> dict:
    """Test Google Custom Search credentials."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": cx,
                    "q": "test",
                    "num": 1,
                },
                timeout=10,
            )
            if response.status_code == 200:
                return {"success": True, "message": "Google CSE credentials are valid"}
            elif response.status_code == 400:
                error = response.json().get("error", {}).get("message", "Invalid request")
                return {"success": False, "message": f"Invalid credentials: {error}"}
            elif response.status_code == 403:
                return {"success": False, "message": "API key invalid or quota exceeded"}
            else:
                return {
                    "success": False,
                    "message": f"Google API error: {response.status_code}"
                }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@router.post("/test-service/{service_id}")
async def test_service(
    service_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Test all credentials for a service."""
    if service_id not in SERVICE_GROUPS:
        raise HTTPException(status_code=400, detail=f"Invalid service: {service_id}")

    user_id = current_user["id"]

    if service_id == "anthropic":
        api_key = db.get_setting(user_id, "api_keys", "anthropic")
        if not api_key:
            return {"success": False, "message": "API key not configured"}
        return await _test_anthropic(api_key)

    elif service_id == "openai":
        api_key = db.get_setting(user_id, "api_keys", "openai")
        if not api_key:
            return {"success": False, "message": "API key not configured"}
        return await _test_openai(api_key)

    elif service_id == "reddit":
        client_id = db.get_setting(user_id, "api_keys", "reddit_client_id")
        client_secret = db.get_setting(user_id, "api_keys", "reddit_client_secret")
        username = db.get_setting(user_id, "api_keys", "reddit_username")
        password = db.get_setting(user_id, "api_keys", "reddit_password")

        if not all([client_id, client_secret, username, password]):
            return {"success": False, "message": "All Reddit credentials must be configured"}
        return await _test_reddit(client_id, client_secret, username, password)

    elif service_id == "twitter":
        bearer_token = db.get_setting(user_id, "api_keys", "twitter_bearer_token")
        if not bearer_token:
            return {"success": False, "message": "Bearer token not configured"}
        return await _test_twitter(bearer_token)

    elif service_id == "producthunt":
        api_key = db.get_setting(user_id, "api_keys", "producthunt_api_key")
        api_secret = db.get_setting(user_id, "api_keys", "producthunt_api_secret")

        if not api_key or not api_secret:
            return {"success": False, "message": "Both API key and secret must be configured"}
        return await _test_producthunt(api_key, api_secret)

    elif service_id == "websearch":
        provider = db.get_setting(user_id, "api_keys", "websearch_provider") or "serpapi"

        if provider == "serpapi":
            api_key = db.get_setting(user_id, "api_keys", "websearch_serpapi_api_key")
            if not api_key:
                return {"success": False, "message": "SerpAPI key not configured"}
            return await _test_serpapi(api_key)

        elif provider == "google":
            api_key = db.get_setting(user_id, "api_keys", "websearch_google_api_key")
            cx = db.get_setting(user_id, "api_keys", "websearch_google_cx")
            if not api_key or not cx:
                return {
                    "success": False,
                    "message": "Both Google API key and Search Engine ID must be configured"
                }
            return await _test_google_cse(api_key, cx)

        else:
            return {"success": False, "message": f"Unknown provider: {provider}"}

    return {"success": True, "message": "Service configured"}
