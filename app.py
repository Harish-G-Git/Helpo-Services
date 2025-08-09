from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google_sheets import add_vendor, connect_to_sheet, get_reviews, add_review
from datetime import datetime
import os
import re
import gspread
import requests
from collections import Counter, defaultdict
from oauth2client.service_account import ServiceAccountCredentials
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
import config  # <--- NEW

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.secret_key = config.SECRET_KEY

TWOFACTOR_API_KEY = config.TWOFACTOR_API_KEY
SENDER_EMAIL = config.SENDER_EMAIL
SENDER_PASSWORD = config.SENDER_PASSWORD


# ✅ Add to the top with other imports
from flask import request

# ✅ Replace the existing home route with this
@app.route("/")
def home():
    query = request.args.get("query", "").strip().lower()
    location = request.args.get("location", "").strip().lower()

    ads, vendors = [], []

    try:
        ads = get_ads()
    except Exception as e:
        print("Ad fetch failed:", e)

    try:
        sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
        vendors = sheet.get_all_records()

        # Add review data
        review_sheet = connect_to_sheet("HelpoVendorSheet", "VendorReviews")
        reviews = review_sheet.get_all_records()
        review_map = defaultdict(list)
        for r in reviews:
            phone = str(r.get("VendorPhone", "")).strip()
            try:
                rating = int(r.get("Rating", 0))
                if 1 <= rating <= 5 and phone:
                    review_map[phone].append(rating)
            except (ValueError, TypeError):
                continue

        for v in vendors:
            phone = str(v.get("phone", "")).strip()
            ratings = review_map.get(phone, [])
            if ratings:
                v["average_rating"] = round(sum(ratings) / len(ratings), 1)
                v["review_count"] = len(ratings)
            else:
                v["average_rating"] = None
                v["review_count"] = 0

        # Filter by search and location
        if query:
            vendors = [v for v in vendors if query in v.get("business_name", "").lower() or query in v.get("category", "").lower()]
        if location:
            vendors = [v for v in vendors if location in v.get("city", "").lower()]

    except Exception as e:
        print("Vendor fetch failed:", e)

    return render_template("index.html", ads=ads, vendors=vendors)


@app.route("/send_otp")
def send_otp():
    phone = request.args.get("phone")
    if not phone or not re.match(r"^91[6-9]\d{9}$", phone):
        return jsonify({"status": "Failed", "message": "Invalid phone format"})
    try:
        response = requests.get(f"https://2factor.in/API/V1/{TWOFACTOR_API_KEY}/SMS/{phone}/AUTOGEN")
        result = response.json()
        print("📞 OTP API response:", result)  # ✅ Add this line
        if result.get("Status") == "Success":
            return jsonify({"status": "Success", "session_id": result.get("Details")})
        else:
            return jsonify({"status": "Failed", "message": result.get("Details", "OTP sending failed")})
    except Exception as e:
        print("🚨 OTP send error:", e)  # ✅ Add this
        return jsonify({"status": "Failed", "message": str(e)})


@app.route("/verify_otp")
def verify_otp():
    session_id = request.args.get("session_id")
    otp = request.args.get("otp")
    try:
        response = requests.get(f"https://2factor.in/API/V1/{TWOFACTOR_API_KEY}/SMS/VERIFY/{session_id}/{otp}")
        result = response.json()
        return jsonify({"status": result.get("Status", "Failed")})
    except Exception as e:
        return jsonify({"status": "Failed", "message": str(e)})

@app.route("/vendor", methods=["GET", "POST"])
def vendor():
    message = None
    if request.method == "POST":
        data = {key: request.form.get(key) for key in [
            "business_name", "phone", "email", "password", "confirm_password",
            "plot_info", "building_info", "street", "landmark", "area", "city", "state", "pincode",
            "category", "service_hours", "description"
        ]}

        if data["password"] != data["confirm_password"]:
            message = "Passwords do not match."
            return render_template("vendor.html", message=message)

        if not all(data.values()) or not re.match(r"^[6-9]\d{9}$", data["phone"]):
            message = "Please fill in all required fields correctly."
            return render_template("vendor.html", message=message)

        photos = request.files.getlist("photos")
        photo_names = [photo.filename for photo in photos if photo.filename]
        for photo in photos:
            if photo.filename:
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo.filename))

        data["photos"] = ",".join(photo_names)
        result = add_vendor(data)
        message = "Vendor already registered." if result == "duplicate" else "Vendor registered successfully!"

    return render_template("vendor.html", message=message)

