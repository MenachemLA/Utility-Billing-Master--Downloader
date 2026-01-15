"""Bill extraction and download module"""

import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tenacity import retry, stop_after_attempt, wait_exponential

from .logger import setup_logger
from .config import config

logger = setup_logger("BillExtractor")


class BillExtractor:
    """Extracts and downloads utility bills from provider websites"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.download_dir = config.download_path / "temp"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with download preferences"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Set download preferences
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)

        return driver

    def _manual_login(self, login_url: str) -> bool:
        """Open browser and wait for user to manually log in"""
        try:
            logger.info(f"Opening browser to {login_url}")
            self.driver.get(login_url)

            logger.info("="*60)
            logger.info("🔐 MANUAL LOGIN REQUIRED")
            logger.info("="*60)
            logger.info("1. The browser window is now open")
            logger.info("2. Complete ALL login steps:")
            logger.info("   - Click 'Commercial' if prompted")
            logger.info("   - Enter username and password")
            logger.info("   - Solve any CAPTCHA")
            logger.info("   - Complete any additional login steps")
            logger.info("3. Wait until you see your account dashboard")
            logger.info("4. Make sure you're FULLY logged in")
            logger.info("5. Then press ENTER in this terminal to continue...")
            logger.info("")
            logger.info("⚠️  DO NOT press Enter until you're completely logged in!")
            logger.info("="*60)

            # Wait for user to press Enter
            input("Press ENTER after you've logged in: ")

            logger.info("✅ Continuing with bill download...")
            return True

        except Exception as e:
            logger.error(f"Manual login failed: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _login(self, provider_config: Dict[str, Any], credentials: Dict[str, str], manual_mode: bool = False) -> bool:
        """Log in to utility provider website"""
        try:
            login_url = provider_config.get("login_url")

            # Use manual login for LADWP or if manual_mode is True
            if manual_mode or provider_config.get("provider") == "ladwp":
                return self._manual_login(login_url)

            selectors = provider_config.get("selectors", {})

            logger.info(f"Logging in to {login_url}")
            self.driver.get(login_url)

            # Wait for login form
            wait = WebDriverWait(self.driver, 10)

            # Enter username
            username_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors["username_field"]))
            )
            username_field.send_keys(credentials["username"])

            # Enter password
            password_field = self.driver.find_element(By.CSS_SELECTOR, selectors["password_field"])
            password_field.send_keys(credentials["password"])

            # Click login
            login_button = self.driver.find_element(By.CSS_SELECTOR, selectors["login_button"])
            login_button.click()

            # Wait for login to complete
            time.sleep(3)

            logger.info("Login successful")
            return True

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def _navigate_to_bills(self, selectors: Dict[str, str]) -> bool:
        """Navigate to bills/billing history page"""
        try:
            wait = WebDriverWait(self.driver, 10)
            bills_link = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selectors["bills_link"]))
            )
            bills_link.click()
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to bills: {str(e)}")
            return False

    def _get_current_billing_period_dates(self) -> List[datetime]:
        """Get list of dates for current billing periods"""
        today = datetime.now()
        dates = []

        for i in range(config.current_billing_period_months):
            date = today - relativedelta(months=i)
            dates.append(date)

        return dates

    def _download_bills(self, selectors: Dict[str, str], billing_dates: List[datetime]) -> List[Path]:
        """Download bills for specified billing periods"""
        downloaded_files = []

        try:
            # Find all download buttons/links
            download_elements = self.driver.find_elements(By.CSS_SELECTOR, selectors["download_button"])

            logger.info(f"Found {len(download_elements)} potential bills to download")

            # Track files before download
            existing_files = set(self.download_dir.glob("*.pdf"))

            for element in download_elements:
                try:
                    # Click download
                    element.click()
                    time.sleep(2)  # Wait for download to start

                    # Wait for new file to appear
                    max_wait = 30
                    start_time = time.time()

                    while time.time() - start_time < max_wait:
                        current_files = set(self.download_dir.glob("*.pdf"))
                        new_files = current_files - existing_files

                        if new_files:
                            new_file = list(new_files)[0]
                            downloaded_files.append(new_file)
                            existing_files = current_files
                            logger.info(f"Downloaded: {new_file.name}")
                            break

                        time.sleep(1)

                except Exception as e:
                    logger.warning(f"Failed to download bill: {str(e)}")
                    continue

            logger.info(f"Successfully downloaded {len(downloaded_files)} bills")
            return downloaded_files

        except Exception as e:
            logger.error(f"Error during bill download: {str(e)}")
            return downloaded_files

    def extract_bills(self, building_id: str, utility_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract bills for a specific building and utility"""
        provider_id = utility_config["provider"]
        account_number = utility_config["account_number"]

        logger.info(f"Extracting bills for building {building_id}, provider {provider_id}, account {account_number}")

        # Get provider configuration
        providers = config.get_providers()
        provider_config = providers.get(provider_id)

        if not provider_config:
            logger.error(f"Provider {provider_id} not found in configuration")
            return []

        # Get credentials
        credentials = config.get_provider_credentials(provider_id)

        if not credentials["username"] or not credentials["password"]:
            logger.error(f"Missing credentials for provider {provider_id}")
            return []

        # Merge utility config with provider config
        full_config = {**provider_config, **utility_config}

        try:
            # Set up driver
            self.driver = self._setup_driver()

            # Login
            self._login(full_config, credentials)

            # Navigate to bills
            self._navigate_to_bills(provider_config["selectors"])

            # Get billing dates
            billing_dates = self._get_current_billing_period_dates()

            # Download bills
            downloaded_files = self._download_bills(provider_config["selectors"], billing_dates)

            # Create bill records
            bills = []
            for file_path in downloaded_files:
                bills.append({
                    "building_id": building_id,
                    "provider": provider_id,
                    "account_number": account_number,
                    "file_path": file_path,
                    "downloaded_at": datetime.now()
                })

            return bills

        except Exception as e:
            logger.error(f"Failed to extract bills: {str(e)}")
            return []

        finally:
            if self.driver:
                self.driver.quit()

    def extract_all_bills(self) -> List[Dict[str, Any]]:
        """Extract bills for all buildings and utilities"""
        all_bills = []
        buildings = config.get_buildings()

        for building_id, building_config in buildings.items():
            logger.info(f"Processing building: {building_config['name']}")

            for utility in building_config.get("utilities", []):
                bills = self.extract_bills(building_id, utility)
                all_bills.extend(bills)

        logger.info(f"Extracted {len(all_bills)} bills total")
        return all_bills
