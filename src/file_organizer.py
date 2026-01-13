"""File organization module - organize bills by building and month"""

import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import PyPDF2

from .logger import setup_logger
from .config import config

logger = setup_logger("FileOrganizer")


class FileOrganizer:
    """Organizes downloaded bills by building and month"""

    def __init__(self):
        self.base_path = config.download_path

    def _extract_date_from_pdf(self, pdf_path: Path) -> Optional[datetime]:
        """Extract date from PDF content"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # Extract text from first few pages
                text = ""
                for page_num in range(min(3, len(pdf_reader.pages))):
                    text += pdf_reader.pages[page_num].extract_text()

                # Look for common date patterns
                date_patterns = [
                    r'Bill Date[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
                    r'Date[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
                    r'Statement Date[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
                    r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
                    r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',  # "January 15, 2024"
                ]

                for pattern in date_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        date_str = match.group(1)
                        # Try to parse the date
                        for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y', '%B %d, %Y', '%b %d, %Y']:
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                continue

                # If no date found in content, try PDF metadata
                if pdf_reader.metadata:
                    creation_date = pdf_reader.metadata.get('/CreationDate')
                    if creation_date:
                        # PDF dates are in format: D:YYYYMMDDHHmmSS
                        date_match = re.match(r'D:(\d{4})(\d{2})(\d{2})', creation_date)
                        if date_match:
                            year, month, day = date_match.groups()
                            return datetime(int(year), int(month), int(day))

        except Exception as e:
            logger.warning(f"Failed to extract date from {pdf_path.name}: {str(e)}")

        return None

    def _get_month_year_string(self, date: datetime) -> str:
        """Format date as YYYY-MM for folder naming"""
        return date.strftime("%Y-%m")

    def _create_organized_path(self, building_id: str, date: datetime, provider: str, account_number: str) -> Path:
        """Create organized file path: building_id/YYYY-MM/provider_account.pdf"""
        building_config = config.get_buildings().get(building_id, {})
        building_name = building_config.get("name", building_id)

        # Sanitize building name for filesystem
        safe_building_name = re.sub(r'[^\w\s-]', '', building_name).strip().replace(' ', '_')

        # Create path structure
        month_year = self._get_month_year_string(date)
        organized_path = self.base_path / safe_building_name / month_year

        # Create directory
        organized_path.mkdir(parents=True, exist_ok=True)

        # Create filename
        filename = f"{provider}_{account_number}_{date.strftime('%Y%m%d')}.pdf"

        return organized_path / filename

    def organize_bill(self, bill_info: Dict[str, Any]) -> Optional[Path]:
        """Organize a single bill file"""
        source_path = bill_info["file_path"]
        building_id = bill_info["building_id"]
        provider = bill_info["provider"]
        account_number = bill_info["account_number"]

        logger.info(f"Organizing bill: {source_path.name}")

        # Extract date from PDF
        bill_date = self._extract_date_from_pdf(source_path)

        if not bill_date:
            # Fallback to current date
            logger.warning(f"Could not extract date from {source_path.name}, using current date")
            bill_date = datetime.now()

        # Create organized path
        dest_path = self._create_organized_path(building_id, bill_date, provider, account_number)

        try:
            # Copy file to organized location
            shutil.copy2(source_path, dest_path)
            logger.info(f"Organized to: {dest_path}")

            # Update bill info with new path and date
            bill_info["organized_path"] = dest_path
            bill_info["bill_date"] = bill_date

            return dest_path

        except Exception as e:
            logger.error(f"Failed to organize {source_path.name}: {str(e)}")
            return None

    def organize_bills(self, bills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Organize all downloaded bills"""
        logger.info(f"Organizing {len(bills)} bills")

        organized_bills = []
        for bill in bills:
            organized_path = self.organize_bill(bill)
            if organized_path:
                organized_bills.append(bill)

        logger.info(f"Successfully organized {len(organized_bills)} bills")
        return organized_bills

    def get_organized_structure(self) -> Dict[str, Any]:
        """Get the current organized file structure"""
        structure = {}

        for building_dir in self.base_path.iterdir():
            if not building_dir.is_dir() or building_dir.name == "temp":
                continue

            structure[building_dir.name] = {}

            for month_dir in building_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                bills = list(month_dir.glob("*.pdf"))
                structure[building_dir.name][month_dir.name] = [bill.name for bill in bills]

        return structure

    def print_structure(self):
        """Print the organized file structure"""
        structure = self.get_organized_structure()

        logger.info("\n" + "="*50)
        logger.info("ORGANIZED BILL STRUCTURE")
        logger.info("="*50)

        for building, months in structure.items():
            logger.info(f"\n📁 {building}")
            for month, bills in months.items():
                logger.info(f"  📅 {month}")
                for bill in bills:
                    logger.info(f"    📄 {bill}")

        logger.info("\n" + "="*50)
