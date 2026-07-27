import os
import sqlite3
import jwt
import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()

# Allow your frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images so the frontend can display them
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

DB_NAME = "rakhi_vaibhav.db"
SECRET_KEY = "super-secret-rakhi-key-change-in-production"
ADMIN_PASSCODE = "admin123" # Change this to your desired admin passcode

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, mrp REAL,
                  tag TEXT, image_url TEXT, rating REAL, reviews INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # Seed default products if empty
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        default_products = [
            ("Rudraksha Premium Rakhi", 299, 499, "Bestseller", None, 4.8, 125),
            ("Silver Om Rakhi", 599, 799, "Premium", None, 4.9, 89),
            ("Kids Superhero Rakhi", 199, 249, "Kids", None, 4.5, 210),
            ("Kundan Designer Rakhi", 449, 599, "New", None, 4.7, 56)
        ]
        c.executemany("INSERT INTO products (name, price, mrp, tag, image_url, rating, reviews) VALUES (?,?,?,?,?,?,?)", default_products)
    conn.commit()
    conn.close()

init_db()

# --- Auth Security ---
security = HTTPBearer()
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --- Models ---
class LoginModel(BaseModel):
    passcode: str

# --- API Endpoints ---

@app.post("/api/admin/login")
def admin_login(data: LoginModel):
    if data.passcode == ADMIN_PASSCODE:
        expire = datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        token = jwt.encode({"exp": expire}, SECRET_KEY, algorithm="HS256")
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Incorrect passcode")

@app.get("/api/products")
def get_products():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, price, mrp, tag, image_url, rating, reviews FROM products ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    
    products = []
    for row in rows:
        products.append({
            "id": row[0], "name": row[1], "price": row[2], "mrp": row[3],
            "tag": row[4], "image_url": row[5], "rating": row[6], "reviews": row[7]
        })
    return products

@app.post("/api/products")
async def add_product(
    name: str = Form(...),
    price: float = Form(...),
    mrp: float = Form(0),
    tag: str = Form(None),
    file: UploadFile = File(None),
    _: bool = Depends(verify_token)
):
    image_url = None
    if file:
        file_location = f"uploads/{file.filename}"
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())
        image_url = f"/uploads/{file.filename}"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, mrp, tag, image_url, rating, reviews) VALUES (?,?,?,?,?,?,?)",
              (name, price, mrp, tag, image_url, 5.0, 0))
    conn.commit()
    prod_id = c.lastrowid
    conn.close()

    return {
        "id": prod_id, "name": name, "price": price, "mrp": mrp,
        "tag": tag, "image_url": image_url, "rating": 5.0, "reviews": 0
    }

@app.delete("/api/products/{prod_id}")
def delete_product(prod_id: int, _: bool = Depends(verify_token)):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (prod_id,))
    conn.commit()
    conn.close()
    return {"detail": "Deleted"}

# --- Settings (Logo) Endpoints ---
@app.get("/api/settings/logo")
def get_logo():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='logo_url'")
    row = c.fetchone()
    conn.close()
    return {"logo_url": row[0] if row else None}

@app.post("/api/settings/logo")
async def upload_logo(file: UploadFile = File(...), _: bool = Depends(verify_token)):
    file_location = f"uploads/logo_{file.filename}"
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())
    logo_url = f"/uploads/logo_{file.filename}"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('logo_url', ?)", (logo_url,))
    conn.commit()
    conn.close()

    return {"logo_url": logo_url}

@app.delete("/api/settings/logo")
def delete_logo(_: bool = Depends(verify_token)):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM settings WHERE key='logo_url'")
    conn.commit()
    conn.close()
    return {"detail": "Logo reset"}