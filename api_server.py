from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import sys
import logging

# --- Path Configuration ---
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("ProcurementAPI")

from auth_utils import TelegramAuth
from supabase_client import SupabaseManager

# --- Configuration ---
# In a real app, use .env files. For now, using hardcoded values provided by you.
BOT_TOKEN = "8719774319:AAF32nPaw10bPMrfTfEKDyGcTO13U54Mo4c"
SUPABASE_URL = "https://mmsjmkvkytiehqdvsclt.supabase.co"
SUPABASE_KEY = "sb_publishable_yoPhk5ao0u8me4NrxxjY-w_sJTue1iS"

app = FastAPI(title="Procurement Mini App API")

# Allow requests from your GitHub Pages URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vashi-123.github.io", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth = TelegramAuth(BOT_TOKEN)
db = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)

class StatusUpdate(BaseModel):
    sku_id: str
    new_stage: str

@app.get("/api/inventory")
async def get_inventory():
    """Returns the current inventory state from Supabase."""
    logger.info("Fetching inventory data from Supabase")
    data = db.get_inventory()
    if not data:
        return []
    return data

@app.post("/api/update_status")
async def update_status(update: StatusUpdate, x_telegram_init_data: str = Header(None)):
    """
    Securely updates the status of an SKU. 
    """
    if not x_telegram_init_data:
        logger.warning("Attempted status update without Telegram authorization header")
        raise HTTPException(status_code=401, detail="Missing Telegram authorization")

    try:
        # 1. Verify the data comes from Telegram
        user_data = auth.verify_init_data(x_telegram_init_data)
        user_id = user_data.get('id')
        user_name = user_data.get('username') or user_data.get('first_name', 'Unknown')

        if not user_id:
            logger.error("Failed to extract user_id from verified Telegram data")
            raise HTTPException(status_code=401, detail="Invalid user data")

        logger.info(f"User {user_name} (ID: {user_id}) attempting to update SKU {update.sku_id} to {update.new_stage}")

        # 2. Check if user is in the authorized list
        if not db.is_user_authorized(user_id):
            logger.warning(f"ACCESS DENIED: User {user_name} (ID: {user_id}) is not authorized to change statuses.")
            raise HTTPException(status_code=403, detail="У вас нет прав для изменения статуса.")

        # 3. Perform the update and log history
        success = db.update_sku_status(update.sku_id, update.new_stage, user_id)
        
        if not success:
            logger.error(f"Database update failed for SKU {update.sku_id}")
            raise HTTPException(status_code=500, detail="Ошибка при обновлении базы данных")

        logger.info(f"SUCCESS: SKU {update.sku_id} updated to {update.new_stage} by {user_name}")
        return {"status": "success", "message": "Статус обновлен"}

    except ValueError as e:
        logger.warning(f"Auth verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during status update: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
