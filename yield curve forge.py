import pandas as pd
import numpy as np

def forge_yield_matrix(input_csv="master_historical_pkrv_2020_2026.csv", output_csv="clean_yield_matrix.csv"):
	"""
	Transforms a raw scraped CSV into a clean, backtest-ready Yield Curve Matrix.
	"""
	print(f"[*] Igniting Data Forge on: {input_csv}")

	try:
		# 1. Ingest Raw Ore
		df = pd.read_csv(input_csv)
	except FileNotFoundError:
		print(f"[-] Critical Failure: {input_csv} not found. Ensure the filename matches your miner's output.")
		return

	# 2. Standardize Time
	df['Date'] = pd.to_datetime(df['Date'])

	# 3. Purge Redundancy
	initial_rows = len(df)
	df = df.drop_duplicates(subset=['Date', 'Tenor'])
	if initial_rows - len(df) > 0:
		print(f"[!] Purged {initial_rows - len(df)} duplicate records.")

	# 4. The Pivot: Transform to Matrix
	print("[*] Pivoting raw data into mathematical matrix...")
	matrix = df.pivot(index='Date', columns='Tenor', values='Yield')

	# 5. Enforce Institutional Tenor Structure
	ordered_tenors = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y']

	# Filter to only keep our whitelist, ordered by true maturity
	existing_tenors = [t for t in ordered_tenors if t in matrix.columns]
	matrix = matrix[existing_tenors]

	# Sort timeline chronologically
	matrix = matrix.sort_index()

	# 6. Heal the Fractures (Interpolate Missing Data)
	# If a specific tenor is missing on a Tuesday, we assume it held Monday's yield (Forward Fill)
	missing_count = matrix.isna().sum().sum()
	if missing_count > 0:
		print(f"[*] Healing {missing_count} fractured data points via Forward-Fill interpolation...")
		matrix = matrix.ffill()
		# Any remaining NaNs at the very start are back-filled
		matrix = matrix.bfill()

	# 7. Export the Refined Steel
	matrix.to_csv(output_csv)
	print(f"\n[+] Forge Complete. Matrix Dimensions: {matrix.shape[0]} trading days, {matrix.shape[1]} tenors.")
	print(f"[+] Institutional Matrix locked and saved to: {output_csv}")

if __name__ == "__main__":
	# Point this to the exact name of the file your miner just created
	raw_file = "historical_pkrv_matrix.csv"
	clean_file = "clean_yield_matrix_2501_to_2606.csv"

	forge_yield_matrix(input_csv="master_historical_pkrv_2020_2026.csv", output_csv=clean_file)