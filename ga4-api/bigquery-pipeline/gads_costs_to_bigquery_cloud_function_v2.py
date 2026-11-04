"""
Wersja 2 Cloud Function z gads_costs_to_bigquery_cloud_function.py — te same dane
(koszty i konwersje kampanii Google Ads z GA4 Data API), z poprawkami z sekcji
„CO POPRAWIŁBYM DZIŚ” w wersji 1:

1. Idempotentny zapis: nadpisanie partycji dnia zamiast dogrywania wierszy.
2. Paginacja: dociąganie kolejnych porcji, aż pobierze się row_count wierszy.
3. Format daty: RRRRMMDD z GA4 -> RRRR-MM-DD dla kolumny DATE.
4. Typy zgodne ze schematem tabeli (keyEvents jako INT64).
5. Kontrola kompletności po zapisie + logi strukturalne do Cloud Logging.
Dodatkowo: ponawianie przy chwilowych błędach API i opcjonalna data w żądaniu
(do uzupełniania historii, czyli backfillu).

Tabela docelowa: create_table_bq_v2.sql (partycjonowana po `date`).
Uwierzytelnianie i zmienne środowiskowe — jak w wersji 1.
"""

# ============================================================================
# JAK OPOWIEDZIEĆ TĘ WERSJĘ — 8 kroków (komentarze „KROK n” niżej w kodzie)
#   1. Uruchomienie: Cloud Scheduler wywołuje funkcję przez HTTP; opcjonalnie
#      w treści żądania można podać datę, żeby uzupełnić konkretny dzień.
#   2. Konfiguracja ze zmiennych środowiskowych, bez wartości w kodzie.
#   3. Zakres dat: domyślnie przedwczoraj (opóźnienie danych Ads w GA4 do 48 h).
#   4. Uwierzytelnienie: konto usługi przypisane do funkcji (ADC), bez klucza.
#   5. Pobranie z GA4 Data API z paginacją i ponawianiem przy chwilowych błędach.
#   6. Transformacja: data w formacie DATE, typy zgodne ze schematem tabeli.
#   7. Zapis idempotentny: nadpisanie partycji dnia (WRITE_TRUNCATE).
#   8. Kontrola kompletności: liczba wierszy w partycji = liczba z API, log + kod HTTP.
# ============================================================================

import json
import os
from datetime import date, datetime, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.api_core import exceptions as api_exceptions
from google.api_core import retry as api_retry
from google.cloud import bigquery

# KROK 2 — konfiguracja ze zmiennych środowiskowych (jak w wersji 1).
PROPERTY_ID = f"properties/{os.environ['GA4_PROPERTY_ID']}"
DATASET_ID = os.environ["BQ_DATASET_ID"]
TABLE_ID = os.environ["BQ_TABLE_ID"]

# Rozmiar jednej strony wyników. GA4 Data API zwraca domyślnie do 10 000 wierszy
# na zapytanie; jawny limit + offset pozwala pobrać wszystko w kolejnych porcjach.
PAGE_SIZE = 10_000

DIMENSIONS = ["date", "googleAdsCampaignName", "googleAdsCampaignId"]
METRICS = [
    "keyEvents",
    "advertiserAdCost",
    "advertiserAdCostPerKeyEvent",
    "advertiserAdImpressions",
    "advertiserAdClicks",
    "advertiserAdCostPerClick",
    "purchaseRevenue",
    "returnOnAdSpend",
]
# Metryki zapisywane jako INT64 (liczniki); reszta jako FLOAT64 (kwoty i ilorazy).
INT_METRICS = {"keyEvents", "advertiserAdImpressions", "advertiserAdClicks"}

# Ponawianie wywołań API: chwilowe błędy serwera i przekroczenie limitu (429)
# ponawiamy z rosnącym odstępem, do 5 minut łącznie; inne błędy przerywają od razu.
GA4_RETRY = api_retry.Retry(
    predicate=api_retry.if_exception_type(
        api_exceptions.ServiceUnavailable,
        api_exceptions.InternalServerError,
        api_exceptions.TooManyRequests,
        api_exceptions.ResourceExhausted,
    ),
    initial=2.0,
    maximum=60.0,
    multiplier=2.0,
    timeout=300.0,
)


