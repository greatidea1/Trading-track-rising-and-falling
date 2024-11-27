from flask import Flask, request, render_template
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
from time import sleep
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Directory to store uploaded files
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize TradingView TvDatafeed instance
tv = TvDatafeed()

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    error = None
    date_message = None  # Variable to store the date range message

    if request.method == 'POST':
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')
        file = request.files.get('file')

        try:
            # Parse dates
            from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_date_dt = from_date_dt + timedelta(days=2) if not to_date else datetime.strptime(to_date, '%Y-%m-%d')

            # Generate the message to display the selected date range
            date_message = f"Selected date range: {from_date_dt.strftime('%Y-%m-%d')} to {to_date_dt.strftime('%Y-%m-%d')}"

            # Handle uploaded file
            if not file:
                raise ValueError("Please upload a CSV file containing coin symbols.")

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Read the CSV file to extract coin symbols
            df_coins = pd.read_csv(filepath)
            if 'symbol' not in df_coins.columns:
                raise ValueError("CSV file must have a 'symbol' column.")

            coin_symbols = df_coins['symbol'].tolist()

            # Fetch historical data
            results = []
            for symbol in coin_symbols:
                sleep(0.5)  # in seconds
                try:
                    # Fetch enough bars to cover the entire date range
                    df = tv.get_hist(
                        symbol=symbol,
                        exchange="BINANCE",  # Default exchange
                        interval=Interval.in_daily,
                        n_bars=10  # Increased to ensure we have enough data
                    )

                    # Ensure the index is a datetime object
                    df.index = pd.to_datetime(df.index)

                    # Filter data based on date range
                    df_filtered = df[(df.index >= from_date_dt) & (df.index <= to_date_dt)]

                    if not df_filtered.empty and len(df_filtered) >= 2:
                        # Calculate daily percentage changes
                        daily_changes = []
                        for i in range(1, len(df_filtered)):
                            prev_close = df_filtered['close'].iloc[i-1]
                            curr_close = df_filtered['close'].iloc[i]
                            daily_change = ((curr_close - prev_close) / prev_close) * 100
                            daily_changes.append(round(daily_change, 2))

                        # Calculate total percentage change
                        open_price = df_filtered['open'].iloc[0]
                        close_price = df_filtered['close'].iloc[-1]
                        total_percentage_change = ((close_price - open_price) / open_price) * 100

                        # Prepare result with daily changes
                        result = {
                            'symbol': symbol,
                            'exchange': "BINANCE",
                            'total_percentage_change': round(total_percentage_change, 2),
                            'daily_changes': daily_changes
                        }
                        results.append(result)
                    else:
                        results.append({
                            'symbol': symbol,
                            'exchange': "BINANCE",
                            'total_percentage_change': 'No data within range',
                            'daily_changes': []
                        })
                except Exception as e:
                    results.append({
                        'symbol': symbol,
                        'exchange': "BINANCE",
                        'total_percentage_change': f"Error: {str(e)}",
                        'daily_changes': []
                    })

        except Exception as e:
            error = str(e)

    return render_template('index.html', results=results, error=error, date_message=date_message)

if __name__ == '__main__':
    app.run(debug=True, port=3000)