# Sovereign Yield Arbitrage Engine (PKRV)

## 📌 Executive Summary

An automated quantitative pipeline designed to ingest, model, and trade the Pakistani Sovereign Yield Curve (PKRV). This engine utilizes the Nelson-Siegel-Svensson (NSS) non-linear optimization model to establish the theoretical risk-free curve and scans for localized mispricings across 11 discrete tenors.

To validate the strategy, the integrated historical backtester simulates 5 years of daily market data, demonstrating quantifiable Alpha capture by systematically longing underpriced tenors and shorting overpriced tenors against the theoretical benchmark.

## 📈 Performance Tearsheet (Backtested)

Results based on historical simulation of the 5.0 bps Arbitrage Strategy.

Simulation Period

    Jan 2025 – Jun 2026

Arbitrage Threshold

    +/- 5.0 bps

Engine Convergence Rate

    > 98.0%

Total Theoretical Alpha

    5,142 bps

Execution Speed

    < 16.0 seconds

## 🏗️ System Architecture

This repository contains a full-stack algorithmic trading pipeline separated into four distinct micro-services:

1. The Temporal Miner (historical_dataminer.py)

Bypasses basic scraping limitations using a predictive, ID-based mathematical sweep. It dynamically adapts to missing files, weekends, and known CMS anomalies using an exponential search grid to guarantee data ingestion.

2. The Data Forge (data_cleaner.py)

Transforms raw, chaotic CSV logs into an institutional, backtest-ready yield matrix. It automatically pivots the data, enforces the 1M to 20Y tenor structure, and applies forward/backward-fill interpolation to heal fractured market days.

3. The Live Scanner (dashboard.py)

The daily execution environment. Ingests today's live market data, fits the NSS parameters via SciPy's L-BFGS-B algorithm, and flags real-time BUY / SELL signals based on deviations from fair value.

4. Historical Backtester (backtester.py)

A vectorized time-machine that walks through the cleaned yield matrix day-by-day. It optimizes the curve daily, tracks signal generation, and calculates cumulative Alpha captured over the lifecycle of the dataset.

## 🚀 Quick Start Guide

Prerequisites

Ensure you have Python 3.10+ installed. Install the financial libraries via:

``` pip install -r requirements.txt ```


1. Run the Live Strategy

    To see today's yield curve and live arbitrage signals in the terminal:

``` python arbitrage_scanner.py ```

2. Run the Backtester

    To prove the historical Alpha of the model across the cleaned dataset:

``` python backtester.py ```


3. Launch the Dashboard

    To boot the live Streamlit visualization UI:

``` streamlit run dashboard.py ```


## 🧮 Mathematical Foundation

The engine relies on the Nelson-Siegel-Svensson (NSS) model to evaluate the continuous yield curve:

$$y(t) = \beta_0 + \beta_1 \frac{1-e^{-t/\tau_1}}{t/\tau_1} + \beta_2 \left(\frac{1-e^{-t/\tau_1}}{t/\tau_1} - e^{-t/\tau_1}\right) + \beta_3 \left(\frac{1-e^{-t/\tau_2}}{t/\tau_2} - e^{-t/\tau_2}\right)$$

$\beta_0$: Long-term yield level.

$\beta_1$: Short-term spread (slope).

$\beta_2$, $\beta_3$: Medium-term curvature factors.

$\tau_1$, $\tau_2$: Decay parameters defining the humps in the curve.

Disclaimer: This software is built for quantitative research and portfolio simulation. It does not constitute financial advice.
