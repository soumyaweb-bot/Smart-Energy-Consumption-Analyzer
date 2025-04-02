from flask import Flask, render_template, request, jsonify
import json
import os
import requests
from dotenv import load_dotenv
import random
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Groq API Key (loaded from .env)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# Base URL for Groq
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Load consumption data
def load_consumption_data():
    with open('consumption_data/sample_data.json') as f:
        return json.load(f)

# Function to call Groq LLM API
def generate_energy_report(consumption_data):
    analysis_focus = random.choice([
        "reduce peak load",
        "optimize appliance usage",
        "implement renewable energy",
        "reduce overall energy consumption",
        "maximize energy efficiency during summer"
    ])

    prompt = (
        f"You are an expert energy analyst. Analyze the following household energy consumption data "
        f"and provide an precise and insightful report on how to {analysis_focus}.\n\n"
        f"Here is the data:\n{json.dumps(consumption_data, indent=2)}\n\n"
        f"Provide 3 actionable recommendations in bullet points and an overview."
        f"response must be short and each suggestion must not exceed more than 1line"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful energy optimization assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']

    except requests.exceptions.HTTPError as e:
        print("🔥 Groq API error:", e.response.status_code, e.response.text)
        return f"There was an error generating the energy report: {e.response.text}"

    except Exception as e:
        print("💥 Unexpected error:", str(e))
        return "There was an unexpected error. Please try again later."

# Predict next month's consumption
def predict_next_month(consumption_data):
    monthly_data = consumption_data.get('monthly_consumption_kwh', [])
    if not monthly_data:
        return "No consumption data available to make a prediction."

    total_consumptions = [month['total_consumption_kwh'] for month in monthly_data]

    average_consumption = sum(total_consumptions) / len(total_consumptions)
    last_month_consumption = total_consumptions[-1]

    trend = total_consumptions[-1] - total_consumptions[-2] if len(total_consumptions) >= 2 else 0
    predicted_consumption = last_month_consumption + trend * 0.5

    return {
        "average_consumption": round(average_consumption, 2),
        "predicted_next_month": round(predicted_consumption, 2),
        "last_month_consumption": last_month_consumption,
        "trend": round(trend, 2)
    }

# Find the month with the highest total consumption
def get_highest_consumption_month(consumption_data):
    monthly_data = consumption_data.get('monthly_consumption_kwh', [])
    if not monthly_data:
        return "No consumption data available."

    highest_month = max(monthly_data, key=lambda x: x['total_consumption_kwh'])
    return {
        "month": highest_month['month'],
        "consumption_kwh": highest_month['total_consumption_kwh'],
        "appliances": highest_month['appliances']
    }

# Calculate total appliance consumption over the year
def get_annual_appliance_consumption(consumption_data):
    monthly_data = consumption_data.get('monthly_consumption_kwh', [])
    if not monthly_data:
        return {}

    total_appliance_consumption = {}
    for month in monthly_data:
        appliances = month.get('appliances', {})
        for appliance, consumption in appliances.items():
            total_appliance_consumption[appliance] = total_appliance_consumption.get(appliance, 0) + consumption

    return total_appliance_consumption

# Home page route
@app.route('/')
def index():
    consumption_data = load_consumption_data()
    prediction = predict_next_month(consumption_data)
    highest_month = get_highest_consumption_month(consumption_data)
    annual_appliance_consumption = get_annual_appliance_consumption(consumption_data)

    return render_template(
        'index.html',
        consumption_data=consumption_data,
        prediction=prediction,
        highest_month=highest_month,
        annual_appliance_consumption=annual_appliance_consumption
    )

# Analyze report route
@app.route('/analyze', methods=['POST'])
def analyze():
    consumption_data = load_consumption_data()
    report = generate_energy_report(consumption_data)
    prediction = predict_next_month(consumption_data)
    highest_month = get_highest_consumption_month(consumption_data)
    annual_appliance_consumption = get_annual_appliance_consumption(consumption_data)

    return render_template(
        'index.html',
        report=report,
        consumption_data=consumption_data,
        prediction=prediction,
        highest_month=highest_month,
        annual_appliance_consumption=annual_appliance_consumption
    )

# Filter by date range
@app.route('/filter', methods=['POST'])
def filter_by_date():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if not start_date or not end_date:
        return "Invalid date range", 400

    start_dt = datetime.strptime(start_date, "%Y-%m")
    end_dt = datetime.strptime(end_date, "%Y-%m")

    consumption_data = load_consumption_data()
    filtered_months = []

    for month in consumption_data.get("monthly_consumption_kwh", []):
        month_dt = datetime.strptime(month["month"], "%Y-%m")
        if start_dt <= month_dt <= end_dt:
            filtered_months.append(month)

    filtered_data = {
        "monthly_consumption_kwh": filtered_months
    }

    report = generate_energy_report(filtered_data)
    prediction = predict_next_month(filtered_data)
    highest_month = get_highest_consumption_month(filtered_data)
    annual_appliance_consumption = get_annual_appliance_consumption(filtered_data)

    return render_template(
        'index.html',
        report=report,
        consumption_data=filtered_data,
        prediction=prediction,
        highest_month=highest_month,
        annual_appliance_consumption=annual_appliance_consumption
    )

# Optional API endpoint for JSON prediction
@app.route('/api/predict')
def predict_api():
    consumption_data = load_consumption_data()
    prediction = predict_next_month(consumption_data)
    return jsonify(prediction)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
