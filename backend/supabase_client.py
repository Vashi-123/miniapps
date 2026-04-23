from supabase import create_client, Client
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SupabaseManager:
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)

    def get_inventory(self) -> List[Dict]:
        """Fetches the current inventory state from Supabase."""
        try:
            response = self.supabase.table('inventory').select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching inventory: {str(e)}")
            return []

    def is_user_authorized(self, telegram_id: int) -> bool:
        """Checks if a Telegram user is in the authorized_users table."""
        try:
            response = self.supabase.table('authorized_users') \
                .select("telegram_id") \
                .eq("telegram_id", telegram_id) \
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking authorization: {str(e)}")
            return False

    def update_sku_status(self, sku_id: str, new_stage: str, user_id: int) -> bool:
        """
        Updates the status of an SKU and logs the change in history.
        Uses a simple transaction-like logic (fetch current, update, log).
        """
        try:
            # 1. Fetch current stage for history logging
            current_sku = self.supabase.table('inventory') \
                .select("stage") \
                .eq("sku_id", sku_id) \
                .single() \
                .execute()
            
            from_stage = current_sku.data.get('stage') if current_sku.data else 'unknown'

            # 2. Update the status
            self.supabase.table('inventory') \
                .update({"stage": new_stage, "updated_at": "now()"}) \
                .eq("sku_id", sku_id) \
                .execute()

            # 3. Log to history
            self.supabase.table('status_history').insert({
                "sku_id": sku_id,
                "from_stage": from_stage,
                "to_stage": new_stage,
                "changed_by": user_id
            }).execute()

            return True
        except Exception as e:
            logger.error(f"Error updating status for {sku_id}: {str(e)}")
            return False

    def sync_parquet_data(self, df_records: List[Dict]) -> bool:
        """
        Syncs data from analysis script to Supabase.
        Critically, it ensures that if an SKU already exists in a status 
        other than 'needs', it won't be reset or duplicated.
        """
        try:
            for record in df_records:
                sku_id = str(record['id'])
                
                payload = {
                    "sku_id": sku_id,
                    "name": record['name'],
                    "group": record['group'],
                    "qty": record['qty'],
                    "days_left": record['days'],
                    "need": record['need'],
                    "updated_at": "now()"
                }

                # 1. Check if the item already exists
                existing = self.supabase.table('inventory').select("stage").eq("sku_id", sku_id).execute()
                
                if existing.data and len(existing.data) > 0:
                    # It exists. Update quantitative data, but DO NOT touch the stage.
                    # This guarantees it won't be reset to 'needs' or duplicated.
                    self.supabase.table('inventory').update(payload).eq("sku_id", sku_id).execute()
                else:
                    # It's a new item. Insert it with the default 'needs' stage.
                    payload['stage'] = 'needs'
                    self.supabase.table('inventory').insert(payload).execute()
                    
            return True
        except Exception as e:
            logger.error(f"Error syncing parquet data: {str(e)}")
            return False
