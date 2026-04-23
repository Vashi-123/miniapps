import hmac
import hashlib
from urllib.parse import parse_qsl
import json
import logging

logger = logging.getLogger(__name__)

class TelegramAuth:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    def verify_init_data(self, init_data: str) -> dict:
        """
        Verifies the integrity of the data received from the Telegram Mini App.
        Returns the user data if valid, raises ValueError otherwise.
        """
        try:
            # 1. Parse the query string
            vals = dict(parse_qsl(init_data))
            hash_val = vals.pop('hash', None)
            if not hash_val:
                raise ValueError("Missing hash in initData")

            # 2. Sort key-value pairs alphabetically
            data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(vals.items())])

            # 3. Create secret key using bot_token
            secret_key = hmac.new(b"WebAppData", self.bot_token.encode(), hashlib.sha256).digest()

            # 4. Calculate HMAC-SHA256 signature
            computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

            # 5. Compare signatures
            if computed_hash != hash_val:
                logger.warning(f"Hash mismatch: computed={computed_hash}, received={hash_val}")
                raise ValueError("Invalid hash: data integrity check failed")

            # 6. Parse the 'user' field
            if 'user' in vals:
                return json.loads(vals['user'])
            
            return {}

        except Exception as e:
            logger.error(f"Error verifying telegram data: {str(e)}")
            raise ValueError(f"Verification failed: {str(e)}")