@app.route("/vendor/<phone>", methods=["GET", "POST"])
def vendor_detail(phone):
    sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    vendor = next((v for v in sheet.get_all_records() if str(v["phone"]).strip() == phone.strip()), None)
    if not vendor:
        return "Vendor not found", 404

    if request.method == "POST":
        name = request.form.get("name")
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        photo = request.files.get("review_photo")
        filename = secure_filename(photo.filename) if photo and photo.filename else ""
        if filename:
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        if name and rating and comment:
            add_review(phone, name, rating, filename, comment)

    reviews = get_reviews(phone)
    average_rating = round(sum(int(r["Rating"]) for r in reviews) / len(reviews), 1) if reviews else None
    rating_counts = Counter(int(r["Rating"]) for r in reviews)
    total_ratings = sum(rating_counts.values())

    return render_template("vendor_detail.html", vendor=vendor, reviews=reviews, average_rating=average_rating,
                           rating_counts=rating_counts, total_ratings=total_ratings)

@app.route("/api/vendors")
def api_vendors():
    category = request.args.get("category", "").lower()
    query = request.args.get("query", "").lower()

    vendor_sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    review_sheet = connect_to_sheet("HelpoVendorSheet", "VendorReviews")
    vendors = vendor_sheet.get_all_records()
    reviews = review_sheet.get_all_records()
    review_map = defaultdict(list)
    
    for r in reviews:
        # ✅ CORRECTED: Use 'VendorPhone' to match the detail page logic and the sheet header
        phone = str(r.get("VendorPhone", "")).strip()
        if not phone:
            continue
        try:
            rating = int(r.get("Rating", 0))
            if 1 <= rating <= 5:
                review_map[phone].append(rating)
        except (ValueError, TypeError):
            continue

    # ... (The rest of the function remains the same) ...
    
    # This part correctly uses the 'phone' key from the main vendor record
    for v in vendors:
        phone_key = str(v.get("phone", "")).strip()
        ratings = review_map.get(phone_key, [])
        v["average_rating"] = round(sum(ratings) / len(ratings), 1) if ratings else None
        v["review_count"] = len(ratings)

    # Filtering logic remains the same
    if query:
        vendors = [v for v in vendors if query in v.get('business_name', '').lower() or query in v.get('category', '').lower()]
    if category:
        vendors = [v for v in vendors if v.get('category', '').lower() == category]

    return jsonify(vendors)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username, password = request.form.get("username"), request.form.get("password")
        if username == "admin" and password == "password123":
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("admin_login.html", error=error)

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    return render_template("admin_dashboard.html", vendors=sheet.get_all_records())

#@app.route("/vendor/dashboard")
#def vendor_dashboard():
#    if "vendor_phone" not in session:
#        return redirect("/vendor/login")
#    phone = session["vendor_phone"]
#    vendor_sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
#    contact_sheet = connect_to_sheet("HelpoVendorSheet", "ContactLeads")
#    vendors = vendor_sheet.get_all_records()
#    leads = contact_sheet.get_all_records()
#    vendor = next((v for v in vendors if str(v["phone"]).strip() == phone), None)
#    vendor_leads = [l for l in leads if str(l.get("vendor_phone", "")).strip() == phone]
#    return render_template("vendor_dashboard.html", vendor=vendor, lead_count=len(vendor_leads), active_tab="dashboard")


