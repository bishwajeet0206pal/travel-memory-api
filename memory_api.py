# memory_api.py
# Simple Memory API for LangFlow Cloud
# Deploy this to Render (free tier)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

app = FastAPI(title="Travel Memory API", version="1.0.0")

# Enable CORS for LangFlow Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (Phase 1 MVP - later move to real DB)
user_profiles = {}
sessions = {}

# Models
class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    budget_style: Optional[str] = None  # 'always_budget' | 'mid_range' | 'luxury' | 'mixed'
    preferred_transport: Optional[str] = None  # 'train' | 'flight' | 'bus'
    no_early_flights: bool = False
    no_late_nights: bool = False
    walking_tolerance: Optional[str] = None  # 'low' | 'medium' | 'high'
    food_preferences: List[str] = []
    transport_dislikes: List[str] = []
    accommodation_dislikes: List[str] = []
    typical_hotel_budget: Optional[int] = None
    total_trips_booked: int = 0

class TripSlots(BaseModel):
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    companions: Optional[str] = None
    budget_level: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    intent: Optional[str] = None
    constraints: List[str] = []

class SessionState(BaseModel):
    session_id: str
    user_id: str
    trip_slots: TripSlots = TripSlots()
    clarifier_count: int = 0
    conversation_stage: str = "clarifying"

class Assumption(BaseModel):
    text: str
    source: str

# Initialize with sample data
def init_sample_data():
    """Create sample user for testing"""
    user_profiles["user_demo_123"] = {
        "user_id": "user_demo_123",
        "name": "Rahul Kumar",
        "budget_style": "always_budget",
        "preferred_transport": "train",
        "no_early_flights": True,
        "no_late_nights": False,
        "walking_tolerance": "medium",
        "food_preferences": ["vegetarian"],
        "transport_dislikes": ["overnight_bus"],
        "accommodation_dislikes": ["shared_bathroom"],
        "typical_hotel_budget": 1200,
        "total_trips_booked": 5
    }

# Initialize on startup
init_sample_data()

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Travel Memory API",
        "version": "1.0.0",
        "endpoints": {
            "profile": "GET /profile/{user_id}",
            "assumptions": "GET /profile/{user_id}/assumptions",
            "update_profile": "POST /profile/{user_id}",
            "session": "GET/POST /session/{session_id}"
        }
    }

# Endpoint 1: Get User Profile
@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """
    Get user profile by ID
    Returns default profile if user doesn't exist
    """
    if user_id not in user_profiles:
        # Return default profile for new users
        default_profile = {
            "user_id": user_id,
            "name": None,
            "budget_style": "mixed",
            "preferred_transport": None,
            "no_early_flights": False,
            "no_late_nights": False,
            "walking_tolerance": "medium",
            "food_preferences": [],
            "transport_dislikes": [],
            "accommodation_dislikes": [],
            "typical_hotel_budget": None,
            "total_trips_booked": 0
        }
        return default_profile
    
    return user_profiles[user_id]

# Endpoint 2: Update User Profile
@app.post("/profile/{user_id}")
async def update_profile(user_id: str, profile: UserProfile):
    """
    Create or update user profile
    """
    user_profiles[user_id] = profile.dict()
    return {
        "status": "success",
        "message": "Profile saved",
        "user_id": user_id
    }

# Endpoint 3: Get Assumptions for Display
@app.get("/profile/{user_id}/assumptions")
async def get_assumptions(user_id: str):
    """
    Convert profile to displayable assumptions
    Returns formatted text for showing to user
    """
    profile = await get_profile(user_id)
    assumptions = []
    
    # Transport timing
    if profile.get("no_early_flights"):
        assumptions.append({
            "text": "I'll avoid early morning departures",
            "source": "profile_preference"
        })
    
    if profile.get("no_late_nights"):
        assumptions.append({
            "text": "I'll avoid late night travel",
            "source": "profile_preference"
        })
    
    # Transport preference
    if profile.get("preferred_transport"):
        assumptions.append({
            "text": f"Prioritizing {profile['preferred_transport']} when possible",
            "source": "profile_preference"
        })
    
    # Budget style
    budget_style = profile.get("budget_style")
    if budget_style == "always_budget":
        assumptions.append({
            "text": "Budget hotels (₹800-1500/night)",
            "source": "profile_preference"
        })
    elif budget_style == "mid_range":
        assumptions.append({
            "text": "Mid-range hotels (₹2000-4000/night)",
            "source": "profile_preference"
        })
    elif budget_style == "luxury":
        assumptions.append({
            "text": "Premium hotels (₹5000+/night)",
            "source": "profile_preference"
        })
    
    # Walking tolerance
    walking = profile.get("walking_tolerance")
    if walking == "low":
        assumptions.append({
            "text": "Minimizing walking (max 2km/day)",
            "source": "profile_preference"
        })
    elif walking == "high":
        assumptions.append({
            "text": "Comfortable with long walks (5-8km/day)",
            "source": "profile_preference"
        })
    
    # Food preferences
    food_prefs = profile.get("food_preferences", [])
    if food_prefs:
        assumptions.append({
            "text": f"Food preferences: {', '.join(food_prefs)}",
            "source": "profile_preference"
        })
    
    # Transport dislikes
    transport_dislikes = profile.get("transport_dislikes", [])
    if transport_dislikes:
        assumptions.append({
            "text": f"Avoiding: {', '.join(transport_dislikes)}",
            "source": "profile_preference"
        })
    
    # Format for LangFlow consumption
    if assumptions:
        formatted_text = "\n".join([f"• {a['text']}" for a in assumptions])
        return {
            "user_id": user_id,
            "has_assumptions": True,
            "count": len(assumptions),
            "assumptions": assumptions,
            "formatted_text": formatted_text
        }
    else:
        return {
            "user_id": user_id,
            "has_assumptions": False,
            "count": 0,
            "assumptions": [],
            "formatted_text": "No previous preferences found. Let's start fresh!"
        }

# Endpoint 4: Create/Update Session
@app.post("/session")
async def update_session(session: SessionState):
    """
    Create or update conversation session
    """
    sessions[session.session_id] = session.dict()
    return {
        "status": "success",
        "message": "Session saved",
        "session_id": session.session_id
    }

# Endpoint 5: Get Session
@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get conversation session by ID
    Returns empty session if doesn't exist
    """
    if session_id not in sessions:
        return {
            "session_id": session_id,
            "user_id": None,
            "trip_slots": {},
            "clarifier_count": 0,
            "conversation_stage": "clarifying"
        }
    
    return sessions[session_id]

# Endpoint 6: Update Trip Slots
@app.post("/session/{session_id}/slots")
async def update_trip_slots(session_id: str, slots: Dict[str, Any]):
    """
    Update trip slots in session
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    session["trip_slots"].update(slots)
    sessions[session_id] = session
    
    return {
        "status": "success",
        "session_id": session_id,
        "updated_slots": slots
    }

# Endpoint 7: List All Users (for debugging)
@app.get("/debug/users")
async def list_users():
    """
    Debug endpoint: list all stored users
    """
    return {
        "count": len(user_profiles),
        "users": list(user_profiles.keys())
    }

# Endpoint 8: Clear All Data (for testing)
@app.post("/debug/reset")
async def reset_data():
    """
    Debug endpoint: reset all data and reinitialize sample
    """
    user_profiles.clear()
    sessions.clear()
    init_sample_data()
    return {
        "status": "success",
        "message": "All data reset, sample user restored"
    }

# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "users_count": len(user_profiles),
        "sessions_count": len(sessions)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
