"""
Google Cloud Function (HTTP trigger) uruchamiana codziennie przez Cloud Scheduler.
Pobiera z GA4 Data API dzienny raport kosztów/konwersji Google Ads sprzed 2 dni
(GA4 potrzebuje ok. 24-48h, żeby dane z Ads w pełni się ułożyły) i dogrywa wiersze
do tabeli w BigQuery zdefiniowanej w create_table_bq.sql.

Uwierzytelnianie GA4 i BigQuery: BetaAnalyticsDataClient() i bigquery.Client() bez
argumentów korzystają z Application Default Credentials — w środowisku Cloud Functions
to konto usługi przypisane do funkcji (musi mieć uprawnienia "Viewer" do właściwości GA4
i "BigQuery Data Editor" do datasetu docelowego).

Zmienne środowiskowe (ustawiane w konfiguracji Cloud Function):
- GA4_PROPERTY_ID   — ID właściwości GA4 (bez prefiksu "properties/")
- BQ_DATASET_ID     — dataset docelowy w BigQuery
- BQ_TABLE_ID       — tabela docelowa w BigQuery
"""

# ============================================================================
# JAK OPOWIEDZIEĆ TEN SKRYPT — 7 kroków (komentarze „KROK n” niżej w kodzie)
#   1. Uruchomienie: Cloud Scheduler codziennie rano wywołuje funkcję przez HTTP.
#   2. Konfiguracja: ID właściwości GA4 i tabeli docelowej ze zmiennych
#      środowiskowych — nic nie jest wpisane na sztywno w kodzie.
#   3. Zakres dat: dzień sprzed 2 dni, bo dane Google Ads w GA4 układają się do 48 h.
#   4. Uwierzytelnienie: konto usługi przypisane do funkcji (ADC), bez pliku klucza.
#   5. Zapytanie do GA4 Data API (REST): wymiary + metryki kampanii Google Ads.
#   6. Transformacja: każdy wiersz odpowiedzi -> słownik z typami pod schemat tabeli.
#   7. Zapis do BigQuery i odpowiedź HTTP 200 / 500 dla harmonogramu.
# Na końcu pliku: co poprawiłbym dziś (idempotentność, paginacja, format daty).
# ============================================================================

import json
import os
from datetime import date, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.cloud import bigquery

# KROK 2 — konfiguracja ze zmiennych środowiskowych Cloud Function.
# Ten sam kod działa dla innej właściwości albo tabeli bez zmiany kodu;
# brak zmiennej kończy się błędem od razu przy starcie (KeyError), nie w połowie.
PROPERTY_ID = f"properties/{os.environ['GA4_PROPERTY_ID']}"
DATASET_ID = os.environ["BQ_DATASET_ID"]
TABLE_ID = os.environ["BQ_TABLE_ID"]


