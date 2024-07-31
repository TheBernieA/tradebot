const currencyPairEl = document.querySelector('#currencyPair');
const serverField = document.querySelector('#serverField')
const url = 'http://localhost:5000'
// let apiToken = null;
// let orderIds = []; // Array to store order IDs

const currencyPairs = [
    { value: 'USDCAD', label: 'USD/CAD' },
    { value: 'EURUSD', label: 'EUR/USD' },
    { value: 'GBPUSD', label: 'GBP/USD' },
    { value: 'USDJPY', label: 'USD/JPY' },
    { value: 'EURGBP', label: 'EUR/GBP' },
    { value: 'AUDUSD', label: 'AUD/USD' },
    { value: 'XAUUSD', label: 'XAU/USD' },
    { value: 'BTCUSD', label: 'BTC/USD' },
    { value: 'ETHUSD', label: 'ETH/USD' },
    { value: 'US30', label: 'US30' },
];

currencyPairs.forEach(pair => {
    const option = document.createElement('option');
    option.value = pair.value;
    option.innerHTML = pair.label;
    currencyPairEl.appendChild(option);
});

const servers = [
    { value: 'ICMarketsSC-MT5-4', label: 'ICMarketsSC-MT5-4' },
    { value: 'ICMarketsUK-MT5-2', label: 'ICMarketsUK-MT5-2' },
    { value: 'MetaQuotes-Demo', label: 'MetaQuotes-Demo' },
]

servers.forEach(server => {
    const option = document.createElement('option');
    option.value = server.value;
    option.innerHTML = server.label;
    serverField.appendChild(option);
})


// Event listeners for buttons
document.getElementById('login').addEventListener('click', login);
document.getElementById('openTrade').addEventListener('click', openTrade);
document.querySelector('#closeTrade').addEventListener('click', closeAllTrades);

let loginStatus = false; // Track login status


// Function to handle login
async function login() {
    const loginField = parseInt(document.getElementById('loginField').value);
    const passwordField = document.getElementById('passwordField').value;
    const serverField = document.querySelector('#serverField').value

    if (!loginField || !passwordField || !serverField) {
        alert('Please enter your login, password, and server.');
        return;
    }

    try {
        const response = await fetch(`${url}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ login: loginField, password: passwordField, server: serverField })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Login successful');
            loginStatus = true;
            document.getElementById('openTrade').disabled = false;
            document.getElementById('closeTrade').disabled = false;
            fetchOpenTrades()
        } else {
            alert(`Error: ${data.error}`);
            loginStatus = false;
            document.getElementById('openTrade').disabled = true;
            document.getElementById('closeTrade').disabled = true;
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to login');
        loginStatus = false;
        document.getElementById('openTrade').disabled = true;
        document.getElementById('closeTrade').disabled = true;
    }
}

// Function to handle opening a trade
async function openTrade() {
    if (!loginStatus) {
        alert('You must log in first.');
        return;
    }

    const currencyPair = document.getElementById('currencyPair').value;
    const tradeType = document.getElementById('tradeType').value;
    const lotSize = document.getElementById('lotSize').value;
    const takeProfitPips = document.getElementById('takeProfit').value * 10;
    const stopLossPips = document.getElementById('stopLoss').value * 10;
    const numTrades = document.getElementById('numTrades').value;


    if (!currencyPair || !tradeType || !lotSize || !stopLossPips || !numTrades) {
        alert('Please enter all fields.');
        return;
    }

    try {
        for (let i = 0; i < numTrades; i++) {
            const response = await fetch(`${url}/open_trade`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    symbol: currencyPair,
                    volume: lotSize,
                    take_profit: takeProfitPips,
                    stop_loss: stopLossPips,
                    type: tradeType
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                alert(`Error opening trade ${i + 1}: ${errorData.error}`);
                return;  // Exit the loop on the first error
            } else {
                const data = await response.json();
                console.log(`Trade ${i + 1} opened successfully with order ID: ${data.order_id}`);
            }
        }
        fetchOpenTrades();  // Refresh the list of open trades
        alert('All trades opened successfully');
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to open trades');
    }
}




// Fetch all opened trades
async function fetchOpenTrades() {
    if (!loginStatus) {
        alert('You must log in first.');
        return;
    }

    const BUY = [];
    const SELL = [];

    try {
        const response = await fetch(`${url}/get_open_trades`);

        const data = await response.json();

        console.log('trades', data);

        if (response.ok) {
            const sellList = document.getElementById('sellList');
            const buyList = document.getElementById('buyList');

            if (!sellList || !buyList) {
                console.error('sellList or buyList element not found');
                return;
            }

            sellList.innerHTML = '';  // Clear previous entries
            buyList.innerHTML = '';

            if (data.length > 0) {
                data.forEach(trade => {
                    if (trade.type === 'BUY') {
                        BUY.push(trade);
                        const buyLengthElement = document.querySelector('.buyLength');
                        if (buyLengthElement) {
                            buyLengthElement.innerHTML = `BUY: ${BUY.length}`;
                        } else {
                            console.error('.buyLength element not found');
                        }
                    } else {
                        SELL.push(trade);
                        const sellLengthElement = document.querySelector('.sellLength');
                        if (sellLengthElement) {
                            sellLengthElement.innerHTML = `SELL: ${SELL.length}`;
                        } else {
                            console.error('.sellLength element not found');
                        }
                    }
                });
            }

            BUY.forEach(trade => {
                const listItem = document.createElement('li');
                listItem.textContent = `Order ID: ${trade.order_id}, Symbol: ${trade.symbol}, Volume: ${trade.volume}, Price: ${trade.price}, Type: ${trade.type}`;
                buyList.appendChild(listItem);
            });

            SELL.forEach(trade => {
                const listItem = document.createElement('li');
                listItem.textContent = `Order ID: ${trade.order_id}, Symbol: ${trade.symbol}, Volume: ${trade.volume}, Price: ${trade.price}, Type: ${trade.type}`;
                sellList.appendChild(listItem);
            });
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to fetch trades');
    }
}


// Function to handle closing trades
async function closeAllTrades() {
    if (!loginStatus) {
        alert('You must log in first.');
        return;
    }

    try {
        const response = await fetch(`${url}/close_all_trades`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})  // No body needed for closing all trades
        });

        const data = await response.json();

        if (response.ok) {
            const results = data.results;
            if (results.every(result => result.status === "success")) {
                alert('All trades closed successfully');
            } else {
                alert('Some trades could not be closed:\n' + results.map(result => `Ticket: ${result.ticket}, Status: ${result.status}, Error: ${result.error}`).join('\n'));
            }
            fetchOpenTrades();  // Refresh the list of open trades
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to close trades');
    }
}