def log(severity, message, **fields):
    """Log strukturalny: Cloud Logging odczytuje JSON z stdout i pole `severity`."""
    print(json.dumps({"severity": severity, "message": message, **fields}, ensure_ascii=False))


# KROK 3 — zakres dat. Domyślnie przedwczoraj; data z treści żądania
# ({"date": "2026-10-30"}) pozwala ponownie przeliczyć albo uzupełnić konkretny dzień.
def resolve_report_date(request):
    payload = request.get_json(silent=True) if request is not None else None
    if payload and payload.get("date"):
        return datetime.strptime(payload["date"], "%Y-%m-%d").date()
    return date.today() - timedelta(days=2)


# KROK 5 — pobranie wszystkich wierszy z paginacją (limit + offset).
# Pętla kończy się, gdy pobierzemy tyle wierszy, ile API zgłasza w row_count,
# albo gdy strona przyjdzie pusta.
def fetch_all_rows(client, report_date):
    day = report_date.strftime("%Y-%m-%d")
    rows, offset, total = [], 0, None
    while True:
        request = RunReportRequest(
            property=PROPERTY_ID,
            dimensions=[Dimension(name=d) for d in DIMENSIONS],
            metrics=[Metric(name=m) for m in METRICS],
            date_ranges=[DateRange(start_date=day, end_date=day)],
            limit=PAGE_SIZE,
            offset=offset,
        )
        response = client.run_report(request, retry=GA4_RETRY)
        total = response.row_count  # łączna liczba wierszy raportu (wszystkie strony)
        rows.extend(response.rows)
        offset += len(response.rows)
        if not response.rows or offset >= total:
            return rows, total


# KROK 6 — transformacja jednego wiersza GA4 do formatu tabeli.
# GA4 zwraca wartości jako tekst w kolejności z DIMENSIONS i METRICS.
def to_record(row):
    record = {name: value.value for name, value in zip(DIMENSIONS, row.dimension_values)}
    # Data: GA4 zwraca RRRRMMDD, kolumna DATE w BigQuery wymaga RRRR-MM-DD.
    record["date"] = datetime.strptime(record["date"], "%Y%m%d").strftime("%Y-%m-%d")
    for name, value in zip(METRICS, row.metric_values):
        number = float(value.value)
        # Liczniki zaokrąglamy do liczby całkowitej (GA4 potrafi zwrócić "12.0").
        record[name] = int(round(number)) if name in INT_METRICS else number
    return record


# KROK 7 — zapis idempotentny: zadanie ładowania do jednej partycji dnia
# (dekorator tabela$RRRRMMDD) w trybie WRITE_TRUNCATE. Ponowne uruchomienie
# za ten sam dzień zastępuje jego dane zamiast je dublować.
def load_partition(bq_client, records, report_date):
    table_ref = f"{bq_client.project}.{DATASET_ID}.{TABLE_ID}"
    partition = f"{table_ref}${report_date.strftime('%Y%m%d')}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    bq_client.load_table_from_json(records, partition, job_config=job_config).result()
    return table_ref


# KROK 8 — kontrola kompletności: ile wierszy jest w partycji po zapisie.
def count_partition_rows(bq_client, table_ref, report_date):
    query = f"SELECT COUNT(*) AS n FROM `{table_ref}` WHERE date = @day"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("day", "DATE", report_date)]
    )
    return list(bq_client.query(query, job_config=job_config).result())[0].n


