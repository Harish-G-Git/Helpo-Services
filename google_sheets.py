import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def connect_to_sheet(sheet_name, tab_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).worksheet(tab_name)
    return sheet

def add_vendor(data):
    sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    existing = sheet.get_all_records()
    if any(str(v.get("phone")) == str(data["phone"]) for v in existing):
        return "duplicate"

    row = [
    data.get("business_name", ""),
    data.get("pincode", ""),
    data.get("city", ""),
    data.get("state", ""),
    data.get("plot_info", ""),
    data.get("building_info", ""),
    data.get("street", ""),
    data.get("landmark", ""),
    data.get("area", ""),
    data.get("category", ""),
    data.get("phone", ""),
    data.get("photos", ""),
    data.get("description", ""),      # ✅ NEW
    data.get("service_hours", ""),    # ✅ NEW
    data.get("email", ""),    # ✅ NEW
    data.get("password", ""),    # ✅ NEW
    data.get("confirm_password", ""),    # ✅ NEW
    data.get("subscription", "free"),  # Default to "free"
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]

    sheet.append_row(row)
    return "success"

def get_reviews(phone):
    sheet = connect_to_sheet("HelpoVendorSheet", "VendorReviews")
    all_reviews = sheet.get_all_records()
    return [r for r in all_reviews if str(r.get("VendorPhone", "")).strip() == phone]

def add_review(phone, name, rating, photo, comment):
    sheet = connect_to_sheet("HelpoVendorSheet", "VendorReviews")  # or your review sheet name
    sheet.append_row([
        phone,
        name,
        rating,
        photo,      # ✅ Add this new column
        comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

