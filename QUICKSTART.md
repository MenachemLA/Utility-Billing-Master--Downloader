# Quick Start Guide

Get started with the Utility Billing Master Downloader in 5 minutes!

## 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## 2. Set Up Credentials

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your credentials
nano .env  # or use your preferred editor
```

**Required credentials:**
- AppFolio API key
- Utility provider usernames and passwords

## 3. Configure Your Buildings

Edit `config.json` and add your buildings:

```json
{
  "buildings": {
    "my_building": {
      "name": "My Apartment Building",
      "address": "123 Main St",
      "appfolio_property_id": "prop_12345",
      "utilities": [
        {
          "provider": "electric_company",
          "account_number": "YOUR_ACCOUNT",
          "login_url": "https://www.utilitycompany.com/login"
        }
      ]
    }
  }
}
```

## 4. Configure Provider Selectors

For each utility provider, add CSS selectors to `config.json`:

```json
{
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

**Finding CSS Selectors:**
1. Open the utility provider website
2. Right-click on the element (username field, button, etc.)
3. Select "Inspect Element"
4. Copy the CSS selector

## 5. Test Run (Dry Run)

Test without actually uploading:

```bash
python main.py --dry-run --no-headless
```

This will:
- Show the browser so you can see what's happening
- Extract and organize bills
- NOT upload to AppFolio

## 6. Full Run

Once everything works:

```bash
python main.py
```

This will:
- Extract bills from utility providers
- Organize by building and month
- Upload to AppFolio Smart Bill Entry

## 📊 Check Results

After running:

1. **Downloaded bills**: Check `downloaded_bills/` directory
2. **Logs**: Check `logs/bill_extractor.log`
3. **Results**: Check `results/extraction_results_*.json`

## 🔍 Common First-Time Issues

### Issue: Chrome driver not found
**Solution**: The script auto-downloads it. Ensure Chrome is installed.

### Issue: Login fails
**Solution**: Run with `--no-headless` to see what's happening. Check credentials and selectors.

### Issue: No bills downloaded
**Solution**: Check that:
- Credentials are correct
- CSS selectors match the website
- Billing period has bills available

### Issue: AppFolio upload fails
**Solution**: Verify:
- API key is correct
- `appfolio_property_id` is set in config
- Property exists in AppFolio

## 🎯 Next Steps

1. Set up a cron job for automatic monthly runs
2. Add more buildings and utility providers
3. Customize billing period months in `.env`
4. Review logs regularly for any issues

## 💡 Tips

- Start with one building and one utility provider
- Test with `--dry-run` first
- Use `--no-headless` when debugging
- Check the organized structure matches your needs
- Keep credentials secure and never commit `.env`

## 🆘 Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Review logs in `logs/` directory
- Open an issue on GitHub

Happy automating! 🎉