# KROK 1 — punkt wejścia funkcji HTTP (wywołuje go Cloud Scheduler).
def ga4_api_gads(request):
    try:
        report_date = resolve_report_date(request)

        # KROK 4 — klienci API przez Application Default Credentials (jak w wersji 1).
        client = BetaAnalyticsDataClient()
        bq_client = bigquery.Client()

        rows, api_total = fetch_all_rows(client, report_date)
        records = [to_record(row) for row in rows]

        if not records:
            # Brak wierszy to nie zawsze błąd (np. dzień bez aktywnych kampanii),
            # ale ma być widoczny w logach — partycji nie nadpisujemy pustą listą.
            log("WARNING", "GA4 zwróciło 0 wierszy", date=str(report_date))
            return json.dumps({"message": "Brak danych za ten dzień.", "date": str(report_date)}), 200

        table_ref = load_partition(bq_client, records, report_date)
        loaded = count_partition_rows(bq_client, table_ref, report_date)

        if loaded != api_total:
            # Niezgodność liczby wierszy = alert (log ERROR + kod 500 dla harmonogramu).
            log("ERROR", "Niekompletny zapis", date=str(report_date), api_rows=api_total, loaded_rows=loaded)
            return json.dumps({"error": f"API: {api_total} wierszy, w tabeli: {loaded}"}), 500

        log("INFO", "Zapisano partycję", date=str(report_date), rows=loaded)
        return json.dumps({"message": "Dane zostały pomyślnie zapisane.", "date": str(report_date), "rows": loaded}), 200

    except Exception as e:
        # Każdy inny błąd: log ERROR z opisem i kod 500, żeby harmonogram widział porażkę.
        log("ERROR", "Błąd funkcji", error=str(e))
        return json.dumps({"error": str(e)}), 500


# ----------------------------------------------------------------------------
# CO ZMIENIŁO SIĘ WZGLĘDEM WERSJI 1 (odpowiedź na „co by Pan poprawił?”)
#   1. insert_rows_json -> load job z WRITE_TRUNCATE na partycji dnia: ponowienie
#      za ten sam dzień nie dubluje danych (wymaga tabeli z create_table_bq_v2.sql).
#   2. Jedno wywołanie run_report -> pętla limit/offset do row_count: raport
#      większy niż 10 000 wierszy nie jest już ucinany po cichu.
#   3. Data RRRRMMDD -> RRRR-MM-DD przed zapisem do kolumny DATE.
#   4. keyEvents zapisywane jako liczba całkowita, zgodnie ze schematem INT64.
#   5. Po zapisie: liczba wierszy w partycji porównana z row_count z API;
#      niezgodność = log ERROR i kod 500.
#   Dodatkowo: ponawianie przy 429/5xx, logi strukturalne, data w żądaniu do backfillu.
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# Przykładowy wynik (dane syntetyczne)
#
# Odpowiedź HTTP przy sukcesie:
#   200 {"message": "Dane zostały pomyślnie zapisane.", "date": "2026-10-31", "rows": 5}
# Log w Cloud Logging:
#   {"severity": "INFO", "message": "Zapisano partycję", "date": "2026-10-31", "rows": 5}
#
# Partycja 2026-10-31 w tabeli BigQuery (date jako DATE, keyEvents jako INT64):
#
# | date | googleAdsCampaignName | googleAdsCampaignId | keyEvents | advertiserAdCost | advertiserAdCostPerKeyEvent | advertiserAdImpressions | advertiserAdClicks | advertiserAdCostPerClick | purchaseRevenue | returnOnAdSpend |
# |---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
# | 2026-10-31 | PL_Search_Brand | 21034567811 | 48 | 312.40 | 6.51 | 4120 | 655 | 0.48 | 9420.50 | 30.16 |
# | 2026-10-31 | PL_Search_Generic | 21034567812 | 61 | 1840.90 | 30.18 | 52300 | 2210 | 0.83 | 41230.00 | 22.40 |
# | 2026-10-31 | PL_PMax_Wszystkie_produkty | 21034567813 | 97 | 2950.00 | 30.41 | 210400 | 3120 | 0.95 | 69870.25 | 23.68 |
# | 2026-10-31 | PL_Display_Remarketing | 21034567814 | 12 | 640.20 | 53.35 | 380500 | 1015 | 0.63 | 6210.80 | 9.70 |
# | 2026-10-31 | PL_YouTube_Zasięg | 21034567815 | 3 | 1200.00 | 400.00 | 455000 | 690 | 1.74 | 590.00 | 0.49 |
#
# Ponowne uruchomienie z {"date": "2026-10-31"} daje te same 5 wierszy, nie 10.
