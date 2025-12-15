# pattern_miner/config.py (add these fields)

class Config:
    # Existing fields...

    # A2A Configuration
    agent_url: str = os.getenv("AGENT_URL", "http://localhost:8080")
    port: int = int(os.getenv("PORT", "8080"))

    # Authentication (optional)
    require_auth: bool = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
    auth_token: str = os.getenv("AUTH_TOKEN", "")