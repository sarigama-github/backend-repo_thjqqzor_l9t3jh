import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
from database import create_document
from schemas import Lead, Estimate

app = FastAPI(title="AZ Window Services LLC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists and mount static serving
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
def read_root():
    return {"message": "AZ Window Services LLC API running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Lead submit (simple contact form)
@app.post("/api/lead")
def submit_lead(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    service_needed: str = Form(...),
    address: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
):
    lead = Lead(
        name=name,
        email=email,
        phone=phone,
        service_needed=service_needed,
        address=address,
        message=message,
        source="website"
    )
    try:
        inserted_id = create_document("lead", lead)
        return {"success": True, "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Estimate with optional photo uploads
@app.post("/api/estimate")
async def submit_estimate(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    service_needed: str = Form(...),
    address: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    photos: List[UploadFile] = File(default_factory=list)
):
    saved_files: List[str] = []
    for f in photos:
        filename = f.filename
        # create unique filename to avoid collisions
        base, ext = os.path.splitext(filename)
        safe_base = base.replace(" ", "_")[:50]
        unique_name = f"{safe_base}_{os.urandom(4).hex()}{ext}"
        dest_path = os.path.join(UPLOAD_DIR, unique_name)
        content = await f.read()
        with open(dest_path, "wb") as out:
            out.write(content)
        saved_files.append(unique_name)

    estimate = Estimate(
        name=name,
        email=email,
        phone=phone,
        service_needed=service_needed,
        address=address,
        message=message,
        photo_filenames=saved_files,
        source="website"
    )
    try:
        inserted_id = create_document("estimate", estimate)
        return {"success": True, "id": inserted_id, "files": saved_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health route
@app.get("/api/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
