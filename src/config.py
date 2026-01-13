"""Configuration management for the bill extraction agent"""

import os
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Central configuration manager"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config_data = self._load_config()

        # Environment variables
        self.appfolio_api_key = os.getenv("APPFOLIO_API_KEY")
        self.appfolio_client_id = os.getenv("APPFOLIO_CLIENT_ID")
        self.appfolio_client_secret = os.getenv("APPFOLIO_CLIENT_SECRET")
        self.appfolio_base_url = os.getenv("APPFOLIO_BASE_URL", "https://api.appfolio.com")

        self.download_path = Path(os.getenv("DOWNLOAD_PATH", "./downloaded_bills"))
        self.current_billing_period_months = int(os.getenv("CURRENT_BILLING_PERIOD_MONTHS", "3"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Create download directory if it doesn't exist
        self.download_path.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            return {"buildings": {}, "providers": {}}

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get_buildings(self) -> Dict[str, Any]:
        """Get all buildings configuration"""
        return self.config_data.get("buildings", {})

    def get_providers(self) -> Dict[str, Any]:
        """Get all provider configurations"""
        return self.config_data.get("providers", {})

    def get_provider_credentials(self, provider: str) -> Dict[str, str]:
        """Get credentials for a specific provider from environment"""
        username_key = f"{provider.upper()}_USERNAME"
        password_key = f"{provider.upper()}_PASSWORD"

        return {
            "username": os.getenv(username_key),
            "password": os.getenv(password_key)
        }

    def validate(self) -> bool:
        """Validate configuration"""
        if not self.appfolio_api_key:
            raise ValueError("APPFOLIO_API_KEY not set in environment")

        if not self.config_data.get("buildings"):
            raise ValueError("No buildings configured in config.json")

        return True


# Global config instance
config = Config()
