import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import json

load_dotenv(override=True)
api_key = os.environ.get("BirdEyeApi")

def get_historical_prices(
    address: str,
    time_from: int,
    time_to: int,
    address_type: str = "token",
    interval_type: str = "12H",
    chain: str = 'solana',
    currency: str = 'USD',
    cache_file: str = 'token_price_history.json'
) -> list:
    """
    Fetch historical token prices from BirdEye API
    Args:
        address: Token contract address
        address_type: Type of address (typically 'token')
        interval_type: OHLCV interval (e.g., '15m', '1h', '4h')
        time_from: Start timestamp (Unix seconds)
        time_to: End timestamp (Unix seconds)
        api_key: BirdEye API key
        chain: Blockchain network (default: 'solana')
        currency: Currency symbol to append to price (default: 'USD')
        cache_file: Path to cache file (default: 'token_price_history.json')
    
    Returns:
        List of formatted price entries with datetime and price
    """
    # Generate unique cache key
    cache_key = f"{address}-{address_type}-{interval_type}-{time_from}-{time_to}-{chain}-{currency}"
    
    # Load cache
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            pass

    # Cache check logic
    if cache_key in cache:
        cache_entry = cache[cache_key]
        cache_age = datetime.now() - datetime.fromisoformat(cache_entry['fetch_time'])
        
        if cache_age <= timedelta(hours=3):
            # Return False if cached items are empty
            if not cache_entry['items']:
                return False
            return {
                'token': address,
                'fetch_time': cache_entry['fetch_time'],
                'history': cache_entry['items']
            }

    # API call when no valid cache exists
    url = 'https://public-api.birdeye.so/defi/history_price'
    params = {
        'address': address,
        'address_type': address_type,
        'type': interval_type,
        'time_from': time_from,
        'time_to': time_to
    }
    headers = {
        'accept': 'application/json',
        'x-chain': chain,
        'X-API-KEY': api_key
    }

    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        raise Exception(f'API request failed: {response.status_code} - {response.text}')

    data = response.json()
    # Return False for unsuccessful requests or missing items
    if not data.get('success') or not data.get('data', {}).get('items'):
        return False

    # Process results
    fetch_time = datetime.now().isoformat()
    formatted = []
    for item in data['data']['items']:
        dt = datetime.fromtimestamp(item['unixTime'])
        formatted.append({
            'time': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': item['unixTime'],
            'price': f"{item['value']:.4f} {currency}"
        })

    # Return False if no formatted results
    if not formatted:
        return False

    # Update cache
    cache[cache_key] = {
        'fetch_time': fetch_time,
        'items': formatted
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)

    # Return final response
    return {
        'token': address,
        'fetch_time': fetch_time,
        'history': formatted
    }


if __name__ == "__main__":
    prices = get_historical_prices(
    address="CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump",
    address_type='token',
    time_from=1737772532,
    time_to=1738647000,
    interval_type='12H',
    api_key=api_key)

    print(json.dumps(prices, indent=2))
    print("updated")
