import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import requests
import datetime
import io

st.set_page_config(page_title="PKRV Arbitrage Engine", layout="wide", page_icon="📈")

st.title("🏛️ Sovereign Yield Arbitrage Engine")
st.markdown("""
This institutional pipeline ingests the Pakistani Sovereign Yield Curve (PKRV), fits a Nelson-Siegel-Svensson (NSS) model 
to establish the risk-free benchmark, and calculates real-time arbitrage signals based on yield deviations.
""")

@st.cache_data(ttl=3600) # Cache for 1 hour to prevent IP bans from MUFAP
def get_latest_valid_mufap_url():
    """
    Temporal Back-Loop: Steps backward in time, skipping weekends, until it finds
    the most recent published market matrix.
    """
    # Our mathematical anchor: June 17, 2026 | ID: 25134
    anchor_date = datetime.date(2026, 6, 17)
    anchor_id = 25134
    today = datetime.date.today()

    base_url = "https://mufap.com.pk/Upload/WebDoc/IndustryStatictics/PKRV"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # Loop backward up to 10 days to find the latest valid file
    for lookback in range(10):
        target_date = today - datetime.timedelta(days=lookback)

        # 1. The Weekend Skipper (5 = Saturday, 6 = Sunday)
        if target_date.weekday() >= 5:
            continue

        # 2. ID Prediction Math
        days_elapsed = (target_date - anchor_date).days
        predicted_id = anchor_id + (days_elapsed * 5)
        date_str = target_date.strftime("%d%m%Y")

        # 3. The Precision Sweep (+/- 2 ID variation)
        for current_id in range(predicted_id - 2, predicted_id + 3):
            target_url = f"{base_url}{date_str}{current_id}.csv"
            try:
                response = requests.head(target_url, headers=headers, timeout=3)
                if response.status_code == 200:
                    return target_url, target_date
            except Exception:
                pass

    return None, None

@st.cache_data(ttl=3600)
def fetch_protected_csv(csv_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(csv_url, headers=headers, timeout=10)
        response.raise_for_status()

        df = pd.read_csv(io.StringIO(response.text))

        tenor_mapping = {
            '1M': 0.083, '3M': 0.25, '6M': 0.50, '1Y': 1.0,
            '2Y': 2.0, '3Y': 3.0, '5Y': 5.0, '7Y': 7.0, '10Y': 10.0,
            '15Y': 15.0, '20Y': 20.0
        }

        df['tau'] = df['Tenor'].map(tenor_mapping)
        df['y'] = pd.to_numeric(df['Mid Rate'], errors='coerce')
        clean_df = df.dropna(subset=['tau', 'y']).sort_values('tau')

        return clean_df['tau'].values, clean_df['y'].values, clean_df['Tenor'].values
    except Exception as e:
        return None, None, None

def nss_model(t, b0, b1, b2, b3, tau1, tau2):
    t = np.where(t == 0, 1e-5, t)
    factor1 = (1 - np.exp(-t / tau1)) / (t / tau1)
    factor2 = (1 - np.exp(-t / tau2)) / (t / tau2)
    return b0 + b1 * factor1 + b2 * (factor1 - np.exp(-t / tau1)) + b3 * (factor2 - np.exp(-t / tau2))

def objective_function(params, t_data, y_data):
    if params[4] <= 0 or params[5] <= 0:
        return np.inf
    y_pred = nss_model(t_data, *params)
    return np.sum((y_data - y_pred) ** 2)

# --- UI Sidebar Controls ---
st.sidebar.header("⚙️ Engine Parameters")
threshold_bps = st.sidebar.slider("Arbitrage Threshold (bps)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)

# --- Execution ---
with st.spinner("Initiating Temporal Back-Loop and securing market data..."):
    source_url, market_date = get_latest_valid_mufap_url()

if source_url:
    st.success(f"Data Pipeline Secured. Active Market Date: **{market_date.strftime('%B %d, %Y')}**")
    t_data, y_data, tenors = fetch_protected_csv(source_url)

    if t_data is not None:
        # Dynamic Initial Guesses
        b0_guess = y_data[-1] if len(y_data) > 0 else 12.0
        b1_guess = y_data[0] - b0_guess if len(y_data) > 0 else -1.0
        initial_guess = [b0_guess, b1_guess, 0.0, 0.0, 1.0, 2.0]

        bounds = [(0, 30), (-20, 20), (-20, 20), (-20, 20), (0.1, 15.0), (0.1, 15.0)]

        # Optimize curve
        result = minimize(objective_function, initial_guess, args=(t_data, y_data), method='L-BFGS-B', bounds=bounds)

        if result.success:
            optimal_params = result.x

            # 1. Visualization
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("NSS Sovereign Curve Architecture")
                t_continuous = np.linspace(0.1, max(t_data) + 2, 100)
                y_continuous = nss_model(t_continuous, *optimal_params)

                fig, ax = plt.subplots(figsize=(10, 5))
                # Institutional Dark Mode Styling
                fig.patch.set_facecolor('#0E1117')
                ax.set_facecolor('#0E1117')
                ax.scatter(t_data, y_data, color='#FF4B4B', s=60, label='Market Quotes', zorder=5)
                ax.plot(t_continuous, y_continuous, color='#00C4EB', linewidth=2.5, label='Fair Value (NSS)')

                ax.tick_params(colors='white')
                ax.yaxis.label.set_color('white')
                ax.xaxis.label.set_color('white')
                ax.set_xlabel('Tenor (Years)')
                ax.set_ylabel('Yield (%)')
                ax.grid(True, color='#333333', linestyle='--')
                ax.legend(facecolor='#0E1117', labelcolor='white')

                st.pyplot(fig)

            # 2. Arbitrage Scanner
            with col2:
                st.subheader("Live Signals")
                y_theo = nss_model(t_data, *optimal_params)
                spreads_bps = (y_data - y_theo) * 100

                df_arb = pd.DataFrame({
                    'Tenor': tenors,
                    'Market (%)': y_data,
                    'Fair Value': np.round(y_theo, 4),
                    'Spread (bps)': np.round(spreads_bps, 1)
                })

                def signal_logic(spread):
                    if spread >= threshold_bps: return "BUY"
                    if spread <= -threshold_bps: return "SELL"
                    return "HOLD"

                df_arb['Signal'] = df_arb['Spread (bps)'].apply(signal_logic)

                # Apply color formatting
                def highlight_signals(val):
                    if val == "BUY": return 'color: #00FF00; font-weight: bold'
                    if val == "SELL": return 'color: #FF4B4B; font-weight: bold'
                    return 'color: gray'

                st.dataframe(df_arb.style.map(highlight_signals, subset=['Signal']), height=400)
        else:
            st.error("Mathematical convergence failed for today's market data.")
else:
    st.error("Catastrophic Pipeline Failure: Exhausted 10-day temporal sweep. MUFAP servers may be down.")