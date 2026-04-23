import requests
import logging
import sys
import os

# Добавляем путь к папке backend, чтобы скрипт видел supabase_client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import SupabaseManager
import argparse

logger = logging.getLogger(__name__)

# --- Configuration ---
# You can replace these with environment variables in a production setup
BOT_TOKEN = "8719774319:AAF32nPaw10bPMrfTfEKDyGcTO13U54Mo4c"
CHAT_IDS = ["198799905", "8513763454"]
SUPABASE_URL = "https://mmsjmkvkytiehqdvsclt.supabase.co"
SUPABASE_KEY = "sb_publishable_yoPhk5ao0u8me4NrxxjY-w_sJTue1iS"
MINI_APP_URL = "https://vashi-123.github.io/miniapps/" # Update if different

def send_telegram_message(text: str):
    """Sends an HTML formatted message via Telegram Bot API to multiple users."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    for chat_id in CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print(f"✅ Telegram notification sent successfully to {chat_id}!")
        except Exception as e:
            print(f"❌ Failed to send Telegram notification to {chat_id}: {e}")

def main():
    print("🔄 Checking Supabase for SKUs that need purchasing...")
    db = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Fetch inventory
    inventory = db.get_inventory()
    
    # 2. Count SKUs in "needs" stage
    needs_count = sum(1 for item in inventory if item.get('stage') == 'needs')
    
    # 3. Format message
    if needs_count > 0:
        message = (
            "🚨 <b>Сток обновлен!</b>\n\n"
            f"У вас <b>{needs_count} SKU</b>, которые нужно закупить.\n\n"
            f"🔗 Откройте Mini App для управления статусами:\n{MINI_APP_URL}"
        )
    else:
        message = (
            "✅ <b>Сток обновлен!</b>\n\n"
            "Все необходимые закупки сделаны или находятся в статусе ожидания. Сегодня закупать ничего не нужно.\n\n"
            f"🔗 Открыть Mini App:\n{MINI_APP_URL}"
        )
        
    print(f"📦 Needs count: {needs_count}")
    
    # 4. Send message
    send_telegram_message(message)

if __name__ == "__main__":
    main()