@app.route('/vendor/dashboard', methods=['GET', 'POST'])
def vendor_dashboard():
    if "vendor_phone" not in session:
        return redirect("/vendor/login")

    phone = session["vendor_phone"]
    vendor_sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    contact_sheet = connect_to_sheet("HelpoVendorSheet", "ContactLeads")
    vendors = vendor_sheet.get_all_records()
    leads = contact_sheet.get_all_records()

    vendor = next((v for v in vendors if str(v["phone"]).strip() == phone), None)
    vendor_leads = [l for l in leads if str(l.get("vendor_phone", "")).strip() == phone]

    plans = [
        {
            "name": "Basic",
            "price": "₹199/month (₹6.63/day)",
            "features": ["👤 Basic listing on Helpo platform", "Email support", "📈 Access to basic profile analytics","🛡️ Verified vendor badge"]
        },
        {
            "name": "Standard",
            "price": "₹499/month(₹16.63/day)",
            "features": ["👀 Increased visibility in search results", "⭐ Featured in category listings", "💬 Priority support", "🔍 Access to callback request tools (when customers ask to be contacted)"]
        },
        {
            "name": "Premium",
            "price": "₹999/month(₹33.30/day)",
            "features": ["🚀 Top-tier placement on homepage & search results", "🧲 Priority access to customer callback requests", "📞 Dedicated account support", "🛠️ Advanced analytics dashboard"]
        }
    ]

    # Optional: show subscription confirmation message if just subscribed
    message = None
    if request.method == 'POST':
        selected_plan = request.form.get('plan')
        session['selected_plan'] = selected_plan
        return redirect('/vendor/subscribe')  # Redirect to payment

    return render_template("vendor_dashboard.html",
                           vendor=vendor,
                           lead_count=len(vendor_leads),
                           active_tab="dashboard",
                           plans=plans,
                           message=message)



# Leads Page 

from datetime import datetime

@app.route("/vendor/leads")
def vendor_leads():
    if not session.get("vendor_logged_in"):
        return redirect("/vendor/login")

    phone = session.get("vendor_phone")
    if not phone:
        return redirect("/vendor/login")

    try:
        sheet = connect_to_sheet("HelpoVendorSheet", "ContactLeads")
        all_leads = sheet.get_all_records()

        my_leads = [
            {
                "name": lead.get("user_name"),
                "phone": lead.get("user_phone "),
                "message": lead.get("message "),
                "timestamp": lead.get("timestamp "),
            }
            for lead in all_leads
            if str(lead.get("vendor_phone", "")).strip() == str(phone)
        ]

        # ✅ Sort by timestamp descending
        for lead in my_leads:
            try:
                lead["timestamp_parsed"] = datetime.strptime(lead["timestamp"], "%Y-%m-%d %H:%M:%S")
            except:
                lead["timestamp_parsed"] = datetime.now()  # fallback

        my_leads.sort(key=lambda x: x["timestamp_parsed"], reverse=True)

        # ✅ Filter by search (name or phone)
        search = request.args.get("search", "").strip().lower()
        if search:
            my_leads = [
                lead for lead in my_leads
                if search in str(lead["name"]).lower() or search in str(lead["phone"])
            ]

        return render_template("vendor_leads.html", leads=my_leads, active_tab="leads")

    except Exception as e:
        print(f"Error fetching vendor leads: {e}")
        return render_template("vendor_leads.html", leads=[], active_tab="leads", error="Could not fetch leads.")

        
#@app.route("/vendor/leads")
#def vendor_leads():
#    if not session.get("vendor_logged_in"):
#        return redirect("/vendor/login")
#    phone = session["vendor_phone"]
#    sheet = connect_to_sheet("HelpoVendorSheet", "VendorLeads")
#    leads = sheet.get_all_records()
#    my_leads = [l for l in leads if str(l.get("vendor_phone")) == phone]
#    return render_template("vendor_leads.html", leads=my_leads, active_tab="leads")

