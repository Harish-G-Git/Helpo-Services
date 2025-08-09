import os

# Flask secret key
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "helpo_admin_secret_2025")

# Upload folder
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")

# TwoFactor API Key
TWOFACTOR_API_KEY = os.getenv("TWOFACTOR_API_KEY", "abd4d443-71bd-11f0-a562-0200cd936042")

# Email credentials for OTP
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "harishprogram.py@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "fkkf vlvo rwik mbjx")

# Google Sheets config
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "HelpoVendorSheet")
VENDOR_SHEET = os.getenv("VENDOR_SHEET", "Helpovendor")
REVIEW_SHEET = os.getenv("REVIEW_SHEET", "VendorReviews")
LEADS_SHEET = os.getenv("LEADS_SHEET", "ContactLeads")
ADS_SHEET = os.getenv("ADS_SHEET", "Ads")

# Admin credentials (for demo only; use proper authentication in production)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password123")