from datetime import datetime, timezone
from io import StringIO

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

def analyze_swap_transactions(transactions, wallet_address):
   
    swap_transactions = []

    for tx in transactions:
        if tx.get('type') != 'SWAP':
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
            
            if transfer['fromUserAccount'] == wallet_address:
                token_inputs.append({
                    'symbol': mint,
                    'address': mint,
                    'amount': amount
                })
            elif transfer['toUserAccount'] == wallet_address:
                token_outputs.append({
                    'symbol': mint,
                    'address': mint,
                    'amount': amount
                })

        if token_inputs or token_outputs:
            transaction_details = {
                'time_ago': time_ago,
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

    return swap_transactions

if __name__ == "__main__":
    import json
    
    with open('transactions.json', 'r') as file:
        transactions_data = json.load(file)
    
    wallet_to_analyze = "CkBWowCj1SFFVDk8Fkn9b2S3gV8kgBm9MEPG2YQvmhFB"
    swap_details = analyze_swap_transactions(transactions_data, wallet_to_analyze)
    
    # Print the output in JSON format
    print(json.dumps(swap_details, indent=4))

