# meal_planner.py
import os
import pandas as pd
import random

def load_data():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    file_path = os.path.join(desktop, "meal_plan_database.xlsx")
    print(f"🔍 در حال جستجوی فایل: {file_path}")
    
    if not os.path.exists(file_path):
        print("❌ فایل 'meal_plan_database.xlsx' روی دسکتاپ پیدا نشد!")
        print("📌 لطفاً مطمئن شوید:")
        print("   1. فایل با اسم دقیق 'meal_plan_database.xlsx' روی دسکتاپ است")
        print("   2. فایل باز نیست (مثلاً با اکسل یا گوگل شیت)")
        return None
    
    try:
        foods_df = pd.read_excel(file_path, sheet_name="foods")
        rules_df = pd.read_excel(file_path, sheet_name="rules")
        portion_df = pd.read_excel(file_path, sheet_name="portion_guide")
        temperament_df = pd.read_excel(file_path, sheet_name="temperament_foods")

        print("✅ فایل اکسل با موفقیت لود شد!")
        print(f"📊 {len(foods_df)} غذا بارگذاری شد.")
        print(f"📋 {len(rules_df)} قانون تغذیه یافت شد.")
        
        return {
            "foods": foods_df,
            "rules": rules_df,
            "portion": portion_df,
            "temperament": temperament_df
        }
    except Exception as e:
        print(f"❌ خطا در خواندن فایل اکسل: {e}")
        return None

def calculate_bmr(weight, height, age, gender):
    if gender.lower() == "female":
        return 10 * weight + 6.25 * height - 5 * age - 161
    else:
        return 10 * weight + 6.25 * height - 5 * age + 5

def calculate_tdee(bmr, activity_level):
    factors = {"low": 1.2, "moderate": 1.55, "high": 1.725}
    return bmr * factors.get(activity_level.lower(), 1.2)

def get_daily_calories(user):
    bmr = calculate_bmr(user["weight"], user["height"], user["age"], user["gender"])
    tdee = calculate_tdee(bmr, user["activity"])
    
    # احتساب کالری ورزش
    workout = user.get("workout", {})
    daily_burn = (workout.get("days_per_week", 0) * workout.get("calories_per_session", 0)) / 7
    
    if user["goal"] == "weight_loss":
        target_calories = tdee - 500 + daily_burn
    elif user["goal"] == "muscle_gain":
        target_calories = tdee + 300 + daily_burn
    else:  # maintain
        target_calories = tdee + daily_burn
    
    min_cal = 1200 if user["gender"] == "female" else 1500
    return max(target_calories, min_cal)

def filter_foods_by_rules(foods_df: pd.DataFrame, user: dict, data: dict) -> pd.DataFrame:
    allowed = foods_df.copy()
    
    # استخراج داده‌ها
    conditions = [c.lower() for c in user.get("conditions", [])]
    lactose_int = user["food_preferences"].get("lactose_intolerance", False)
    mizaj = user.get("mizaj", "معتدل").lower()
    rules_df = data["rules"]
    temperament_df = data["temperament"]

    # بررسی ستون‌های ضروری
    if "بیماری / شرایط" not in rules_df.columns or "محدودیت" not in rules_df.columns:
        print("❌ خطا: ستون‌های 'بیماری / شرایط' یا 'محدودیت' در برگ rules یافت نشد.")
        return allowed

    for _, rule in rules_df.iterrows():
        condition = str(rule["بیماری / شرایط"]).strip().lower()
        restriction = str(rule["محدودیت"]).strip().lower()
        match = False

        if condition in conditions:
            match = True
        elif condition == "عدم تحمل لاکتوز" and lactose_int:
            match = True

        if not match:
            continue

        if "gi بالا" in restriction or "گلیسمی بالا" in restriction:
            allowed = allowed[allowed["GI"] <= 55]
        elif "لاکتوز" in restriction:
            allowed = allowed[allowed["لاکتوز"] == "خیر"]
        elif "گلوتن" in restriction:
            allowed = allowed[allowed["گلوتن"] == "خیر"]
        elif "نمک بالا" in restriction or "نمک زیاد" in restriction:
            allowed = allowed[allowed["نمک بالا"] == "خیر"]
        elif "گاززا" in restriction or "هضم سخت" in restriction:
            allowed = allowed[allowed["گاززا"] == "خیر"]
        elif "پورین بالا" in restriction or "نقرس" in restriction:
            allowed = allowed[allowed["پورین"] == "خیر"]
        elif "ترش" in restriction or "تند" in restriction:
            allowed = allowed[allowed["ترش/تند"] == "خیر"]

    # فیلتر بر اساس طبع
    if "نام غذا" in temperament_df.columns and "طبع" in temperament_df.columns:
        cold_foods = temperament_df[temperament_df["طبع"] == "سرد"]["نام غذا"].tolist()
        hot_foods = temperament_df[temperament_df["طبع"] == "گرم"]["نام غذا"].tolist()
        if mizaj == "سرد":
            allowed = allowed[~allowed["نام غذا"].str.contains('|'.join(cold_foods), case=False, na=False)]
        elif mizaj == "گرم":
            allowed = allowed[~allowed["نام غذا"].str.contains('|'.join(hot_foods), case=False, na=False)]
    
    return allowed

