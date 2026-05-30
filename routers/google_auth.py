from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from database import get_db
from models import User
from auth import create_access_token
from config import Config as AppConfig
import os

router = APIRouter(prefix="/api/auth", tags=["Google Auth"])

# OAuth Configuration
oauth_config = Config(os.environ)
oauth = OAuth(oauth_config)

google = oauth.register(
    name='google',
    client_id=AppConfig.GOOGLE_CLIENT_ID,
    client_secret=AppConfig.GOOGLE_CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
)

@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google login page"""
    redirect_uri = AppConfig.GOOGLE_REDIRECT_URI
    return await google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Get user info from Google
        token = await google.authorize_access_token(request)
        user_info = await google.parse_id_token(request, token)
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        # Extract user data from Google
        google_id = user_info.get('sub')
        email = user_info.get('email')
        full_name = user_info.get('name')
        picture = user_info.get('picture')
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # User exists - update last login
            user.google_id = google_id
            user.full_name = full_name
            user.picture = picture
            db.commit()
            db.refresh(user)
        else:
            # Create new user
            user = User(
                full_name=full_name,
                email=email,
                google_id=google_id,
                picture=picture,
                phone_number=f"google_{google_id[:10]}",  # Placeholder
                password_hash="google_oauth_user",  # Placeholder
                is_google_user=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(data={"sub": user.id, "email": user.email})
        
        # Redirect to frontend with token
        frontend_url = f"http://localhost:3000/auth/google/callback?token={access_token}&user_id={user.id}&name={full_name}&email={email}"
        
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google login failed: {str(e)}")

@router.post("/google/logout")
async def google_logout(request: Request):
    """Logout user - clear session"""
    request.session.clear()
    return {"message": "Logged out successfully"}