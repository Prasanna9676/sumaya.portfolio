from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import json
app = Flask(__name__)
app.secret_key = "super_secret_healthcare_key"

# MongoDB Setup
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    db = client["healthcare_db"]
    users_collection = db["users"]
    diseases_collection = db["diseases"]
    contact_collection = db["contact_queries"]
    search_history_collection = db["search_queries"]
    client.server_info() # Test connection
    
    # Pre-populate a comprehensive list of diseases if collection is empty
    if diseases_collection.count_documents({}) == 0:
        sample_diseases = [
            # Fever & Pain
            {"category": "Fever & Pain", "disease": "Common Cold / Flu", "symptoms": "Fever, cough, runny nose, body ache", "tablet": "Paracetamol & Antihistamines"},
            {"category": "Fever & Pain", "disease": "Migraine / Severe Headache", "symptoms": "Headache, nausea, sensitivity to light", "tablet": "Ibuprofen / Naproxen"},
            {"category": "Fever & Pain", "disease": "Muscle Pain / Sprains", "symptoms": "Localized pain, swelling, stiffness", "tablet": "Diclofenac Gel / Aceclofenac"},
            
            # Digestive Health
            {"category": "Digestive Health", "disease": "Acid Reflux / Acidity", "symptoms": "Heartburn, chest pain, nausea", "tablet": "Pantoprazole / Digene Syrup"},
            {"category": "Digestive Health", "disease": "Diarrhea / Loose Motion", "symptoms": "Frequent watery stools, stomach cramps", "tablet": "Loperamide / ORS (Electral)"},
            {"category": "Digestive Health", "disease": "Constipation", "symptoms": "Hard stools, infrequent bowel movements", "tablet": "Bisacodyl / Cremaffin Syrup"},
            {"category": "Digestive Health", "disease": "Mild Food Poisoning", "symptoms": "Stomach pain, vomiting, diarrhea", "tablet": "ORS & Probiotics"},
            
            # Respiratory & Allergy
            {"category": "Respiratory & Allergy", "disease": "Allergies / Hay Fever", "symptoms": "Sneezing, itchy eyes, runny nose", "tablet": "Cetirizine / Loratadine"},
            {"category": "Respiratory & Allergy", "disease": "Dry Cough", "symptoms": "Tickly throat, no mucus", "tablet": "Dextromethorphan Syrup"},
            {"category": "Respiratory & Allergy", "disease": "Wet Cough", "symptoms": "Cough with mucus, chest congestion", "tablet": "Ambroxol / Guaifenesin Syrup"},
            {"category": "Respiratory & Allergy", "disease": "Asthma (Mild)", "symptoms": "Wheezing, shortness of breath", "tablet": "Salbutamol Inhaler (Consult MD)"},
            
            # Skin & Hygiene
            {"category": "Skin & Hygiene", "category_icon": "🧴", "disease": "Skin Rash / Eczema", "symptoms": "Itchy, red, inflamed skin", "tablet": "Hydrocortisone Cream / Calamine"},
            {"category": "Skin & Hygiene", "disease": "Fungal Infection", "symptoms": "Itchy red rings, scaling skin", "tablet": "Clotrimazole / Itraconazole"},
            {"category": "Skin & Hygiene", "disease": "Acne / Pimples", "symptoms": "Blackheads, red bumps, oily skin", "tablet": "Benzoyl Peroxide / Salicylic Acid"},
            
            # Vitamins & Supplements
            {"category": "Vitamins & Supplements", "disease": "Vitamin A Deficiency", "symptoms": "Night blindness, dry eyes, skin issues", "tablet": "Vitamin A (Retinol) Capsules"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin C (Immunity)", "symptoms": "Scurvy, slow wound healing, weak immunity", "tablet": "Ascorbic Acid (Limcee)"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin D3 (Bones)", "symptoms": "Bone pain, muscle weakness, mood issues", "tablet": "Cholecalciferol (Uprise-D3)"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin E (Skin/Hair)", "symptoms": "Nerve damage, muscle weakness, dry skin", "tablet": "Evion 400 (Tocopherol)"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin K (Clotting)", "symptoms": "Excessive bleeding, easy bruising", "tablet": "Phytonadione (Vitamin K1)"},
            
            # B-Complex Vitamins
            {"category": "Vitamins & Supplements", "disease": "Vitamin B1 (Thiamine)", "symptoms": "Beriberi, loss of appetite, fatigue", "tablet": "Thiamine Hydrochloride"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B2 (Riboflavin)", "symptoms": "Mouth sores, sore throat, skin cracks", "tablet": "Riboflavin Tablets"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B3 (Niacin)", "symptoms": "Pellagra, digestive issues, skin inflammation", "tablet": "Niacinamide"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B5 (Pantothenic Acid)", "symptoms": "Numbness, burning hands/feet, fatigue", "tablet": "Calcium Pantothenate"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B6 (Pyridoxine)", "symptoms": "Anemia, depression, confusion", "tablet": "Pyridoxine (Neurobion)"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B7 (Biotin)", "symptoms": "Hair loss, brittle nails, skin rashes", "tablet": "Biotin (Hair & Nail Support)"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B9 (Folic Acid)", "symptoms": "Anemia, pregnancy complications, fatigue", "tablet": "Folic Acid (Folvite)"},
            {"category": "Vitamins & Supplements", "disease": "Vitamin B12 (Cobalamin)", "symptoms": "Nerve pain, memory loss, fatigue", "tablet": "Methylcobalamin"}
        ]
        diseases_collection.insert_many(sample_diseases)

