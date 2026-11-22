import json, os, io
from pathlib import Path
import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, inspect, text
from .database import Base, engine, get_db, SessionLocal
from . import models
from .schemas import PredictRequest, RegisterRequest, LoginRequest, ProfileUpdate
from .auth import hash_password, verify_password, create_token, current_user, require_admin
from .recommendations import make_recommendations

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
Base.metadata.create_all(bind=engine)

# Lightweight additive migration for existing project databases.
with engine.begin() as conn:
    cols = {c['name'] for c in inspect(engine).get_columns('students')}
    if 'user_id' not in cols:
        conn.execute(text('ALTER TABLE students ADD COLUMN user_id INTEGER NULL'))

# Create the first administrator from environment variables; never hard-code credentials.
if os.getenv('ADMIN_EMAIL') and os.getenv('ADMIN_PASSWORD'):
    db0 = SessionLocal()
    try:
        email = os.getenv('ADMIN_EMAIL').strip().lower()
        admin = db0.query(models.User).filter(func.lower(models.User.email) == email).first()
        if not admin:
            db0.add(models.User(email=email, password_hash=hash_password(os.getenv('ADMIN_PASSWORD')), role='admin'))
            db0.commit()
    finally: db0.close()

app = FastAPI(title="Student AI Performance & Placement API", version="2.0.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
MODEL_DIR = ROOT / "ml/models"
CLASSIFIER_PATH = MODEL_DIR / "placement_model.joblib"
REGRESSOR_PATH = MODEL_DIR / "score_model.joblib"
META_PATH = MODEL_DIR / "model_metadata.json"
CSV_PATH = ROOT / os.getenv("CSV_PATH", "data/StudentsPerformance.csv")

def model_load(path):
    if not path.exists(): return None
    return joblib.load(path)

def get_student(db: Session, user: models.User):
    student = db.query(models.Student).filter(models.Student.user_id == user.user_id).first()
    if not student:
        student = models.Student(user_id=user.user_id, name=user.email.split('@')[0], email=user.email)
        db.add(student); db.commit(); db.refresh(student)
    return student

def latest_inputs(db, student_id):
    status = db.query(models.ClassStatus).filter_by(student_id=student_id).order_by(desc(models.ClassStatus.created_at)).first()
    academic = db.query(models.AcademicRecord).filter_by(student_id=student_id).order_by(desc(models.AcademicRecord.created_at)).first()
    if not status: return None
    return {"study_hours":status.study_hours,"attendance":status.attendance,"sleep_hours":status.sleep_hours,"internet_usage":status.internet_usage,"assignments_completed":status.assignments_completed,"previous_score":academic.previous_score if academic else 0}

def dataset_stats():
    if not CSV_PATH.exists(): raise HTTPException(404, detail='Training CSV not found.')
    df = pd.read_csv(CSV_PATH)
    score_cols = ['math score','reading score','writing score']
    df['average_score'] = df[score_cols].mean(axis=1)
    return df

@app.get('/')
def root(): return {"message":"Student AI Performance & Placement Prediction API","docs":"/docs"}

@app.get('/api/health')
def health(): return {"status":"ok","classifier_ready":CLASSIFIER_PATH.exists(),"regressor_ready":REGRESSOR_PATH.exists(),"database":"configured"}

@app.post('/api/auth/register')
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.query(models.User).filter(func.lower(models.User.email)==email).first(): raise HTTPException(409, detail='An account with this email already exists.')
    user = models.User(email=email, password_hash=hash_password(payload.password), role='student')
    db.add(user); db.flush()
    student = models.Student(user_id=user.user_id, name=payload.name.strip(), email=email)
    db.add(student); db.commit(); db.refresh(user)
    return {"access_token":create_token(user),"token_type":"bearer","role":user.role,"name":student.name,"email":user.email}

@app.post('/api/auth/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(func.lower(models.User.email)==str(payload.email).lower()).first()
    if not user or not user.is_active or not verify_password(payload.password,user.password_hash): raise HTTPException(401, detail='Incorrect email or password.')
    student = db.query(models.Student).filter_by(user_id=user.user_id).first() if user.role=='student' else None
    return {"access_token":create_token(user),"token_type":"bearer","role":user.role,"name":student.name if student else 'Administrator',"email":user.email}

@app.get('/api/auth/me')
def me(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(user_id=user.user_id).first() if user.role=='student' else None
    return {"user_id":user.user_id,"email":user.email,"role":user.role,"name":student.name if student else 'Administrator'}

@app.put('/api/me/profile')
def update_profile(payload: ProfileUpdate, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != 'student': raise HTTPException(403, detail='Student profile only.')
    student=get_student(db,user); student.name=payload.name.strip(); db.commit()
    return {"student_id":student.student_id,"name":student.name,"email":student.email}

@app.post('/api/predict')
def predict(payload: PredictRequest, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    classifier=model_load(CLASSIFIER_PATH); regressor=model_load(REGRESSOR_PATH)
    if classifier is None: raise HTTPException(503, detail='Placement model missing. Run python ml/train_model.py.')
    student=get_student(db,user)
    data=payload.model_dump(); data['name']=student.name
    if data.get('email') and data['email'].lower()!=user.email.lower(): raise HTTPException(400, detail='Use the email associated with your account.')
    features=pd.DataFrame([{"study_hours":data['study_hours'],"attendance":data['attendance'],"sleep_hours":data['sleep_hours'],"internet_usage":data['internet_usage'],"assignments_completed":data['assignments_completed'],"previous_score":data['previous_score']}])
    regression_features=features.drop(columns=['previous_score'])
    try:
        predicted=str(classifier.predict(features)[0]); probability=None
        if hasattr(classifier,'predict_proba'):
            classes=list(classifier.classes_); positive='Placed' if 'Placed' in classes else classes[-1]
            probability=float(classifier.predict_proba(features)[0][classes.index(positive)])
        score_prediction=float(regressor.predict(regression_features)[0]) if regressor else None
        score_prediction=max(0,min(100,score_prediction)) if score_prediction is not None else None
        academic=models.AcademicRecord(student_id=student.student_id,previous_score=data['previous_score'])
        status=models.ClassStatus(student_id=student.student_id,attendance=data['attendance'],study_hours=data['study_hours'],sleep_hours=data['sleep_hours'],internet_usage=data['internet_usage'],assignments_completed=data['assignments_completed'])
        db.add_all([academic,status])
        metadata=json.loads(META_PATH.read_text(encoding='utf-8')) if META_PATH.exists() else {}
        tips=make_recommendations(data)
        version=metadata.get('model_version','rf-v2')
        pred=models.PlacementPrediction(student_id=student.student_id,predicted_status=predicted,placement_probability=probability,model_version=version,recommendations=json.dumps(tips))
        db.add(pred); db.commit(); db.refresh(pred)
        df=dataset_stats()
        return {"student_id":student.student_id,"prediction_id":pred.prediction_id,"predicted_status":predicted,"placement_probability":probability,"predicted_exam_score":round(score_prediction,1) if score_prediction is not None else None,"score_prediction_reliable":bool(metadata.get("regression",{}).get("metrics",{}).get("r2",-1)>0),"score_prediction_note":metadata.get("regression",{}).get("metrics",{}).get("reliability_note"),"model_version":version,"recommendations":tips,"comparison":{"average_attendance":round(float(df.attendance.mean()),1),"average_score":round(float(df.average_score.mean()),1),"attendance_delta":round(data['attendance']-float(df.attendance.mean()),1),"score_delta":round(data['previous_score']-float(df.average_score.mean()),1)}}
    except HTTPException: raise
    except Exception as exc:
        db.rollback(); raise HTTPException(500,detail=f'Prediction failed: {exc}')

@app.get('/api/me/dashboard')
def student_dashboard(user: models.User=Depends(current_user), db: Session=Depends(get_db)):
    if user.role!='student': raise HTTPException(403,detail='Student access only.')
    student=get_student(db,user)
    predictions=db.query(models.PlacementPrediction).filter_by(student_id=student.student_id).order_by(desc(models.PlacementPrediction.prediction_date)).all()
    status=db.query(models.ClassStatus).filter_by(student_id=student.student_id).order_by(desc(models.ClassStatus.created_at)).first()
    academic=db.query(models.AcademicRecord).filter_by(student_id=student.student_id).order_by(desc(models.AcademicRecord.created_at)).first()
    df=dataset_stats(); avg_att=float(df.attendance.mean()); avg_score=float(df.average_score.mean())
    return {"profile":{"student_id":student.student_id,"name":student.name,"email":student.email},"total_predictions":len(predictions),"latest_prediction":({"status":predictions[0].predicted_status,"probability":predictions[0].placement_probability,"date":predictions[0].prediction_date.isoformat()} if predictions else None),"current":{"attendance":status.attendance if status else None,"study_hours":status.study_hours if status else None,"sleep_hours":status.sleep_hours if status else None,"internet_usage":status.internet_usage if status else None,"assignments_completed":status.assignments_completed if status else None,"score":academic.previous_score if academic else None},"benchmark":{"average_attendance":round(avg_att,1),"average_score":round(avg_score,1),"attendance_delta":round(status.attendance-avg_att,1) if status else None,"score_delta":round(academic.previous_score-avg_score,1) if academic else None},"history":[{"prediction_id":p.prediction_id,"status":p.predicted_status,"probability":p.placement_probability,"date":p.prediction_date.isoformat()} for p in predictions[:10]]}

@app.get('/api/me/report.pdf')
def student_report(user: models.User=Depends(current_user), db: Session=Depends(get_db)):
    if user.role!='student': raise HTTPException(403,detail='Student access only.')
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError: raise HTTPException(503,detail='Install reportlab: pip install reportlab')
    student=get_student(db,user); data=student_dashboard(user,db)
    buff=io.BytesIO(); c=canvas.Canvas(buff,pagesize=A4); width,height=A4; y=height-55
    c.setFont('Helvetica-Bold',19); c.drawString(48,y,'Student Performance Report'); y-=30
    c.setFont('Helvetica',10); c.drawString(48,y,f"Student: {student.name}  |  Email: {student.email}"); y-=24
    c.setFont('Helvetica-Bold',13); c.drawString(48,y,'Current performance'); y-=20
    c.setFont('Helvetica',11)
    current=data['current']; bench=data['benchmark']
    lines=[f"Attendance: {current['attendance'] if current['attendance'] is not None else 'Not available'}% (dataset average {bench['average_attendance']}%)",f"Previous / average score: {current['score'] if current['score'] is not None else 'Not available'} (dataset average {bench['average_score']})",f"Study hours per day: {current['study_hours'] if current['study_hours'] is not None else 'Not available'}",f"Sleep hours per day: {current['sleep_hours'] if current['sleep_hours'] is not None else 'Not available'}",f"Internet usage per day: {current['internet_usage'] if current['internet_usage'] is not None else 'Not available'}",f"Assignments completed: {current['assignments_completed'] if current['assignments_completed'] is not None else 'Not available'}"]
    for line in lines: c.drawString(55,y,line); y-=18
    y-=12; c.setFont('Helvetica-Bold',13); c.drawString(48,y,'Latest placement assessment'); y-=20; c.setFont('Helvetica',11)
    latest=data['latest_prediction']; c.drawString(55,y, f"Result: {latest['status'] if latest else 'No prediction yet'}"); y-=18
    probability_text = f"{latest['probability']*100:.1f}%" if latest and latest['probability'] is not None else 'N/A'
    c.drawString(55,y, f'Model probability: {probability_text}'); y-=28
    c.setFont('Helvetica-Bold',13); c.drawString(48,y,'Interpretation'); y-=20; c.setFont('Helvetica',10)
    c.drawString(55,y,'Comparisons use the supplied training dataset as a benchmark, not a verified classroom cohort.'); y-=16
    c.drawString(55,y,'Predictions are estimates for learning support and are not guarantees of exam or placement outcomes.')
    y-=38; c.setFont('Helvetica-Bold',13); c.drawString(48,y,'Personal vs dataset benchmark'); y-=22
    c.setFont('Helvetica',10)
    for label, own, avg in [('Attendance', current['attendance'], bench['average_attendance']), ('Average score', current['score'], bench['average_score'])]:
        c.drawString(55,y,label); y-=15
        c.setFillColorRGB(0.91,0.92,0.96); c.rect(55,y,300,9,fill=1,stroke=0)
        c.setFillColorRGB(0.31,0.27,0.90); c.rect(55,y,300*max(0,min(100,float(own or 0)))/100,9,fill=1,stroke=0)
        c.setFillColorRGB(0.05,0.62,0.57); c.rect(55,y-4,300*max(0,min(100,float(avg or 0)))/100,3,fill=1,stroke=0)
        c.setFillColorRGB(0.15,0.18,0.23); c.drawString(365,y-1,f'You: {own if own is not None else "N/A"} | Dataset: {avg}'); y-=25
    c.setFont('Helvetica',8); c.setFillColorRGB(0.35,0.38,0.43); c.drawString(55,42,'Purple = your value; teal = dataset average. Dataset benchmark is not a verified class ranking.')
    c.showPage(); c.save(); buff.seek(0)
    return StreamingResponse(buff,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=student-performance-report.pdf'})

@app.get('/api/admin/dashboard')
def admin_dashboard(user: models.User=Depends(require_admin),db: Session=Depends(get_db)):
    total=db.query(func.count(models.Student.student_id)).scalar() or 0
    pred_count=db.query(func.count(models.PlacementPrediction.prediction_id)).scalar() or 0
    placed=db.query(func.count(models.PlacementPrediction.prediction_id)).filter(func.lower(models.PlacementPrediction.predicted_status)=='placed').scalar() or 0
    df=dataset_stats()
    return {"total_students":total,"total_predictions":pred_count,"predicted_placed":placed,"predicted_not_placed":pred_count-placed,"dataset_average_attendance":round(float(df.attendance.mean()),1),"dataset_average_score":round(float(df.average_score.mean()),1),"dataset_rows":len(df)}

@app.get('/api/admin/students')
def admin_students(user: models.User=Depends(require_admin),db: Session=Depends(get_db)):
    rows=db.query(models.Student).order_by(desc(models.Student.created_at)).limit(500).all()
    return [{"student_id":s.student_id,"name":s.name,"email":s.email,"created_at":s.created_at.isoformat(),"predictions":len(s.predictions)} for s in rows]

@app.get('/api/admin/predictions')
def admin_predictions(user: models.User=Depends(require_admin),db: Session=Depends(get_db)):
    rows=db.query(models.PlacementPrediction,models.Student.name).join(models.Student).order_by(desc(models.PlacementPrediction.prediction_date)).limit(100).all()
    return [{"prediction_id":p.prediction_id,"student_id":p.student_id,"name":name,"predicted_status":p.predicted_status,"placement_probability":p.placement_probability,"model_version":p.model_version,"prediction_date":p.prediction_date.isoformat()} for p,name in rows]

@app.get('/api/analytics/eda')
def eda(user: models.User=Depends(current_user)):
    df=dataset_stats(); score_bins=pd.cut(df.average_score,bins=[-1,39,49,59,69,79,89,100],labels=['0–39','40–49','50–59','60–69','70–79','80–89','90–100'])
    att_bins=pd.cut(df.attendance,bins=[-1,49,59,69,79,89,100],labels=['0–49','50–59','60–69','70–79','80–89','90–100'])
    return {"dataset_rows":len(df),"average_attendance":round(float(df.attendance.mean()),2),"average_score":round(float(df.average_score.mean()),2),"average_study_hours":round(float(df.study_hours.mean()),2),"attendance_distribution":df.assign(attendance_band=att_bins).groupby('attendance_band',observed=False).size().reset_index(name='students').to_dict(orient='records'),"score_distribution":df.assign(score_band=score_bins).groupby('score_band',observed=False).size().reset_index(name='students').to_dict(orient='records'),"attendance_vs_score":df[['attendance','average_score']].to_dict(orient='records'),"subject_averages":[{"subject":"Math","average":round(float(df['math score'].mean()),1)},{"subject":"Reading","average":round(float(df['reading score'].mean()),1)},{"subject":"Writing","average":round(float(df['writing score'].mean()),1)}],"historical_placement_distribution":df.placement_status.value_counts().rename_axis('status').reset_index(name='students').to_dict(orient='records')}

@app.get('/ml-metadata')
def ml_metadata(user: models.User=Depends(current_user)):
    if not META_PATH.exists(): raise HTTPException(404,detail='Train the models first.')
    return json.loads(META_PATH.read_text(encoding='utf-8'))
