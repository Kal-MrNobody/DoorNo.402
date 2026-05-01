from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
receipt = w3.eth.get_transaction_receipt("0xe48234441e6a29c1a68c3c5d2d3b90a4a838d93198a07f06123ad1d7fcab38e1")
print(f"Status: {receipt.status}")
