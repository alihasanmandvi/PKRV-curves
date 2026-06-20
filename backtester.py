import pandas as pd
import numpy as np
from scipy.optimize import minimize
import time
import warnings

# Suppress SciPy optimization warnings for a clean terminal output
warnings.filterwarnings('ignore')

# ==========================================
# 1. CORE QUANTITATIVE MATH
# ==========================================
def nss_model(t, b0, b1, b2, b3, tau1, tau2):
	t = np.where(t == 0, 1e-5, t)
	factor1 = (1 - np.exp(-t / tau1)) / (t / tau1)
	factor2 = (1 - np.exp(-t / tau2)) / (t / tau2)
	return b0 + b1 * factor1 + b2 * (factor1 - np.exp(-t / tau1)) + b3 * (factor2 - np.exp(-t / tau2))

def objective_function(params, t_data, y_data):
	if params[4] <= 0 or params[5] <= 0: return np.inf
	return np.sum((y_data - nss_model(t_data, *params)) ** 2)

# ==========================================
# 2. THE SIMULATION ENGINE
# ==========================================
def run_historical_simulation(matrix_csv="clean_yield_matrix_2501_to_2606.csv", threshold_bps=5.0):
	print(f"[*] Initializing Backtest Engine with Matrix: {matrix_csv}")

	try:
		df = pd.read_csv(matrix_csv, index_col='Date', parse_dates=True)
	except FileNotFoundError:
		print("[-] Critical Failure: Matrix not found. Run the Data Forge first.")
		return

	# Tenor to maturity mapping (Years)
	tenor_map = {'1M': 0.083, '3M': 0.25, '6M': 0.50, '1Y': 1.0, '2Y': 2.0,
	             '3Y': 3.0, '5Y': 5.0, '7Y': 7.0, '10Y': 10.0, '15Y': 15.0, '20Y': 20.0}

	available_tenors = list(df.columns)
	t_data = np.array([tenor_map[t] for t in available_tenors])

	# Portfolio Tracking Metrics
	total_trading_days = len(df)
	successful_optimizations = 0
	total_signals_generated = 0
	cumulative_spread_captured_bps = 0.0

	start_time = time.time()

	print("\n🚀 IGNITING TIME MACHINE...")
	print("-" * 60)

	# The Temporal Loop: Step through history day by day
	for date, row in df.iterrows():
		y_data = row.values

		# Skip days with catastrophic missing data that ffill couldn't fix
		if np.isnan(y_data).any():
			continue

		# Dynamic Initial Guess based on current day's yield curve
		b0_guess = y_data[-1]
		b1_guess = y_data[0] - b0_guess
		initial_guess = [b0_guess, b1_guess, 0.0, 0.0, 1.0, 2.0]
		bounds = [(0, 30), (-20, 20), (-20, 20), (-20, 20), (0.1, 15.0), (0.1, 15.0)]

		# Optimize curve for this specific historical day
		result = minimize(objective_function, initial_guess, args=(t_data, y_data),
		                  method='L-BFGS-B', bounds=bounds)

		if result.success:
			successful_optimizations += 1
			y_theo = nss_model(t_data, *result.x)
			spreads_bps = (y_data - y_theo) * 100

			# Identify mispricings
			buy_signals = spreads_bps[spreads_bps >= threshold_bps]
			sell_signals = spreads_bps[spreads_bps <= -threshold_bps]

			daily_signals = len(buy_signals) + len(sell_signals)
			total_signals_generated += daily_signals

			# Proxy for PnL: Assume we capture 50% of the theoretical mispricing as alpha
			daily_alpha_captured = (np.sum(buy_signals) + np.sum(np.abs(sell_signals))) * 0.5
			cumulative_spread_captured_bps += daily_alpha_captured

			# Terminal UI: Print a heart-beat every 20 days so we know it's running
			if successful_optimizations % 20 == 0:
				print(f"[>] Simulating {date.strftime('%Y-%m-%d')} | Alpha Captured: {daily_alpha_captured:.1f} bps")

	# ==========================================
	# 3. INSTITUTIONAL TEARSHEET
	# ==========================================
	execution_time = time.time() - start_time
	win_rate = (successful_optimizations / total_trading_days) * 100

	print("\n" + "="*60)
	print(" 📈 INSTITUTIONAL STRATEGY TEARSHEET")
	print("="*60)
	print(f"Simulation Period:      {df.index[0].strftime('%b %Y')} to {df.index[-1].strftime('%b %Y')}")
	print(f"Total Trading Days:     {total_trading_days}")
	print(f"Engine Convergence:     {win_rate:.1f}% ({successful_optimizations} days)")
	print(f"Execution Speed:        {execution_time:.2f} seconds")
	print("-" * 60)
	print(f"Arbitrage Threshold:    +/- {threshold_bps} bps")
	print(f"Total Signals Fired:    {total_signals_generated} trades")
	print(f"Avg Signals Per Day:    {total_signals_generated / successful_optimizations:.1f} trades")
	print("=" * 60)
	print(f"🏆 TOTAL THEORETICAL ALPHA CAPTURED: {cumulative_spread_captured_bps:,.0f} Basis Points")
	print("=" * 60)
	print("\n[!] Put this Alpha number on your resume.")

if __name__ == "__main__":
	# Ensure this matches the exact filename outputted by your data_cleaner.py
	run_historical_simulation(matrix_csv="clean_yield_matrix_2501_to_2606.csv", threshold_bps=5.0)