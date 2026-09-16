"""
Pobiera z GA4 Data API dzienny raport kosztów i konwersji Google Ads
(połączone konto Ads widoczne w GA4 jako "Google Ads Campaign") i zapisuje do CSV.

Wymaga:
- klucza JSON konta serwisowego z uprawnieniem "Viewer" do właściwości GA4
- zmiennej środowiskowej GA4_CREDENTIALS_PATH ze ścieżką do tego klucza
- zmiennej środowiskowej GA4_PROPERTY_ID z ID właściwości GA4 (bez prefiksu "properties/")
"""

import csv
import os

from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

CREDENTIALS_PATH = os.environ["GA4_CREDENTIALS_PATH"]
PROPERTY_ID = os.environ["GA4_PROPERTY_ID"]

credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
client = BetaAnalyticsDataClient(credentials=credentials)

request = RunReportRequest(
   property=f"properties/{PROPERTY_ID}",
   dimensions=[
       Dimension(name="date"),
       Dimension(name="googleAdsCampaignName"),  # Nazwa kampanii Google Ads przypisanej do kluczowego zdarzenia.
       Dimension(name="googleAdsCampaignId"),  # Identyfikator kampanii Google Ads przypisanej do kluczowego zdarzenia.
    #    Dimension(name="googleAdsAdGroupName"),  # Nazwa grupy reklam przypisana do kluczowego zdarzenia.
    ],
   metrics=[
       Metric(name="keyEvents"),  # Liczba kluczowych zdarzeń.
       Metric(name="advertiserAdCost"),  # Łączny koszt reklam, w tym z połączonych integracji (np. DV360).
       Metric(name="advertiserAdCostPerKeyEvent"),  # Koszt reklamy / liczba kluczowych zdarzeń.
       Metric(name="advertiserAdImpressions"),  # Łączna liczba wyświetleń, w tym z połączonych integracji.
       Metric(name="advertiserAdClicks"),  # Łączna liczba kliknięć reklamy, w tym z połączonych integracji (np. SA360).
       Metric(name="advertiserAdCostPerClick"),  # Koszt reklamy / liczba kliknięć (CPC).
       Metric(name="purchaseRevenue"),  # Przychód z eventów "purchase", pomniejszony o zwroty.
       Metric(name="returnOnAdSpend"),  # Przychód / koszt reklamy (ROAS).
   ],
   date_ranges=[DateRange(start_date="2024-06-01", end_date="2024-06-01")],
)

response = client.run_report(request)

csv_file_path = "output_gads_conversions.csv"

with open(csv_file_path, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow([
        "date",
        "googleAdsCampaignName",
        "googleAdsCampaignId",
        "keyEvents",
        "advertiserAdCost",
        "advertiserAdCostPerKeyEvent",
        "advertiserAdImpressions",
        "advertiserAdClicks",
        "advertiserAdCostPerClick",
        "purchaseRevenue",
        "returnOnAdSpend",
    ])

    for row in response.rows:
        writer.writerow([
            row.dimension_values[0].value,
            row.dimension_values[1].value,
            row.dimension_values[2].value,
            row.metric_values[0].value,
            row.metric_values[1].value,
            row.metric_values[2].value,
            row.metric_values[3].value,
            row.metric_values[4].value,
            row.metric_values[5].value,
            row.metric_values[6].value,
            row.metric_values[7].value,
        ])

print(f"Wyniki zapisane do {csv_file_path}")
