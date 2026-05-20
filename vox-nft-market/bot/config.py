import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

DB_PATH = os.getenv("DB_PATH", "vox_nft.db")

NFT_RECEIVER_USERNAME = os.getenv("NFT_RECEIVER_USERNAME", "VoxManagerNFT")

EVALUATION_PERCENT = float(os.getenv("EVALUATION_PERCENT", "85"))

CURRENCY_API_URL = "https://api.coingecko.com/api/v3/simple/price"

GETGEMS_GRAPHQL_URL = "https://api.getgems.io/graphql"

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "10"))
CHECK_TIMEOUT_SECONDS = int(os.getenv("CHECK_TIMEOUT_SECONDS", "600"))