@app.route("/vendor/profile", methods=["GET", "POST"])
def vendor_profile():
    if not session.get("vendor_logged_in"):
        return redirect("/vendor/login")

    phone = session["vendor_phone"]
    sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    records = sheet.get_all_records()
    print("📋 Records:", records)

    # Locate vendor row in sheet (start=2 for 1-based index + header row)
    row_index = next((i for i, v in enumerate(records, start=2)
                      if str(v.get("phone", "")).strip() == str(phone).strip()), None)

    if request.method == "POST" and row_index:
        # Editable columns
        editable_columns = [
            "business_name", "pincode", "city", "state",
            "plot_info", "building_info", "street", "landmark", "area",
            "category", "phone", "description", "service_hours",
            "email", "password", "confirm_password"
        ]

        # Load form data
        updated_data = {col: request.form.get(col, "") for col in editable_columns}

        # Handle photo uploads
        uploaded_photos = request.files.getlist("photos")
        new_photo_names = []

        for photo in uploaded_photos:
            if photo and photo.filename:
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                new_photo_names.append(filename)

        # Get existing vendor record
        existing_vendor = next((v for v in records
                                if str(v.get("phone", "")).strip() == str(phone).strip()), None)

        existing_photos = existing_vendor.get("photos", "") if existing_vendor else ""
        existing_photo_list = [p.strip() for p in existing_photos.split(",") if p.strip()]
        
        # 🗑 Get photos user wants to remove
        remove_photos = request.form.getlist("remove_photos")
        
        # Final photo list = existing - removed + new uploads
        final_photos = [p for p in existing_photo_list if p not in remove_photos]
        final_photos.extend(new_photo_names)
        updated_data["photos"] = ",".join(final_photos)


        # Update sheet
        for col_name, value in updated_data.items():
            try:
                col_number = list(records[0].keys()).index(col_name) + 1  # 1-based index
                sheet.update_cell(row_index, col_number, value)
            except ValueError:
                print(f"⚠️ Column '{col_name}' not found in sheet.")

        return redirect("/vendor/profile")

    # Load current vendor data
    vendor = next((v for v in records
                   if str(v.get("phone", "")).strip() == str(phone).strip()), None)
    print("✅ Vendor found:", vendor)

    return render_template("vendor_profile.html", vendor=vendor, active_tab="profile")

@app.route("/vendor/logout")
def vendor_logout():
    session.clear()
    return redirect("/")

def get_ads():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet(config.ADS_SHEET)
    return sheet.get_all_records()

@app.template_filter('todatetime')
def todatetime(s, fmt="%Y-%m-%d %H:%M:%S"):
    try:
        return datetime.strptime(s, fmt)
    except:
        return datetime.now()

@app.route("/vendor/login", methods=["GET", "POST"])
def vendor_login():
    error = None
    if request.method == "POST":
        identifier = request.form.get("identifier").strip()
        password = request.form.get("password").strip()

        sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
        vendors = sheet.get_all_records()

        # Match phone or email
        vendor = next(
            (v for v in vendors if (str(v.get("phone")) == identifier or v.get("email", "").lower() == identifier.lower()) and v.get("password") == password),
            None
        )

        if vendor:
            session["vendor_logged_in"] = True
            session["vendor_phone"] = vendor["phone"]
            return redirect("/vendor/profile")
        else:
            error = "Invalid login. Please check your credentials."

    return render_template("vendor_login.html", error=error)

# Forgot Password

@app.route("/vendor/forgot-password", methods=["GET", "POST"])
def vendor_forgot_password():
    message = None
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # --- Validations ---
        if not email or not new_password or not confirm_password:
            error = "Please fill out all fields."
            return render_template("vendor_forgot_password.html", error=error)
        
        if new_password != confirm_password:
            error = "Passwords do not match."
            return render_template("vendor_forgot_password.html", error=error, email=email)

        try:
            sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
            records = sheet.get_all_records()

            # Find the vendor by email
            vendor_row_index = None
            vendor_record = None
            for i, record in enumerate(records):
                if record.get("email", "").lower() == email.lower():
                    # gspread rows are 1-based, and there's a header, so add 2
                    vendor_row_index = i + 2
                    vendor_record = record
                    break
            
            if not vendor_row_index:
                error = "No account found with that email address."
                return render_template("vendor_forgot_password.html", error=error)

            # Find the 'password' column index (1-based)
            headers = sheet.row_values(1)
            try:
                password_col_index = headers.index("password") + 1
            except ValueError:
                error = "System configuration error: 'password' column not found."
                return render_template("vendor_forgot_password.html", error=error)

            # --- Update the sheet ---
            sheet.update_cell(vendor_row_index, password_col_index, new_password)
            
            message = "Your password has been updated successfully! You can now log in."

        except Exception as e:
            print(f"Password recovery error: {e}")
            error = "An unexpected error occurred. Please try again later."
            return render_template("vendor_forgot_password.html", error=error)

    return render_template("vendor_forgot_password.html", message=message, error=error)
    
    
