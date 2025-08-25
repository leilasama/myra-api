from flask import Flask, request, jsonify, send_file
import sys
import os
from io import BytesIO

# اضافه کردن مسیر فعلی
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import meal_planner
    DATA = meal_planner.load_data()
except Exception as e:
    print("❌ خطا در بارگذاری meal_planner:", e)
    DATA = None

app = Flask(__name__)

@app.route('/api/generate-plan', methods=['POST'])
def generate_plan():
    if DATA is None:
        return jsonify({"error": "سیستم در دسترس نیست."}), 500

    try:
        data = request.json
        user = {
            "name": data.get("name", "کاربر"),
            "age": int(data.get("age", 30)),
            "weight": float(data.get("weight", 70)),
            "height": float(data.get("height", 170)),
            "gender": data.get("gender", "female"),
            "conditions": data.get("conditions", []),
            "mizaj": data.get("mizaj", "معتدل"),
            "blood_type": data.get("blood_type", "O"),
            "goal": data.get("goal", "maintain"),
            "duration_weeks": int(data.get("duration_weeks", 2)),
            "activity": data.get("activity", "moderate"),
            "food_preferences": {
                "lactose_intolerance": data.get("lactose_intolerance", False),
                "gluten_free": data.get("gluten_free", False)
            },
            "workout": {"days_per_week": 3, "calories_per_session": 300}
        }

        result = meal_planner.generate_weekly_meal_plan(user, DATA)
        if "error" in result:
            return jsonify(result), 400

        pdf_buffer = create_pdf(result)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"رژیم_غذایی_{user['name']}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def create_pdf(result):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Vazir', '', 'Vazir-Regular.ttf', uni=True)
    pdf.set_font('Vazir', size=14)

    pdf.cell(0, 10, txt=f"رژیم غذایی {result['user_name']}", ln=True, align='R')
    pdf.cell(0, 10, txt=f"هدف: {result['goal']}", ln=True, align='R')
    pdf.cell(0, 10, txt=f"مدت: {result['duration_weeks']} هفته", ln=True, align='R')
    pdf.cell(0, 10, txt=f"کالری روزانه: {result['daily_calories']}", ln=True, align='R')
    pdf.ln(10)

    for day in result["meal_plan"]:
        pdf.cell(0, 10, txt=f"روز {day['day']}", ln=True, align='R', bold=True)
        for meal_name, meal in day["meals"].items():
            txt = f"• {meal_name}: {meal['name']} | {meal['calories']} کالری"
            pdf.cell(0, 8, txt=txt, ln=True, align='R')
        pdf.ln(5)

    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

@app.route('/')
def home():
    return "سرویس مایرا فعال است 🍽️"

if __name__ == '__main__':
    app.run(port=5000)