def generate_weekly_meal_plan(user: dict, data: dict) -> dict:
    daily_calories = get_daily_calories(user)
    total_days = user.get("duration_weeks", 2) * 7
    foods_df = data["foods"]
    allowed_foods = filter_foods_by_rules(foods_df, user, data)
    
    if allowed_foods.empty:
        return {"error": "هیچ غذایی با توجه به محدودیت‌های شما یافت نشد."}
    
    def get_pool(meal_type):
        return allowed_foods[allowed_foods["وعده"].str.contains(meal_type, case=False, na=False)]

    weekly_plan = []
    used_bf, used_lunch, used_dinner = [], [], []
    
    for day in range(1, total_days + 1):
        day_plan = {"day": day, "meals": {}}

        # ——— صبحانه ———
        breakfast_pool = get_pool("صبحانه")
        if breakfast_pool.empty:
            return {"error": "هیچ غذای صبحانه‌ای با محدودیت‌های شما یافت نشد."}
        
        bf_candidates = breakfast_pool[~breakfast_pool["نام غذا"].isin(used_bf[-3:])]
        bf = bf_candidates.sample(1).iloc[0] if not bf_candidates.empty else breakfast_pool.sample(1).iloc[0]
        used_bf.append(bf["نام غذا"])
        day_plan["meals"]["صبحانه"] = {
            "name": bf["نام غذا"],
            "calories": int(bf["کالری"]),
            "portion": bf["اندازه وعده"]
        }

        # ——— ناهار ———
        lunch_pool = get_pool("ناهار")
        if lunch_pool.empty:
            return {"error": "هیچ غذای ناهاری با محدودیت‌های شما یافت نشد."}
        
        lunch_candidates = lunch_pool[~lunch_pool["نام غذا"].isin(used_lunch[-2:])]
        lunch = lunch_candidates.sample(1).iloc[0] if not lunch_candidates.empty else lunch_pool.sample(1).iloc[0]
        used_lunch.append(lunch["نام غذا"])
        day_plan["meals"]["ناهار"] = {
            "name": lunch["نام غذا"],
            "calories": int(lunch["کالری"]),
            "portion": lunch["اندازه وعده"]
        }

        # ——— شام ———
        dinner_pool = get_pool("شام")
        if dinner_pool.empty:
            return {"error": "هیچ غذای شامی با محدودیت‌های شما یافت نشد."}
        
        dinner_candidates = dinner_pool[~dinner_pool["نام غذا"].isin(used_dinner[-2:])]
        dinner = dinner_candidates.sample(1).iloc[0] if not dinner_candidates.empty else dinner_pool.sample(1).iloc[0]
        used_dinner.append(dinner["نام غذا"])
        day_plan["meals"]["شام"] = {
            "name": dinner["نام غذا"],
            "calories": int(dinner["کالری"]),
            "portion": dinner["اندازه وعده"]
        }

        # ——— میان‌وعده ———
        snack_pool = get_pool("میان‌وعده")
        if snack_pool.empty:
            return {"error": "هیچ غذای میان‌وعده‌ای با محدودیت‌های شما یافت نشد."}

        snack1 = snack_pool.sample(1).iloc[0]
        snack2 = snack_pool.sample(1).iloc[0]

        day_plan["meals"]["میان‌وعده صبح"] = {
            "name": snack1["نام غذا"],
            "calories": int(snack1["کالری"]),
            "portion": snack1["اندازه وعده"]
        }
        day_plan["meals"]["میان‌وعده عصر"] = {
            "name": snack2["نام غذا"],
            "calories": int(snack2["کالری"]),
            "portion": snack2["اندازه وعده"]
        }

        weekly_plan.append(day_plan)

    return {
        "user_name": user.get("name", "کاربر"),
        "goal": user["goal"],
        "duration_weeks": user.get("duration_weeks", 2),
        "daily_calories": round(daily_calories),
        "meal_plan": weekly_plan
    }

def print_meal_plan(result: dict):
    if "error" in result:
        print(f"❌ {result['error']}")
        return

    print(f"\n🎯 رژیم غذایی برای {result['user_name']}")
    goal_persian = result['goal'].replace('weight_loss', 'کاهش وزن').replace('muscle_gain', 'افزایش عضله').replace('maintain', 'ثبات وزن')
    print(f"هدف: {goal_persian}")
    print(f"مدت: {result['duration_weeks']} هفته")
    print(f"کالری روزانه: {result['daily_calories']} کالری")
    print("=" * 80)
    for day in result["meal_plan"]:
        print(f"\n📅 روز {day['day']}:")
        for meal_name, meal in day["meals"].items():
            title = meal_name.replace("میان‌وعده", "میان‌وعده")
            print(f"  {title}: {meal['name']} | {meal['portion']} | {meal['calories']} کالری")