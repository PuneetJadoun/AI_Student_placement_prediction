def make_recommendations(data: dict) -> list[str]:
    tips = []
    if data["attendance"] < 75:
        tips.append("Attendance is below 75%. Set a realistic goal to improve attendance over the next month.")
    elif data["attendance"] < 85:
        tips.append("Attendance is fair. Aim for consistent attendance of 85% or higher where feasible.")
    if data["previous_score"] < 60:
        tips.append("Review the subjects with the weakest scores and use short, regular practice sessions.")
    elif data["previous_score"] < 75:
        tips.append("Build on your current score with weekly revision and timed practice questions.")
    if data["assignments_completed"] < 6:
        tips.append("Set a weekly assignment checklist and complete work in smaller milestones.")
    if data["study_hours"] < 2:
        tips.append("Try a consistent study routine, starting with focused 25–30 minute sessions.")
    if data["sleep_hours"] < 7:
        tips.append("Consider a more regular sleep schedule; adequate rest supports learning.")
    if data["internet_usage"] > 8:
        tips.append("Review recreational screen time and protect time for study, rest and offline activities.")
    if not tips:
        tips.append("Maintain your current habits and review your progress after the next assessment.")
    tips.append("These are general suggestions, not a guarantee of placement. Use them alongside feedback from teachers and placement staff.")
    return tips
