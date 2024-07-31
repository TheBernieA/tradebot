import MetaTrader5 as mt5

# Initialize and login in one step
if not mt5.initialize(login=11015784, password="BenA@1994", server="ICMarketsSC-MT5-4"):
    print("Failed to initialize and login, error code:", mt5.last_error())
else:
    print("Successfully connected to the account")
