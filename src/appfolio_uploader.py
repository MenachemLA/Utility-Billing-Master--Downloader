"""AppFolio Smart Bill Entry integration module"""

import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from .logger import setup_logger
from .config import config

logger = setup_logger("AppFolioUploader")


class AppFolioUploader:
    """Handles uploading bills to AppFolio Smart Bill Entry"""

    def __init__(self):
        self.base_url = config.appfolio_base_url
        self.api_key = config.appfolio_api_key
        self.client_id = config.appfolio_client_id
        self.client_secret = config.appfolio_client_secret
        self.access_token = None

        # HTTP client with timeouts
        self.client = httpx.Client(timeout=30.0)

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def authenticate(self) -> bool:
        """Authenticate with AppFolio API using OAuth2"""
        try:
            # If using API key, no need to authenticate
            if self.api_key and not self.client_id:
                logger.info("Using API key authentication")
                return True

            # OAuth2 authentication
            auth_url = f"{self.base_url}/oauth2/token"

            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            logger.info("Authenticating with AppFolio...")
            response = self.client.post(auth_url, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")

            logger.info("Authentication successful")
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def _get_property_id(self, building_id: str) -> Optional[str]:
        """Get AppFolio property ID for a building"""
        # In production, this would map your building IDs to AppFolio property IDs
        # For now, we'll use the building_id as the property_id
        # You should maintain a mapping in your config.json

        buildings = config.get_buildings()
        building_config = buildings.get(building_id, {})

        # Check if AppFolio property ID is configured
        appfolio_property_id = building_config.get("appfolio_property_id")

        if not appfolio_property_id:
            logger.warning(f"No AppFolio property ID configured for building {building_id}")
            return None

        return appfolio_property_id

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upload_bill(self, bill_info: Dict[str, Any]) -> bool:
        """Upload a single bill to AppFolio Smart Bill Entry"""
        file_path = bill_info.get("organized_path") or bill_info.get("file_path")
        building_id = bill_info["building_id"]
        provider = bill_info["provider"]
        bill_date = bill_info.get("bill_date", datetime.now())

        logger.info(f"Uploading bill: {file_path.name}")

        # Get property ID
        property_id = self._get_property_id(building_id)
        if not property_id:
            logger.error(f"Cannot upload bill without property ID for building {building_id}")
            return False

        try:
            # Prepare bill data
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # AppFolio Smart Bill Entry API endpoint
            upload_url = f"{self.base_url}/v1/bills/smart-entry"

            # Prepare multipart form data
            files = {
                'file': (file_path.name, file_content, 'application/pdf')
            }

            data = {
                'property_id': property_id,
                'vendor_name': provider,
                'bill_date': bill_date.strftime('%Y-%m-%d'),
                'account_number': bill_info.get('account_number', ''),
                'auto_extract': 'true'  # Enable smart extraction
            }

            # Upload
            response = self.client.post(
                upload_url,
                files=files,
                data=data,
                headers=self._get_headers()
            )

            response.raise_for_status()
            result = response.json()

            bill_id = result.get('bill_id')
            logger.info(f"Successfully uploaded bill (ID: {bill_id}): {file_path.name}")

            # Store upload info
            bill_info['appfolio_bill_id'] = bill_id
            bill_info['uploaded_at'] = datetime.now()
            bill_info['upload_status'] = 'success'

            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error uploading bill: {e.response.status_code} - {e.response.text}")
            bill_info['upload_status'] = 'failed'
            bill_info['upload_error'] = str(e)
            return False

        except Exception as e:
            logger.error(f"Failed to upload bill {file_path.name}: {str(e)}")
            bill_info['upload_status'] = 'failed'
            bill_info['upload_error'] = str(e)
            return False

    def upload_bills(self, bills: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """Upload multiple bills to AppFolio"""
        logger.info(f"Uploading {len(bills)} bills to AppFolio (dry_run={dry_run})")

        if dry_run:
            logger.info("DRY RUN MODE - No actual uploads will be performed")
            for bill in bills:
                logger.info(f"Would upload: {bill.get('organized_path', bill.get('file_path'))}")
            return {"total": len(bills), "success": 0, "failed": 0, "skipped": len(bills)}

        # Authenticate first
        if not self.authenticate():
            logger.error("Failed to authenticate with AppFolio")
            return {"total": len(bills), "success": 0, "failed": len(bills), "skipped": 0}

        stats = {"total": len(bills), "success": 0, "failed": 0, "skipped": 0}

        for bill in bills:
            # Skip if already uploaded
            if bill.get('upload_status') == 'success':
                logger.info(f"Skipping already uploaded bill: {bill.get('file_path').name}")
                stats["skipped"] += 1
                continue

            success = self.upload_bill(bill)
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1

        logger.info(f"Upload complete: {stats['success']} successful, {stats['failed']} failed, {stats['skipped']} skipped")
        return stats

    def get_bill_status(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Get the processing status of an uploaded bill"""
        try:
            status_url = f"{self.base_url}/v1/bills/{bill_id}"

            response = self.client.get(status_url, headers=self._get_headers())
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to get bill status: {str(e)}")
            return None

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
