# config/remote_db.py.example
# Remote database endpoint configuration for 5 converters
# TEMPLATE FILE - Copy to remote_db.py and fill in real credentials

# N01 - ConverterBAT - API Credentials
CONVERTER_BAT_ID = "YOUR_CONVERTER_BAT_ID_HERE"
CONVERTER_BAT_TOKEN = "YOUR_CONVERTER_BAT_TOKEN_HERE"
CONVERTER_BAT_ENDPOINT = f"https://{CONVERTER_BAT_ID}:{CONVERTER_BAT_TOKEN}@shift2dc.prsma.com/api/json/converters"

# N02 - ConverterPV - API Credentials
CONVERTER_PV_ID = "YOUR_CONVERTER_PV_ID_HERE"
CONVERTER_PV_TOKEN = "YOUR_CONVERTER_PV_TOKEN_HERE"
CONVERTER_PV_ENDPOINT = f"https://{CONVERTER_PV_ID}:{CONVERTER_PV_TOKEN}@shift2dc.prsma.com/api/json/converters"

# N03 - ConverterEV1 - API Credentials
CONVERTER_EV1_ID = "YOUR_CONVERTER_EV1_ID_HERE"
CONVERTER_EV1_TOKEN = "YOUR_CONVERTER_EV1_TOKEN_HERE"
CONVERTER_EV1_ENDPOINT = f"https://{CONVERTER_EV1_ID}:{CONVERTER_EV1_TOKEN}@shift2dc.prsma.com/api/json/converters"

# N04 - ConverterEV2 - API Credentials
CONVERTER_EV2_ID = "YOUR_CONVERTER_EV2_ID_HERE"
CONVERTER_EV2_TOKEN = "YOUR_CONVERTER_EV2_TOKEN_HERE"
CONVERTER_EV2_ENDPOINT = f"https://{CONVERTER_EV2_ID}:{CONVERTER_EV2_TOKEN}@shift2dc.prsma.com/api/json/converters"

# N05 - ConverterACDC - API Credentials
CONVERTER_ACDC_ID = "YOUR_CONVERTER_ACDC_ID_HERE"
CONVERTER_ACDC_TOKEN = "YOUR_CONVERTER_ACDC_TOKEN_HERE"
CONVERTER_ACDC_ENDPOINT = f"https://{CONVERTER_ACDC_ID}:{CONVERTER_ACDC_TOKEN}@shift2dc.prsma.com/api/json/converters"

# Map node IDs to their endpoints
ENDPOINTS = {
    "N01": CONVERTER_BAT_ENDPOINT,    # ConverterBAT
    "N02": CONVERTER_PV_ENDPOINT,     # ConverterPV
    "N03": CONVERTER_EV1_ENDPOINT,    # ConverterEV1
    "N04": CONVERTER_EV2_ENDPOINT,    # ConverterEV2
    "N05": CONVERTER_ACDC_ENDPOINT,   # ConverterACDC
}

# Data forwarding settings
AGGREGATION_PERIOD = 30.0   # Seconds to aggregate data before sending (30s average)
RETRY_ATTEMPTS = 3          # Number of retry attempts on failure
RETRY_DELAY = 2.0           # Seconds between retries
REQUEST_TIMEOUT = 10.0      # HTTP request timeout in seconds