# KROK 1 — punkt wejścia funkcji HTTP. Cloud Scheduler wysyła tu zapytanie
# codziennie rano; argument `request` nie jest używany, bo funkcja nie potrzebuje
# parametrów — wszystko wynika z daty i konfiguracji.
def ga4_api_gads(request):
    try:
        # KROK 3 — zakres dat: jeden dzień, przedwczoraj.
        # Wczorajszy dzień byłby niepełny: koszty i konwersje Google Ads
        # dochodzą do GA4 z opóźnieniem do ok. 48 godzin.
        przedwczoraj = date.today() - timedelta(days=2)
        przedwczoraj_str = przedwczoraj.strftime("%Y-%m-%d")

        # KROK 4 — klienci API bez argumentów = Application Default Credentials.
        # W Cloud Functions to konto usługi przypisane do funkcji: Viewer we
        # właściwości GA4 i BigQuery Data Editor w datasecie docelowym.
        # Zero kluczy JSON w kodzie i w repo.
        client = BetaAnalyticsDataClient()
        bq_client = bigquery.Client()

        # KROK 5 — definicja raportu dla GA4 Data API (API REST; biblioteka
        # kliencka wysyła je domyślnie przez gRPC). Wymiary = po czym grupujemy
        # (dzień, kampania), metryki = co liczymy (koszt, kliknięcia, przychód, ROAS).
        ga4_request = RunReportRequest(
            property=PROPERTY_ID,
            dimensions=[
                Dimension(name="date"),
                Dimension(name="googleAdsCampaignName"),
                Dimension(name="googleAdsCampaignId"),
            ],
            metrics=[
                Metric(name="keyEvents"),
                Metric(name="advertiserAdCost"),
                Metric(name="advertiserAdCostPerKeyEvent"),
                Metric(name="advertiserAdImpressions"),
                Metric(name="advertiserAdClicks"),
                Metric(name="advertiserAdCostPerClick"),
                Metric(name="purchaseRevenue"),
                Metric(name="returnOnAdSpend"),
            ],
            date_ranges=[DateRange(start_date=przedwczoraj_str, end_date=przedwczoraj_str)],
        )

        # Wywołanie API — jedno zapytanie, odpowiedź z wierszami raportu.
        response = client.run_report(ga4_request)

        # KROK 6 — transformacja odpowiedzi do formatu tabeli BigQuery.
        # GA4 zwraca każdą wartość jako tekst, w kolejności z definicji raportu:
        # dimension_values[0] = date, [1] = nazwa kampanii itd. Dlatego jawnie
        # rzutujemy typy: kwoty na float, liczniki na int (przez float, bo GA4
        # potrafi zwrócić "12.0").
        rows_to_insert = [
            {
                "date": row.dimension_values[0].value,
                "googleAdsCampaignName": row.dimension_values[1].value,
                "googleAdsCampaignId": row.dimension_values[2].value,
                "keyEvents": float(row.metric_values[0].value),
                "advertiserAdCost": float(row.metric_values[1].value),
                "advertiserAdCostPerKeyEvent": float(row.metric_values[2].value),
                "advertiserAdImpressions": int(float(row.metric_values[3].value)),
                "advertiserAdClicks": int(float(row.metric_values[4].value)),
                "advertiserAdCostPerClick": float(row.metric_values[5].value),
                "purchaseRevenue": float(row.metric_values[6].value),
                "returnOnAdSpend": float(row.metric_values[7].value),
            }
            for row in response.rows
        ]

        # KROK 7 — zapis do BigQuery: projekt bierzemy z konta usługi,
        # dataset i tabelę ze zmiennych środowiskowych.
        table_ref = f"{bq_client.project}.{DATASET_ID}.{TABLE_ID}"
        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)

        # Kod HTTP dla Cloud Scheduler: 200 = sukces, 500 = błąd zapisu.
        # Dzięki 500 harmonogram widzi nieudane uruchomienie i może je ponowić.
        if not errors:
            return json.dumps({"message": "Dane zostały pomyślnie zapisane."}), 200
        return json.dumps({"error": f"Wystąpiły błędy: {errors}"}), 500

    # Każdy inny błąd (brak uprawnień, limit API, zła zmienna) też zwraca 500
    # z opisem — błąd ma być widoczny w logach, a nie ginąć po cichu.
    except Exception as e:
        return json.dumps({"error": str(e)}), 500


# ----------------------------------------------------------------------------
# CO POPRAWIŁBYM DZIŚ (odpowiedź na „co zrobiłby Pan lepiej?”)
#   1. Idempotentność: insert_rows_json dogrywa wiersze, więc ponowne
#      uruchomienie za ten sam dzień dubluje dane. Lepiej: zadanie ładowania
#      z nadpisaniem partycji dnia (WRITE_TRUNCATE) albo MERGE po dacie i kampanii.
#   2. Paginacja: run_report zwraca domyślnie do 10 000 wierszy; przy
#      szczegółowszym raporcie wynik byłby po cichu ucięty. Lepiej: sprawdzić
#      response.row_count i dociągać kolejne porcje przez limit/offset.
#   3. Format daty: GA4 zwraca date jako RRRRMMDD, a kolumna `date` w tabeli
#      ma typ DATE — przed zapisem przeformatować na RRRR-MM-DD.
#   4. Typy: keyEvents jest rzutowane na float, a w tabeli to INT64 — ujednolicić.
#   5. Kontrola kompletności po zapisie (czy dzień ma wiersze) z alertem.
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# Przykładowy wynik (dane syntetyczne): wiersze w tabeli BigQuery
#
# Jeden dzień (sprzed 2 dni) na uruchomienie, typy wg create_table_bq.sql.
# Odpowiedź HTTP: 200 {"message": "Dane zostały pomyślnie zapisane."} albo 500 {"error": "..."}.
#
# | date | googleAdsCampaignName | googleAdsCampaignId | keyEvents | advertiserAdCost | advertiserAdCostPerKeyEvent | advertiserAdImpressions | advertiserAdClicks | advertiserAdCostPerClick | purchaseRevenue | returnOnAdSpend |
# |---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
# | 2026-10-31 | PL_Search_Brand | 21034567811 | 48 | 312.40 | 6.51 | 4120 | 655 | 0.48 | 9420.50 | 30.16 |
# | 2026-10-31 | PL_Search_Generic | 21034567812 | 61 | 1840.90 | 30.18 | 52300 | 2210 | 0.83 | 41230.00 | 22.40 |
# | 2026-10-31 | PL_PMax_Wszystkie_produkty | 21034567813 | 97 | 2950.00 | 30.41 | 210400 | 3120 | 0.95 | 69870.25 | 23.68 |
# | 2026-10-31 | PL_Display_Remarketing | 21034567814 | 12 | 640.20 | 53.35 | 380500 | 1015 | 0.63 | 6210.80 | 9.70 |
# | 2026-10-31 | PL_YouTube_Zasięg | 21034567815 | 3 | 1200.00 | 400.00 | 455000 | 690 | 1.74 | 590.00 | 0.49 |
