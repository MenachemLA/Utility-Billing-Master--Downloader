"""Main agent orchestrator for bill extraction, organization, and upload"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm

from .bill_extractor import BillExtractor
from .file_organizer import FileOrganizer
from .appfolio_uploader import AppFolioUploader
from .logger import setup_logger
from .config import config

logger = setup_logger("BillAgent")


class BillExtractionAgent:
    """Main agent that orchestrates the entire bill extraction and upload process"""

    def __init__(self, headless: bool = True, dry_run: bool = False):
        self.headless = headless
        self.dry_run = dry_run

        self.extractor = BillExtractor(headless=headless)
        self.organizer = FileOrganizer()
        self.uploader = AppFolioUploader()

        self.bills: List[Dict[str, Any]] = []
        self.stats = {
            "extracted": 0,
            "organized": 0,
            "uploaded": 0,
            "failed": 0
        }

    def run(self, skip_extract: bool = False, skip_upload: bool = False) -> Dict[str, Any]:
        """Run the complete bill extraction and upload pipeline"""
        logger.info("="*60)
        logger.info("🚀 STARTING BILL EXTRACTION AGENT")
        logger.info("="*60)

        try:
            # Validate configuration
            config.validate()

            # Step 1: Extract bills from utility providers
            if not skip_extract:
                logger.info("\n📥 STEP 1: Extracting bills from utility providers...")
                self.bills = self.extractor.extract_all_bills()
                self.stats["extracted"] = len(self.bills)

                if not self.bills:
                    logger.warning("No bills were extracted. Check your configuration and credentials.")
                    return self.stats

                logger.info(f"✅ Extracted {len(self.bills)} bills")
            else:
                logger.info("\n⏭️  STEP 1: Skipped (loading existing bills)")
                self.bills = self._load_existing_bills()

            # Step 2: Organize bills by building and month
            logger.info("\n📁 STEP 2: Organizing bills by building and month...")
            self.bills = self.organizer.organize_bills(self.bills)
            self.stats["organized"] = len(self.bills)

            logger.info(f"✅ Organized {len(self.bills)} bills")

            # Print organized structure
            self.organizer.print_structure()

            # Step 3: Upload to AppFolio
            if not skip_upload:
                logger.info("\n☁️  STEP 3: Uploading bills to AppFolio Smart Bill Entry...")

                upload_stats = self.uploader.upload_bills(self.bills, dry_run=self.dry_run)

                self.stats["uploaded"] = upload_stats["success"]
                self.stats["failed"] = upload_stats["failed"]

                logger.info(f"✅ Uploaded {upload_stats['success']} bills")

                if upload_stats["failed"] > 0:
                    logger.warning(f"⚠️  {upload_stats['failed']} bills failed to upload")
            else:
                logger.info("\n⏭️  STEP 3: Skipped upload to AppFolio")

            # Save results
            self._save_results()

            # Print summary
            self._print_summary()

            logger.info("\n" + "="*60)
            logger.info("✨ BILL EXTRACTION AGENT COMPLETED")
            logger.info("="*60 + "\n")

            return self.stats

        except Exception as e:
            logger.error(f"❌ Agent failed: {str(e)}")
            raise

        finally:
            self.uploader.close()

    def _load_existing_bills(self) -> List[Dict[str, Any]]:
        """Load bills from the organized directory structure"""
        bills = []
        base_path = config.download_path

        for building_dir in base_path.iterdir():
            if not building_dir.is_dir() or building_dir.name == "temp":
                continue

            building_id = building_dir.name

            for month_dir in building_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                for pdf_file in month_dir.glob("*.pdf"):
                    # Parse filename: provider_account_date.pdf
                    parts = pdf_file.stem.split('_')
                    if len(parts) >= 3:
                        provider = parts[0]
                        account = parts[1]

                        bills.append({
                            "building_id": building_id,
                            "provider": provider,
                            "account_number": account,
                            "file_path": pdf_file,
                            "organized_path": pdf_file,
                            "downloaded_at": datetime.fromtimestamp(pdf_file.stat().st_mtime)
                        })

        logger.info(f"Loaded {len(bills)} existing bills")
        return bills

    def _save_results(self):
        """Save extraction results to JSON file"""
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"extraction_results_{timestamp}.json"

        # Prepare serializable bill data
        serializable_bills = []
        for bill in self.bills:
            bill_data = bill.copy()

            # Convert Path objects to strings
            if "file_path" in bill_data:
                bill_data["file_path"] = str(bill_data["file_path"])
            if "organized_path" in bill_data:
                bill_data["organized_path"] = str(bill_data["organized_path"])

            # Convert datetime objects to ISO format
            for key in ["downloaded_at", "bill_date", "uploaded_at"]:
                if key in bill_data and isinstance(bill_data[key], datetime):
                    bill_data[key] = bill_data[key].isoformat()

            serializable_bills.append(bill_data)

        results = {
            "timestamp": timestamp,
            "stats": self.stats,
            "bills": serializable_bills
        }

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to: {results_file}")

    def _print_summary(self):
        """Print execution summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 EXECUTION SUMMARY")
        logger.info("="*60)
        logger.info(f"Bills Extracted:  {self.stats['extracted']}")
        logger.info(f"Bills Organized:  {self.stats['organized']}")
        logger.info(f"Bills Uploaded:   {self.stats['uploaded']}")
        logger.info(f"Failed Uploads:   {self.stats['failed']}")
        logger.info("="*60)

    def get_bills(self) -> List[Dict[str, Any]]:
        """Get the list of processed bills"""
        return self.bills

    def get_stats(self) -> Dict[str, int]:
        """Get execution statistics"""
        return self.stats
