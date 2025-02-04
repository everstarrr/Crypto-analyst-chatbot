from datetime import datetime, timezone, timedelta
from io import StringIO
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv(override=True)


def get_time_ago(timestamp):
   
    now = datetime.now(timezone.utc)
    dt = datetime.fromtimestamp(timestamp, timezone.utc)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    intervals = [
        ('year', seconds / (365.242199 * 24 * 60 * 60)),
        ('month', seconds / (30.44 * 24 * 60 * 60)),
        ('day', seconds / (24 * 60 * 60)),
        ('hour', seconds / (60 * 60)),
        ('minute', seconds / 60),
        ('second', seconds)
    ]
    
    for name, count in intervals:
        if count >= 1:
            count = int(count)
            return f"{count} {name}{'s' if count > 1 else ''} ago"
    
    return "just now"

def get_coin_data(contract_address, asset_platform_id='solana', cache_file='coin_data_cache.json'):
    """Retrieve coin data with caching using Helius API"""
    api_key = os.environ.get("HeliusApi")
    cache_key = f"{asset_platform_id}-{contract_address}"
    
    # Load coin cache
    coin_cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                coin_cache = json.load(f)
        except json.JSONDecodeError:
            pass

    # Check cache validity (60 seconds as per API docs)
    if cache_key in coin_cache:
        cache_entry = coin_cache[cache_key]
        cache_age = datetime.now() - datetime.fromisoformat(cache_entry['fetch_time'])
        
        if cache_age <= timedelta(seconds=60):
            return cache_entry['data']

    # Helius API call for fresh data
    url = "https://mainnet.helius-rpc.com/?api-key=" + api_key
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "getAsset",
        "params": {
            "id": contract_address
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 404:
            print(f"Token not found: {contract_address}")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        # Extract relevant fields from Helius response
        token_info = data.get('result', {}).get('token_info', {})
        price_info = token_info.get('price_info', {})
        
        coin_data = {
            'name': data.get('result', {}).get('content', {}).get('metadata', {}).get('name', 'Unknown'),
            'symbol': token_info.get('symbol', '').upper(),
            'current_price': price_info.get('price_per_token'),
            'web_slug': None,  # Not available in Helius response
            'asset_platform_id': 'solana'  # Hardcoded since we're using Solana
        }
        
        # Update cache
        coin_cache[cache_key] = {
            'fetch_time': datetime.now().isoformat(),
            'data': coin_data
        }
        
        with open(cache_file, 'w') as f:
            json.dump(coin_cache, f, indent=2)
            
        return coin_data
        
    except requests.exceptions.RequestException as e:
        print(f"Helius API error: {str(e)}")
        return None

def analyze_swap_transactions(transactions, wallet_address):
    print(f"Analyzing {len(transactions)} raw transactions")  # Debug 1
    
    swap_transactions = []
    swap_count = 0  # Debug counter

    for tx in transactions:
        # Debug: Print transaction type for first 5 transactions
        if swap_count < 5:
            print(f"Transaction type: {tx.get('type')}, Source: {tx.get('source')}")

        if tx.get('type', '').upper() != 'SWAP':
            continue
            
        swap_count += 1
        actual_time_stamp = tx.get('timestamp')
        if not actual_time_stamp:
            print(f"Missing timestamp in transaction: {tx.get('signature')}")
            continue
        time_ago = get_time_ago(tx['timestamp'])
        source = tx.get('source', 'Unknown')
        
        token_inputs = []
        token_outputs = []
        
        # Check native SOL transfers
        swap_events = tx.get('events', {}).get('swap', {})
        
        # Handle nativeInput
        if swap_events.get('nativeInput') is not None:
            amount_in = float(swap_events['nativeInput']['amount']) / 1e9
            token_inputs.append({
                'symbol': 'SOL',
                'address': 'So11111111111111111111111111111111111111112',
                'amount': amount_in
            })
            
        # Handle nativeOutput
        if swap_events.get('nativeOutput') is not None:
            amount_out = float(swap_events['nativeOutput']['amount']) / 1e9
            token_outputs.append({
                'symbol': 'SOL',
                'address': 'So11111111111111111111111111111111111111112',
                'amount': amount_out
            })

        # Process token transfers
        for transfer in tx.get('tokenTransfers', []):
            amount = float(transfer['tokenAmount'])
            mint = transfer.get('mint', 'Unknown Token')
            
            # Get coin metadata
            coin_data = get_coin_data(mint)
            
            token_entry = {
                'symbol': coin_data['symbol'] if coin_data else mint,
                'address': mint,
                'amount': amount,
                'name': coin_data['name'] if coin_data else 'Unknown Token',
                'current_price': coin_data['current_price'] if coin_data else None
            }
            
            if transfer['fromUserAccount'] == wallet_address:
                token_inputs.append(token_entry)
            elif transfer['toUserAccount'] == wallet_address:
                token_outputs.append(token_entry)

        if token_inputs or token_outputs:
            transaction_details = {
                'time_ago': time_ago,
                'timestamp': actual_time_stamp,
                'time': datetime.fromtimestamp(actual_time_stamp).strftime("%Y-%m-%d %H:%M:%S"),
                'source': source,
                'description': tx.get('description', 'No description available'),
                'sold_tokens': token_inputs,
                'bought_tokens': token_outputs
            }

            # Calculate price if there's one input and one output
            if len(token_inputs) == 1 and len(token_outputs) == 1:
                price = token_inputs[0]['amount'] / token_outputs[0]['amount']
                transaction_details['price'] = {
                    'ratio': f"1 {token_outputs[0]['symbol']} = {price:.6f} {token_inputs[0]['symbol']}",
                    'input_symbol': token_inputs[0]['symbol'],
                    'output_symbol': token_outputs[0]['symbol'],
                    'price_value': price
                }
            
            swap_transactions.append(transaction_details)

    print(f"Found {swap_count} SWAP transactions out of {len(transactions)}")  # Debug 2
    return swap_transactions

def get_transactions(wallet_address, cache_file='transactions_cache.json'):
    """Fetch and cache filtered transactions"""
    cache_key = f"{wallet_address}-filtered-transactions"
    
    api_key = os.environ.get("HeliusApi")
    # Load cache
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            pass

    # Cache check logic - return cached filtered results if valid
    if cache_key in cache:
        cache_entry = cache[cache_key]
        cache_age = datetime.now() - datetime.fromisoformat(cache_entry['fetch_time'])
        
        if cache_age <= timedelta(hours=1):
            return cache_entry['filtered_data']

    # API call when no valid cache exists
    url = f'https://api.helius.xyz/v0/addresses/{wallet_address}/transactions/'
    params = {'api-key': api_key}
    
    print(f"Fetching fresh data from {url}")  # Debug 3
    response = requests.get(url, params=params)
    
    # Save raw API response for debugging
    with open('test.json', 'w') as f:
        json.dump(response.json(), f, indent=2)
    print("Saved raw API response to test.json")  # Debug 4

    if response.status_code != 200:
        raise Exception(f'API request failed: {response.status_code} - {response.text}')

    raw_data = response.json()
    print(f"Received {len(raw_data)} raw transactions")  # Debug 5
    
    # Process the data before caching
    filtered_data = analyze_swap_transactions(raw_data, wallet_address)
    print(f"Filtered down to {len(filtered_data)} swap transactions")  # Debug 6
    
    # Update cache with filtered results
    cache[cache_key] = {
        'fetch_time': datetime.now().isoformat(),
        'filtered_data': filtered_data
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)

    return filtered_data

if __name__ == "__main__":
    import json
    import requests
    from datetime import datetime, timedelta
    import os

    wallet_to_analyze = "CkBWowCj1SFFVDk8Fkn9b2S3gV8kgBm9MEPG2YQvmhFB"
    print("Starting transaction analysis...")
    swap_details = get_transactions(wallet_to_analyze)
    
    if not swap_details:
        print("Warning: No swap transactions found!")
    
    print(json.dumps(swap_details, indent=4))


