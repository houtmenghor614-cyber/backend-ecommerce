from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserResponse
from auth import create_access_token, get_current_user
from config import Config
import requests

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.get("/google/login")
async def google_login():
    """Redirect to Google login page"""
    redirect_uri = Config.GOOGLE_REDIRECT_URI
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={Config.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&access_type=online"
    )
    return RedirectResponse(url=google_auth_url)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Get authorization code
        code = request.query_params.get('code')
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not found")
        
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': Config.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f"Bearer {token_json['access_token']}"}
        user_response = requests.get(userinfo_url, headers=headers)
        user_data = user_response.json()
        
        if not user_data or 'email' not in user_data:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        # Extract user data
        google_id = user_data.get('sub')
        email = user_data.get('email')
        full_name = user_data.get('name', email.split('@')[0])
        picture = user_data.get('picture')
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Update existing user
            user.google_id = google_id
            user.full_name = full_name
            user.picture = picture
            user.is_google_user = True
            db.commit()
            db.refresh(user)
        else:
            # Create new user
            user = User(
                full_name=full_name,
                email=email,
                google_id=google_id,
                picture=picture,
                phone_number=None,
                password_hash=None,
                is_google_user=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(data={"sub": user.id, "email": user.email})
        
        # Redirect to frontend
        frontend_url = f"http://localhost:3000/auth/google/callback?token={access_token}&user_id={user.id}&name={full_name}&email={email}&picture={picture}"
        
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google login failed: {str(e)}")

@router.post("/google/logout")
async def google_logout():
    """Logout user"""
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user