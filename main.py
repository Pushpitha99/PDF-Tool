import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import pdf_router, admin_router, auth_router
import database
import traceback

app = FastAPI(
    title="PDF Processing Microservice",
    description="Microservice for PDF processing, meant to be accessed by a PHP/MySQL application.",
    version="1.0.0"
)

@app.on_event("startup")
def on_startup():
    """Initializes MySQL/SQLite database tables and seeds initial user accounts."""
    database.init_db()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch any unhandled exception and return a standard JSON response."""
    import pypdf.errors
    import pikepdf._core
    
    # Check if it's a PDF reading error
    if isinstance(exc, pypdf.errors.PdfReadError) or isinstance(exc, pikepdf._core.PdfError):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid or corrupted PDF file: {str(exc)}"},
        )
        
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )

# Enable CORS for the separate PHP/MySQL application
# Adjust allow_origins in production to strictly allow only the PHP app's origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf_router.router, prefix="/api/v1/pdf", tags=["PDF Processing"])
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["Admin Panel"])
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/admin", tags=["Admin Panel"])
async def serve_admin_panel():
    """Serves the Admin Panel dashboard interface."""
    admin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "admin.html")
    if not os.path.exists(admin_path):
        raise HTTPException(status_code=404, detail="admin.html not found")
    return FileResponse(admin_path)

@app.get("/account", tags=["User Workspace"])
async def serve_account_panel():
    """Serves the User Account Workspace interface."""
    account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "account.html")
    if not os.path.exists(account_path):
        raise HTTPException(status_code=404, detail="account.html not found")
    return FileResponse(account_path)

# Mount frontend static directory
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "PDF Microservice is running"}

if __name__ == "__main__":
    import uvicorn
    # Run the application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
