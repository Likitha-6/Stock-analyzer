A Streamlit web-app that lets you explore fundamental metrics for NSE-listed companies, compare two stocks side-by-side, and visualise long-term trends – all in one click.

✨ Key Features

Smart search  : • Type a symbol or company name
                • Fuzzy-matched against nse stocks.csv for lightning-fast lookup

Fundamental snapshot : • Market Cap tier 
                        • P/E vs industry average 
                        • EPS, Dividend Yield, Profit Margin, FCF 
                        • ROE  with colour-coded hints

Comparison mode : • Tick-marks show which stock “wins” each metric 
                  • Side-by-side line charts: Price, PAT, Revenue, FCF

Historicals  :  • Interactive line / bar charts for up to max data
                • All-time-high tracker with % off ATH

100 % Python + Streamlit  Easy to extend – no JavaScript required


🚀 Quick start:
# 1. Clone
git clone https://github.com/Likitha-6/Stock-analyzer.git
cd Stock-analyzer

# 2. Create / activate a virtual env (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# 3. Install deps
pip install -r requirements.txt      # Streamlit, yfinance, pandas, etc.

# 4. Run
streamlit run app.py
