import os
import jwt
import datetime
import httpx
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# APNI DETAILS YAHAN BHARO
# ==========================================
SUPABASE_URL = "https://suovzjsspybmnzibjdfl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1b3Z6anNzcHlibW56aWJqZGZsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NTIwMTM4MiwiZXhwIjoyMTAwNzc3MzgyfQ.a7mtyL1_GS_i4qxlR_WA8nkkYstSZl9Nqubh35_H-zM"

CLOUDINARY_CLOUD_NAME = "v6zjcchy"
CLOUDINARY_API_KEY = "969744767144196"
CLOUDINARY_API_SECRET = "XUy8uJrnRp4smbp_W3HtwIqqI94"
# ==========================================

cloudinary.config( 
  cloud_name = CLOUDINARY_CLOUD_NAME, 
  api_key = CLOUDINARY_API_KEY, 
  api_secret = CLOUDINARY_API_SECRET 
)

SECRET_KEY = "super-secret-rakhi-key-change-in-production"
ADMIN_PASSCODE = "admin123"

security = HTTPBearer()
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

class LoginModel(BaseModel):
    passcode: str

@app.post("/api/admin/login")
def admin_login(data: LoginModel):
    if data.passcode == ADMIN_PASSCODE:
        expire = datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        token = jwt.encode({"exp": expire}, SECRET_KEY, algorithm="HS256")
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Incorrect passcode")

@app.get("/api/products")
async def get_products():
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/products?order=id.desc", headers=headers)
        products = []
        for p in resp.json():
            products.append({
                "id": p["id"], "name": p["name"], "price": p["price"], "mrp": p["mrp"] if p["mrp"] else 0,
                "tag": p["tag"] if p["tag"] else "", "image_url": p["image_url"] if p["image_url"] else None,
                "rating": p["rating"] if p["rating"] else 5.0, "reviews": p["reviews"] if p["reviews"] else 0,
                "stock": p["stock"] if p["stock"] is not None else 999
            })
        return products

@app.post("/api/products")
async def add_product(
    name: str = Form(...),
    price: float = Form(...),
    mrp: float = Form(0),
    tag: str = Form(None),
    stock: int = Form(999),
    file: UploadFile = File(None),
    _: bool = Depends(verify_token)
):
    image_url = None
    if file:
        upload_result = cloudinary.uploader.upload(file.file)
        image_url = upload_result.get("secure_url")

    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    data = {
        "name": name, "price": price, "mrp": mrp, "tag": tag,
        "image_url": image_url, "rating": 5.0, "reviews": 0, "stock": stock
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SUPABASE_URL}/rest/v1/products", headers=headers, json=data)
        new_prod = resp.json()[0]
    
    return {
        "id": new_prod["id"], "name": new_prod["name"], "price": new_prod["price"], 
        "mrp": new_prod["mrp"], "tag": new_prod["tag"], "image_url": new_prod["image_url"], 
        "rating": 5.0, "reviews": 0, "stock": new_prod["stock"]
    }

@app.delete("/api/products/{prod_id}")
async def delete_product(prod_id: int, _: bool = Depends(verify_token)):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient() as client:
        await client.delete(f"{SUPABASE_URL}/rest/v1/products?id=eq.{prod_id}", headers=headers)
    return {"detail": "Deleted"}

@app.get("/api/settings/logo")
async def get_logo():
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/settings?key=eq.logo_url", headers=headers)
        if resp.json():
            return {"logo_url": resp.json()[0]["value"]}
    return {"logo_url": None}

@app.post("/api/settings/logo")
async def upload_logo(file: UploadFile = File(...), _: bool = Depends(verify_token)):
    upload_result = cloudinary.uploader.upload(file.file)
    logo_url = upload_result.get("secure_url")

    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "upsert=representation"}
    data = {"key": "logo_url", "value": logo_url}
    async with httpx.AsyncClient() as client:
        await client.post(f"{SUPABASE_URL}/rest/v1/settings", headers=headers, json=data)
    return {"logo_url": logo_url}

@app.delete("/api/settings/logo")
async def delete_logo(_: bool = Depends(verify_token)):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient() as client:
        await client.delete(f"{SUPABASE_URL}/rest/v1/settings?key=eq.logo_url", headers=headers)
    return {"detail": "Logo reset"}
