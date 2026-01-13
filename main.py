#!/usr/bin/env python3
"""
Utility Billing Master Downloader
Main entry point for the bill extraction agent
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import BillExtractionAgent
from src.logger import setup_logger
from src.config import config

logger = setup_logger("Main")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Extract utility bills, organize them, and upload to AppFolio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the complete pipeline
  python main.py

  # Run in dry-run mode (no uploads)
  python main.py --dry-run

  # Run with visible browser
  python main.py --no-headless

  # Skip extraction and only upload existing bills
  python main.py --skip-extract

  # Extract and organize only (no upload)
  python main.py --skip-upload

  # Organize and upload existing bills
  python main.py --skip-extract --upload
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual uploads)"
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (not headless)"
    )

    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip bill extraction, use existing downloaded bills"
    )

    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip upload to AppFolio"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    try:
        # Initialize agent
        agent = BillExtractionAgent(
            headless=not args.no_headless,
            dry_run=args.dry_run
        )

        # Run agent
        stats = agent.run(
            skip_extract=args.skip_extract,
            skip_upload=args.skip_upload
        )

        # Exit with appropriate code
        if stats.get("failed", 0) > 0:
            logger.warning("Some operations failed. Check logs for details.")
            sys.exit(1)
        else:
            logger.info("All operations completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Operation cancelled by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"\n\n❌ Fatal error: {str(e)}")
        sys.exit(1)


def print_banner():
    """Print application banner"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Utility Billing Master Downloader Agent            ║
║                                                            ║
║  Extract → Organize → Upload to AppFolio                   ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)


if __name__ == "__main__":
    main()