@app.route("/submit_callback", methods=["POST"])
def submit_callback():
    name = request.form.get("user_name")
    phone = request.form.get("user_phone")
    message = request.form.get("message")
    vendor_phone = request.form.get("vendor_phone")

    if not (name and phone and vendor_phone):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        sheet = connect_to_sheet("HelpoVendorSheet", "ContactLeads")
        sheet.append_row([name, phone, message or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), vendor_phone])
        return jsonify({"status": "success", "message": "Callback request submitted."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def send_email_otp(to_email, otp):
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(f"Your Helpo Services OTP is: {otp}")
    msg["Subject"] = "Email OTP - Helpo Services"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email send failed:", e)
        raise



import random
import traceback

@app.route("/send_email_otp", methods=["POST"])
def send_email_otp_route():
    email = request.form.get("email")
    if not email:
        return jsonify({"status": "error", "message": "Email required"}), 400

    otp = str(random.randint(100000, 999999))
    session["email_otp"] = otp
    session["email_otp_to"] = email

    try:
        send_email_otp(email, otp)
        return jsonify({"status": "success"})
    except Exception as e:
        traceback.print_exc()  # Print the real error in terminal
        return jsonify({"status": "error", "message": "Server error while sending email OTP."}), 500


@app.route("/verify_email_otp", methods=["POST"])
def verify_email_otp_route():
    email = request.form.get("email")
    otp_input = request.form.get("otp")
    if not email or not otp_input:
        return jsonify({"status": "error", "message": "Missing email or OTP"})

    stored_otp = session.get("email_otp")
    stored_email = session.get("email_otp_to")

    if stored_email == email and stored_otp == otp_input:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid OTP"})

from flask import jsonify
from difflib import get_close_matches

@app.route("/api/vendor_suggestions")
def vendor_suggestions():
    query = request.args.get("q", "").lower()
    user_city = request.args.get("city", "").lower()

    if not query:
        return jsonify([])

    sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    vendors = sheet.get_all_records()

    suggestions = set()
    for v in vendors:
        for field in ["business_name", "category", "city", "description"]:
            value = v.get(field, "").lower()
            if query in value or get_close_matches(query, [value], cutoff=0.7):
                if not user_city or user_city in v.get("city", "").lower():
                    suggestions.add(v.get("business_name"))

    return jsonify(sorted(suggestions))


@app.context_processor
def inject_now():
    return {'now': datetime.now}

# terms & conditions 
@app.route("/terms")
def terms():
    return render_template("terms.html")

# privacy policy


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")
    
    
# subscribe page

@app.route('/vendor/subscribe', methods=['GET', 'POST'])
def vendor_subscribe():
    if "vendor_phone" not in session:
        return redirect("/vendor/login")

    selected_plan = request.args.get("plan")

    if not selected_plan:
        return redirect("/vendor/dashboard")  # fallback

    # Simulate a payment page (you can replace this with real Razorpay/Stripe etc.)
    return render_template("vendor_payment.html", plan=selected_plan)

# payment status

@app.route('/vendor/payment-success', methods=['POST'])
def payment_success():
    if "vendor_phone" not in session:
        return redirect("/vendor/login")

    plan = request.form.get("plan")
    phone = session["vendor_phone"]

    # Update subscription in Google Sheet
    vendor_sheet = connect_to_sheet("HelpoVendorSheet", "Helpovendor")
    vendors = vendor_sheet.get_all_records()

    for i, v in enumerate(vendors):
        if str(v.get("phone")).strip() == str(phone).strip():
            vendor_sheet.update_cell(i + 2, YOUR_PLAN_COLUMN_INDEX, plan)
            break

    return redirect("/vendor/dashboard")


if __name__ == "__main__":
    app.run(debug=True)
