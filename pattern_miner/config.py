# pattern_miner/config.py
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration for Pattern Miner service"""

    # Required configuration
    anthropic_api_key: str
    github_token: str

    # A2A Configuration
    agent_url: str
    port: int

    # Optional configuration
    dev_nexus_url: Optional[str] = None
    webhook_url: Optional[str] = None

    # Authentication (optional)
    require_auth: bool = False
    auth_token: Optional[str] = None

    # GCP Configuration (for deployment)
    gcp_project_id: Optional[str] = None
    gcp_region: str = "us-central1"

    # Database Configuration (shared with dev-nexus)
    database_url: Optional[str] = None
    db_host: Optional[str] = None
    db_port: int = 5432
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    use_database: bool = False


def load_config() -> Config:
    """Load configuration from environment variables"""

    # Required variables
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    # A2A configuration
    agent_url = os.getenv("AGENT_URL", "http://localhost:8080")
    port = int(os.getenv("PORT", "8080"))

    # Optional configuration
    dev_nexus_url = os.getenv("DEV_NEXUS_URL")
    webhook_url = os.getenv("WEBHOOK_URL")

    # Authentication
    require_auth = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
    auth_token = os.getenv("AUTH_TOKEN")

    # GCP configuration
    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    gcp_region = os.getenv("GCP_REGION", "us-central1")

    # Database configuration (shared with dev-nexus)
    database_url = os.getenv("DATABASE_URL")
    db_host = os.getenv("DB_HOST")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "devnexus")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    use_database = os.getenv("USE_DATABASE", "false").lower() == "true"

    return Config(
        anthropic_api_key=anthropic_api_key,
        github_token=github_token,
        agent_url=agent_url,
        port=port,
        dev_nexus_url=dev_nexus_url,
        webhook_url=webhook_url,
        require_auth=require_auth,
        auth_token=auth_token,
        gcp_project_id=gcp_project_id,
        gcp_region=gcp_region,
        database_url=database_url,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        use_database=use_database
    )
