from flask import Flask, request, render_template
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
from time import sleep
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
                sleep(0.8)  # Delay between requests
                try:
                    logging.info(f"Fetching data for symbol: {symbol}")
                    
                    # Fetch more historical data to ensure coverage
                    df = tv.get_hist(
                        symbol=symbol,
                        exchange="BINANCE",  
                        interval=Interval.in_daily,
                        n_bars=10  # Increased to ensure more data
                    )
                    
                    # Ensure the index is a datetime object
                    df.index = pd.to_datetime(df.index)
                    
                    # Detailed logging of data range
                    logging.info(f"Full data range for {symbol}: {df.index.min()} to {df.index.max()}")
                    logging.info(f"Filtering from {from_date_dt} to {to_date_dt}")

                    # More flexible date filtering
                    df_filtered = df[
                        (df.index.date >= from_date_dt.date()) & 
                        (df.index.date <= to_date_dt.date())
                    ]
                    
                    logging.info(f"Filtered data length for {symbol}: {len(df_filtered)}")

                    if not df_filtered.empty and len(df_filtered) >= 3:
                        # Calculate daily percentage changes
                        day1_change = round(((df_filtered['close'].iloc[1] - df_filtered['close'].iloc[0]) / df_filtered['close'].iloc[0]) * 100, 2)
                        day2_change = round(((df_filtered['close'].iloc[2] - df_filtered['close'].iloc[1]) / df_filtered['close'].iloc[1]) * 100, 2)

                        # Calculate total percentage change
                        open_price = df_filtered['open'].iloc[0]
                        close_price = df_filtered['close'].iloc[-1]
                        total_percentage_change = ((close_price - open_price) / open_price) * 100

                        # Prepare result with daily changes
                        result = {
                            'symbol': symbol,
                            'exchange': "BINANCE",
                            'total_percentage_change': round(total_percentage_change, 2),
                            'day_1_percent_change': day1_change,
                            'day_2_percent_change': day2_change
                        }
                        results.append(result)
                        
                        # Log successful data retrieval
                        logging.info(f"Successfully processed {symbol}: {result}")
                    else:
                        logging.warning(f"No data within range for {symbol}")
                        results.append({
                            'symbol': symbol,
                            'exchange': "BINANCE",
                            'total_percentage_change': 'No data within range',
                            'day_1_percent_change': 'N/A',
                            'day_2_percent_change': 'N/A'
                        })
                
                except Exception as e:
                    logging.error(f"Error processing {symbol}: {e}")
                    results.append({
                        'symbol': symbol,
                        'exchange': "BINANCE",
                        'total_percentage_change': f"Error: {str(e)}",
                        'day_1_percent_change': 'Error',
                        'day_2_percent_change': 'Error'
                    })

        except Exception as e:
            logging.error(f"Main processing error: {e}")
            error = str(e)

    return render_template('index.html', results=results, error=error, date_message=date_message)

if __name__ == '__main__':
    app.run(debug=True, port=3000)