except Exception as e:
    print(f"MongoDB connection error: {e}")


# AI-based symptom engine for /api/search using OpenRouter
def analyze_symptoms(symptoms_str):
    api_key = "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"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    You are a medical symptom checker assistant. The user has provided the following query, which could be a disease name or symptoms:
    "{symptoms_str}"
    
    Please provide your response strictly as a JSON object with the following keys:
    "conditions": A list of 1 to 3 possible conditions (strings) based on the input.
    "precautions": A list of 1 to 2 sentences of advice or precautions (strings).
    "medicine": MANDATORY. You must provide a string specifying an over-the-counter medicine, tablet, or drug class for this issue. Example: "Paracetamol", "Antacids", or "Cetirizine".
    "emergency": A boolean (true/false) indicating if this requires immediate emergency care.
    
    Do not include any other text or markdown formatting. Output raw JSON only.
    """
    
    data = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response_json = response.json()
        
        content = response_json["choices"][0]["message"]["content"]
        
        # Clean up possible markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        result = json.loads(content)
        return result.get("conditions", ["Condition analysis failed."]), result.get("precautions", ["Please consult a doctor."]), result.get("medicine", "Consult Doctor"), result.get("emergency", False)
        
    except Exception as e:
        print(f"LLM API Error: {e}")
        # Fallback response
        return ["Unable to analyze symptoms at the moment."], ["Please consult a healthcare professional."], "Consult Doctor", False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/services")
def services():
    diseases = list(diseases_collection.find({}))
    return render_template("services.html", diseases_data=diseases)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if users_collection.find_one({"email": email}):
            flash("Email already exists. Please login.", "danger")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password
        })
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        
        contact_data = {
            "name": name,
            "email": email,
            "message": message,
            "date": datetime.now()
        }
        contact_collection.insert_one(contact_data)
        flash("Thank you! Your message has been sent.", "success")
        return redirect(url_for("contact"))
        
    return render_template("contact.html")

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.json
    symptoms_str = data.get("symptoms", "")
    
    conditions, precautions, medicine, emergency = analyze_symptoms(symptoms_str)
    
    # Log the search
    search_data = {
        "symptoms": symptoms_str,
        "conditions": conditions,
        "medicine": medicine,
        "emergency": emergency,
        "date": datetime.now()
    }
    
    if "user_id" in session:
        search_data["user_id"] = session["user_id"]
        
    search_history_collection.insert_one(search_data)
    
    return jsonify({
        "conditions": conditions,
        "precautions": precautions,
        "medicine": medicine,
        "emergency": emergency
    })

# AI-based hospital search for /api/hospitals
def analyze_hospitals(query):
    api_key = "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"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    You are a healthcare assistant. The user is searching for hospitals in India with the following query: "{query}"
    
    Please provide a list of 4 to 6 real, prominent hospitals in India that match this query (specialty or location).
    For each hospital, provide:
    1. Hospital Name
    2. Full Address
    3. Specialization highlight
    
    Output strictly as a JSON list of objects with keys: "name", "address", "specialty".
    Do not include any other text.
    """
    
    data = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        content = response.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"): content = content[7:-3].strip()
        elif content.startswith("```"): content = content[3:-3].strip()
        return json.loads(content)
    except Exception as e:
        print(f"Hospital API Error: {e}")
        return []

@app.route("/api/hospitals", methods=["POST"])
def api_hospitals():
    data = request.json
    query = data.get("query", "")
    hospitals = analyze_hospitals(query)
    return jsonify({"hospitals": hospitals})

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please login to view your dashboard.", "warning")
        return redirect(url_for("login"))
        
    user_history = list(search_history_collection.find({"user_id": session["user_id"]}).sort("date", -1))
    
    # Process data for charts
    stats = {
        "total_searches": len(user_history),
        "emergency_cases": len([s for s in user_history if s.get("emergency")]),
    }
    
    return render_template("dashboard.html", history=user_history, stats=stats)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
