import requests
import datetime
import pandas as pd
import time
import concurrent.futures

# ==========================================
# CONFIGURATION: YEARLY ANCHORS
# ==========================================
# Input your exact IDs for the first trading day of each year below.
# The engine will use these as launchpads to sweep through each specific year.
YEARLY_ANCHORS = {
    2026: {"start": "02012026", "end": "19062026", "anchor_id": 24508}, # Replace anchor_id
    2025: {"start": "02012025", "end": "31122025", "anchor_id": 3079}, # From your previous check
}

# ==========================================
# CONFIGURATION: KNOWN SERVER ANOMALIES
# ==========================================
# Massive jumps that break standard sweep logic.
# Format: "DDMMYYYY": ID_Jump_Amount
KNOWN_ANOMALIES = {
    "14042025": 10000,
    "29042025": 10000
}

# Strict whitelist to filter out CMS garbage/headers across different historical formats
VALID_TENORS = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y']

def mine_year(year, start_str, end_str, initial_anchor_id, session, base_url):
    """
    Executes a multi-threaded temporal sweep for a single specified year.
    """
    start_date = datetime.datetime.strptime(start_str, "%d%m%Y").date()
    end_date = datetime.datetime.strptime(end_str, "%d%m%Y").date()

    yearly_data = []
    current_date = start_date
    current_predicted_id = initial_anchor_id
    consecutive_misses = 0

    print(f"\n🚀 IGNITING BATCH {year}: {start_date} to {end_date} (Base ID: {initial_anchor_id})")

    while current_date <= end_date:
        if current_date.weekday() > 4:
            current_date += datetime.timedelta(days=1)
            continue

        date_str = current_date.strftime("%d%m%Y")
        file_found = False

        # --- THE ANOMALY OVERRIDE ---
        if date_str in KNOWN_ANOMALIES:
            jump = KNOWN_ANOMALIES[date_str]
            print(f"\n[!] TEMPORAL ANOMALY DETECTED: Hard-shifting engine ID by +{jump} for {date_str}")
            current_predicted_id += jump

        # Dynamic exponential sweep: Base 10, doubles every miss, capped at 2000
        sweep_size = min(10 * (2 ** consecutive_misses), 2000)
        search_range = range(current_predicted_id, current_predicted_id + sweep_size + 1)

        target_url_found = None
        verified_id = None

        def check_url(test_id):
            url = f"{base_url}{date_str}{test_id}.csv"
            try:
                if session.head(url, timeout=3).status_code == 200:
                    return test_id, url
            except requests.exceptions.RequestException:
                pass
            return None, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(check_url, test_id): test_id for test_id in search_range}
            for future in concurrent.futures.as_completed(futures):
                res_id, res_url = future.result()
                if res_url:
                    target_url_found = res_url
                    verified_id = res_id
                    for f in futures:
                        f.cancel()
                    break

        if target_url_found:
            try:
                response = session.get(target_url_found, timeout=5)
                print(f"[+] {year} | {current_date} | ID: {verified_id} | Drift: {verified_id - current_predicted_id}")

                # Resilient Parsing Logic for historical format changes
                lines = response.text.split('\n')
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 2:
                        tenor = parts[0].upper()
                        if tenor in VALID_TENORS:
                            try:
                                yield_val = float(parts[1])
                                yearly_data.append({
                                    "Date": current_date,
                                    "Tenor": tenor,
                                    "Yield": yield_val
                                })
                            except ValueError:
                                pass # Skip headers or malformed floats

                file_found = True
                current_predicted_id = verified_id + 5
                consecutive_misses = 0

            except requests.exceptions.RequestException as e:
                print(f"[!] {year} | Target located but download failed for {current_date}: {e}")

        if not file_found:
            consecutive_misses += 1
            print(f"[-] {year} | Missing Data for {current_date} (Swept {sweep_size} IDs from {current_predicted_id})")

        time.sleep(0.3) # Slightly reduced delay for batch speed
        current_date += datetime.timedelta(days=1)

    return yearly_data

def clean_and_compile_dataset(all_data):
    """
    Standardizes tenors, sorts chronologically, and removes anomalies.
    """
    print("\n🧹 Executing Master Data Cleansing Protocol...")
    df = pd.DataFrame(all_data)

    if df.empty:
        print("[-] Master dataset is empty. Pipeline halted.")
        return

    # Convert dates to true datetime objects
    df['Date'] = pd.to_datetime(df['Date'])

    # Drop exact duplicates caused by server re-uploads
    initial_len = len(df)
    df = df.drop_duplicates(subset=['Date', 'Tenor'])

    # Map tenors to numerical values for strict sorting
    tenor_map = {'1M': 1, '3M': 3, '6M': 6, '1Y': 12, '2Y': 24, '3Y': 36, '5Y': 60, '7Y': 84, '10Y': 120, '15Y': 180, '20Y': 240}
    df['Tenor_Months'] = df['Tenor'].map(tenor_map)

    # Sort chronologically, then by tenor curve structure
    df = df.sort_values(by=['Date', 'Tenor_Months']).drop(columns=['Tenor_Months'])

    output_file = "master_historical_pkrv_2025_2026.csv"
    df.to_csv(output_file, index=False)

    print(f"[+] Cleansing Complete. Removed {initial_len - len(df)} duplicate/malformed rows.")
    print(f"[+] Master CSV generated: {output_file} ({len(df)} total records).")

if __name__ == "__main__":
    base_url = "https://mufap.com.pk/Upload/WebDoc/IndustryStatictics/PKRV"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    master_dataset = []

    # Execute the YoY batch sweep
    for year, config in sorted(YEARLY_ANCHORS.items(), reverse=True): # Sweeping backward from 2026 to 2025
        yearly_data = mine_year(
            year=year,
            start_str=config["start"],
            end_str=config["end"],
            initial_anchor_id=config["anchor_id"],
            session=session,
            base_url=base_url
        )
        master_dataset.extend(yearly_data)

    # Clean and Export
    clean_and_compile_dataset(master_dataset)