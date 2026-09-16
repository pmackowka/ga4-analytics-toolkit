# Szybki sanity check środowiska (np. po deployu Cloud Function) — czy wszystkie
# zależności GA4 Data API zainstalowały się poprawnie, bez konieczności odpalania całego raportu.
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

print("Wszystkie biblioteki zostały zaimportowane poprawnie.")
