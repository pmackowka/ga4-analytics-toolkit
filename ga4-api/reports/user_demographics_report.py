"""
Pobiera z GA4 Data API liczbę aktywnych użytkowników w podziale na przedział wiekowy
(userAgeBracket) dla jednego dnia i zapisuje wynik do CSV.

Wymaga:
- klucza JSON konta serwisowego z uprawnieniem "Viewer" do właściwości GA4
  (Admin -> Zarządzanie dostępem do usługi)
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
       Dimension(name="userAgeBracket"),
   ],
   metrics=[
       Metric(name="activeUsers"),
   ],
   date_ranges=[DateRange(start_date="2024-07-01", end_date="2024-07-01")],
)

response = client.run_report(request)

csv_file_path = "output_user_demographics.csv"

with open(csv_file_path, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["date", "userAgeBracket", "activeUsers"])

    for row in response.rows:
        writer.writerow([
            row.dimension_values[0].value,
            row.dimension_values[1].value,
            row.metric_values[0].value,
        ])

print(f"Wyniki zapisane do {csv_file_path}")
