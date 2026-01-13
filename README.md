# Utility Billing Master Downloader

An intelligent agent that automatically extracts utility bills from current billing periods, downloads them to your computer, organizes them by building and month, and uploads them to AppFolio's Smart Bill Entry system.

## 🚀 Features

- **Automated Bill Extraction**: Automatically logs into utility provider websites and downloads bills
- **Smart Organization**: Organizes bills by building and month (`Building/YYYY-MM/provider_account_date.pdf`)
- **AppFolio Integration**: Seamlessly uploads bills to AppFolio's Smart Bill Entry with automatic data extraction
- **Multi-Building Support**: Handle multiple buildings with different utility accounts
- **Flexible Configuration**: Easy-to-configure JSON format for buildings and utility providers
- **Robust Error Handling**: Automatic retries and comprehensive logging
- **Date Extraction**: Automatically extracts bill dates from PDF content and metadata

## 📋 Prerequisites

- Python 3.8 or higher
- Chrome/Chromium browser (for Selenium)
- AppFolio account with API access
- Utility provider account credentials

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/MenachemLA/Utility-Billing-Master--Downloader.git
   cd Utility-Billing-Master--Downloader
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Configure buildings and providers**
   Edit `config.json` to add your buildings and utility provider details.

## ⚙️ Configuration

### Environment Variables (.env)

```env
# AppFolio Credentials
APPFOLIO_API_KEY=your_appfolio_api_key
APPFOLIO_CLIENT_ID=your_client_id
APPFOLIO_CLIENT_SECRET=your_client_secret
APPFOLIO_BASE_URL=https://api.appfolio.com

# Utility Provider Credentials (add for each provider)
ELECTRIC_COMPANY_USERNAME=your_username
ELECTRIC_COMPANY_PASSWORD=your_password
GAS_COMPANY_USERNAME=your_username
GAS_COMPANY_PASSWORD=your_password
WATER_COMPANY_USERNAME=your_username
WATER_COMPANY_PASSWORD=your_password

# Download Settings
DOWNLOAD_PATH=./downloaded_bills
CURRENT_BILLING_PERIOD_MONTHS=3
LOG_LEVEL=INFO
```

### Buildings Configuration (config.json)

```json
{
  "buildings": {
    "building_1": {
      "name": "Main Street Apartments",
      "address": "123 Main St",
      "appfolio_property_id": "prop_12345",
      "utilities": [
        {
          "provider": "electric_company",
          "account_number": "ACCOUNT_123",
          "login_url": "https://www.electriccompany.com/login"
        }
      ]
    }
  },
  "providers": {
    "electric_company": {
      "name": "Electric Company",
      "type": "selenium",
      "selectors": {
        "username_field": "#username",
        "password_field": "#password",
        "login_button": "#login-btn",
        "bills_link": "a[href*='bills']",
        "download_button": ".download-pdf"
      }
    }
  }
}
```

## 🎯 Usage

### Basic Usage

Run the complete pipeline (extract, organize, upload):

```bash
python main.py
```

### Command Line Options

```bash
# Dry run mode (no actual uploads)
python main.py --dry-run

# Run with visible browser (for debugging)
python main.py --no-headless

# Skip extraction, use existing downloaded bills
python main.py --skip-extract

# Extract and organize only (no upload)
python main.py --skip-upload

# Organize and upload existing bills only
python main.py --skip-extract
```

### Help

```bash
python main.py --help
```

## 📁 Output Structure

Bills are organized in the following structure:

```
downloaded_bills/
├── Main_Street_Apartments/
│   ├── 2024-01/
│   │   ├── electric_company_ACCOUNT_123_20240115.pdf
│   │   ├── gas_company_GAS_456_20240110.pdf
│   │   └── water_company_WATER_789_20240105.pdf
│   ├── 2024-02/
│   │   ├── electric_company_ACCOUNT_123_20240215.pdf
│   │   └── gas_company_GAS_456_20240210.pdf
│   └── 2024-03/
│       └── electric_company_ACCOUNT_123_20240315.pdf
└── Oak_Avenue_Complex/
    └── 2024-01/
        └── electric_company_ACCOUNT_321_20240120.pdf
```

## 📊 Results

Execution results are saved in the `results/` directory with timestamps:

```
results/
└── extraction_results_20240315_143022.json
```

## 🔍 Logging

Logs are saved in the `logs/` directory:

```
logs/
└── bill_extractor.log
```

Console output includes color-coded log levels for easy debugging.

## 🏗️ Architecture

The agent is composed of several modules:

- **`src/config.py`**: Configuration management
- **`src/logger.py`**: Logging setup
- **`src/bill_extractor.py`**: Web scraping and bill download using Selenium
- **`src/file_organizer.py`**: File organization by building and month
- **`src/appfolio_uploader.py`**: AppFolio API integration
- **`src/agent.py`**: Main orchestrator that coordinates all components
- **`main.py`**: CLI entry point

## 🔐 Security

- Never commit `.env` file or credentials to version control
- API keys and passwords are loaded from environment variables
- Use AppFolio's OAuth2 authentication for secure API access
- All credentials should be stored securely

## 🛠️ Customization

### Adding New Utility Providers

1. Add provider credentials to `.env`:
   ```env
   NEW_PROVIDER_USERNAME=username
   NEW_PROVIDER_PASSWORD=password
   ```

2. Add provider configuration to `config.json`:
   ```json
   "providers": {
     "new_provider": {
       "name": "New Provider",
       "type": "selenium",
       "selectors": {
         "username_field": "#user",
         "password_field": "#pass",
         "login_button": "#login",
         "bills_link": "a.bills",
         "download_button": ".download"
       }
     }
   }
   ```

3. Add utility to building configuration:
   ```json
   "utilities": [
     {
       "provider": "new_provider",
       "account_number": "ACCOUNT_XXX",
       "login_url": "https://www.newprovider.com/login"
     }
   ]
   ```

## 🐛 Troubleshooting

### Common Issues

1. **Chrome Driver Issues**
   - The agent automatically downloads the correct ChromeDriver version
   - If issues persist, ensure Chrome is installed and up to date

2. **Login Failures**
   - Verify credentials in `.env`
   - Run with `--no-headless` to see what's happening
   - Check if provider website has changed selectors

3. **Upload Failures**
   - Verify AppFolio API credentials
   - Check that `appfolio_property_id` is set in building config
   - Review logs for specific error messages

4. **Date Extraction Issues**
   - The agent tries multiple date formats
   - If dates are incorrect, they default to current date
   - You can manually adjust filenames after organization

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions, please open an issue on GitHub.
