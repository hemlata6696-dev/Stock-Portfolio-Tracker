# Stock Portfolio Tracker

A simple web app built with Python and Flask to track your stock holdings, total investment, and profit or loss. Stock prices are entered by hand, so there is no API key or internet data needed.

## Features

- Add stocks with quantity and buy price
- See total invested, current value, and profit/loss (amount and %)
- Starts with a hardcoded price dictionary (`AAPL`, `TSLA`, `MSFT`, `GOOGL`, `AMZN`)
- Add, update, or delete stock prices from the website
- Saves your data in a local JSON file, so it is still there after a restart
- History table that records your total each time it changes
- Download your portfolio as **CSV** or **TXT**
- Input checks: unknown stocks, negative numbers, and bad values are rejected
- Works on phone and desktop screens, with dark mode support

## Tech used

- Python 3.8+
- Flask
- Python basics: dictionaries, input/output, arithmetic, file handling (JSON, CSV, TXT)

## How to run

1. Install Python from [python.org](https://www.python.org/downloads/)
2. Download or clone this repo:
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```
3. Install Flask:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   python portfolio_tracker.py
   ```
5. Open <http://127.0.0.1:5000> in your browser

To stop the server, press `Ctrl + C` in the terminal.

## How to use

1. **Set prices:** use the "Price list" box to add a stock or update its current price.
2. **Add a holding:** enter the stock, quantity, and the price you bought at.
3. **Check results:** the top cards show total invested, current value, and profit/loss.
4. **Update prices later** to see how your profit/loss changes. Each change is saved in the History table.
5. **Download:** use the CSV or TXT buttons to save a report.

## Project structure

```
.
├── portfolio_tracker.py   # the whole app (routes, logic, page template)
├── requirements.txt       # Python packages needed
├── .gitignore             # keeps your personal data file out of Git
└── README.md
```

`portfolio_data.json` is created automatically on first use. It holds your data and is not uploaded to GitHub.

## Limitations

- **Prices are manual.** The app does not fetch live market prices.
- **No login.** Anyone who can open the page can change the data. Use it only on your own computer, and do not host it publicly as it is.
- **One portfolio only.** It is built for a single user.
- Buying the same stock at different prices shows as separate rows. They are not merged into an average price.

## Ideas for improvement

- Live prices from a market data API
- Login and multiple users
- Charts for portfolio value over time
- Average buy price when the same stock is bought more than once

## License

MIT. Add a `LICENSE` file if you want others to be able to reuse your code.
