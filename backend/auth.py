"""Small dependency-free password hashing and signed bearer-token helpers."""
import base64, hashlib, hmac, json, os, secrets, time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from . import models

SECRET = os.getenv('APP_SECRET_KEY', 'CHANGE_THIS_DEMO_SECRET_BEFORE_DEPLOYMENT')
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    return base64.urlsafe_b64encode(salt).decode() + '$' + base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_s, digest_s = stored.split('$', 1)
        salt = base64.urlsafe_b64decode(salt_s.encode())
        expected = base64.urlsafe_b64decode(digest_s.encode())
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def create_token(user: models.User) -> str:
    now = int(time.time())
    header = _b64(json.dumps({'alg':'HS256','typ':'JWT'}).encode())
    payload = _b64(json.dumps({'sub':user.user_id,'email':user.email,'role':user.role,'iat':now,'exp':now+60*60*12}).encode())
    body = f'{header}.{payload}'
    sig = _b64(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f'{body}.{sig}'

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail='Please log in to continue.')
    try:
        head, payload, signature = credentials.credentials.split('.')
        body = f'{head}.{payload}'
        expected = _b64(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError('signature')
        data = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        if data.get('exp', 0) < int(time.time()): raise ValueError('expired')
        user = db.query(models.User).filter(models.User.user_id == int(data['sub']), models.User.is_active == True).first()
        if not user: raise ValueError('user')
        return user
    except Exception:
        raise HTTPException(status_code=401, detail='Session expired or invalid. Please log in again.')

def require_admin(user: models.User = Depends(current_user)):
    if user.role != 'admin': raise HTTPException(status_code=403, detail='Administrator access required.')
    return user
