"""
Google Cloud Function (HTTP) uruchamiana codziennie przez Cloud Scheduler.
Pobiera z GA4 Data API dzienny raport kosztów i konwersji kampanii Google Ads
i zapisuje go do partycji dnia w BigQuery (tabela: create_table_bq_v2.sql).

Uwierzytelnianie: Application Default Credentials — w Cloud Functions to konto usługi
przypisane do funkcji (Viewer we właściwości GA4, BigQuery Data Editor w datasecie).

Zmienne środowiskowe (konfiguracja Cloud Function):
- GA4_PROPERTY_ID   — ID właściwości GA4 (bez prefiksu "properties/")
- BQ_DATASET_ID     — dataset docelowy w BigQuery
- BQ_TABLE_ID       — tabela docelowa w BigQuery (partycjonowana po `date`)

Opcjonalnie w treści żądania: {"date": "RRRR-MM-DD"} — przeliczenie albo uzupełnienie
konkretnego dnia (backfill).
"""

# ============================================================================
# JAK OPOWIEDZIEĆ TEN SKRYPT — 8 kroków (komentarze „KROK n” niżej w kodzie)
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

# --- Biblioteki standardowe Pythona (wbudowane, bez instalacji) ---
import json  # zamiana słowników na tekst JSON: odpowiedź HTTP i logi
import os  # odczyt zmiennych środowiskowych (konfiguracja funkcji)
from datetime import date, datetime, timedelta  # daty: „przedwczoraj”, parsowanie i formatowanie

# --- Biblioteki Google (instalacja: pip install google-analytics-data google-cloud-bigquery) ---
# Klient GA4 Data API — wysyła zapytania o raporty do właściwości GA4.
from google.analytics.data_v1beta import BetaAnalyticsDataClient
# Klocki zapytania: zakres dat, wymiar, metryka i całe zapytanie o raport.
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
# Typy błędów zwracanych przez API Google (np. 429 = za dużo zapytań, 503 = usługa niedostępna).
from google.api_core import exceptions as api_exceptions
# Mechanizm ponawiania wywołań z rosnącym odstępem (exponential backoff).
from google.api_core import retry as api_retry
# Klient BigQuery — ładowanie danych do tabeli i zapytania SQL.
from google.cloud import bigquery

# KROK 2 — konfiguracja ze zmiennych środowiskowych: ten sam kod działa dla innej
# właściwości albo tabeli, a brak zmiennej kończy się błędem od razu przy starcie.
PROPERTY_ID = f"properties/{os.environ['GA4_PROPERTY_ID']}"
DATASET_ID = os.environ["BQ_DATASET_ID"]
TABLE_ID = os.environ["BQ_TABLE_ID"]

# Rozmiar jednej strony wyników. GA4 Data API zwraca domyślnie do 10 000 wierszy
# na zapytanie; jawny limit + offset pozwala pobrać wszystko w kolejnych porcjach.
PAGE_SIZE = 10_000

# Wymiary = po czym GA4 grupuje wiersze raportu (jeden wiersz = dzień × kampania).
DIMENSIONS = ["date", "googleAdsCampaignName", "googleAdsCampaignId"]
# Metryki = co GA4 liczy dla każdego wiersza. Kolejność ma znaczenie: w tej samej
# kolejności wracają wartości w odpowiedzi (row.metric_values).
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
    initial=2.0,      # pierwsza przerwa przed ponowieniem: 2 s
    maximum=60.0,     # najdłuższa pojedyncza przerwa: 60 s
    multiplier=2.0,   # każda kolejna przerwa 2× dłuższa: 2, 4, 8, 16... s
    timeout=300.0,    # po 5 minutach prób — rezygnujemy i zgłaszamy błąd
)


# Logowanie strukturalne — zamiast zwykłego tekstu każdy wpis jest jedną linią JSON.
# Cloud Functions przekazuje wszystko, co trafia na standardowe wyjście (print), do
# Cloud Logging. Gdy linia jest poprawnym JSON-em, Cloud Logging rozbija ją na pola:
# - `severity` ustawia poziom wpisu (INFO, WARNING, ERROR) — po nim filtrujesz logi
#   i ustawiasz alert, np. „powiadom, gdy pojawi się ERROR z tej funkcji”,
# - `message` to treść widoczna na liście logów,
# - pozostałe pola (np. date, rows) są osobnymi, przeszukiwalnymi polami wpisu.
# Przykład wywołania: log("ERROR", "Niekompletny zapis", date="2026-10-31", api_rows=5)
# daje linię: {"severity": "ERROR", "message": "Niekompletny zapis", "date": "2026-10-31", "api_rows": 5}
def log(severity, message, **fields):
    """Log strukturalny: Cloud Logging odczytuje JSON z stdout i pole `severity`."""
    # **fields zbiera dowolne dodatkowe argumenty nazwane (date=..., rows=...) w słownik,
    # a {..., **fields} dokleja je do wpisu obok severity i message.
    # json.dumps zamienia słownik na tekst JSON; ensure_ascii=False zostawia polskie
    # znaki czytelne („Zapisano partycję”) zamiast kodów w rodzaju \u0119.
    print(json.dumps({"severity": severity, "message": message, **fields}, ensure_ascii=False))


# KROK 3 — zakres dat. Domyślnie przedwczoraj; data z treści żądania
# ({"date": "2026-10-30"}) pozwala ponownie przeliczyć albo uzupełnić konkretny dzień.
def resolve_report_date(request):
    # Treść żądania jako JSON; silent=True zwraca None zamiast błędu, gdy treść jest
    # pusta albo nie jest JSON-em (harmonogram zwykle wysyła puste żądanie).
    payload = request.get_json(silent=True) if request is not None else None
    if payload and payload.get("date"):
        # Data podana ręcznie, np. przy uzupełnianiu historii: tekst -> obiekt daty.
        return datetime.strptime(payload["date"], "%Y-%m-%d").date()
    # Domyślnie: dzisiaj minus 2 dni.
    return date.today() - timedelta(days=2)


# KROK 5 — pobranie wszystkich wierszy z paginacją (limit + offset).
# Pętla kończy się, gdy pobierzemy tyle wierszy, ile API zgłasza w row_count,
# albo gdy strona przyjdzie pusta.
def fetch_all_rows(client, report_date):
    day = report_date.strftime("%Y-%m-%d")  # GA4 przyjmuje daty jako tekst RRRR-MM-DD
    rows, offset, total = [], 0, None        # zebrane wiersze, pozycja startu strony, suma z API
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
        rows.extend(response.rows)              # dołącz wiersze tej strony do wyniku
        offset += len(response.rows)            # następna strona zaczyna się za tą
        if not response.rows or offset >= total:  # pusta strona albo komplet = koniec
            return rows, total


# KROK 6 — transformacja jednego wiersza GA4 do formatu tabeli.
# GA4 zwraca wartości jako tekst w kolejności z DIMENSIONS i METRICS.
def to_record(row):
    # zip łączy w pary nazwę wymiaru z jego wartością: ("date", "20261031"),
    # ("googleAdsCampaignName", "PL_Search_Brand")...; z par powstaje słownik.
    record = {name: value.value for name, value in zip(DIMENSIONS, row.dimension_values)}
    # Data: GA4 zwraca RRRRMMDD, kolumna DATE w BigQuery wymaga RRRR-MM-DD.
    record["date"] = datetime.strptime(record["date"], "%Y%m%d").strftime("%Y-%m-%d")
    # To samo dla metryk: nazwa metryki + wartość, tekst zamieniony na liczbę.
    for name, value in zip(METRICS, row.metric_values):
        number = float(value.value)
        # Liczniki zaokrąglamy do liczby całkowitej (GA4 potrafi zwrócić "12.0").
        record[name] = int(round(number)) if name in INT_METRICS else number
    return record


# KROK 7 — zapis idempotentny: zadanie ładowania do jednej partycji dnia
# (dekorator tabela$RRRRMMDD) w trybie WRITE_TRUNCATE. Ponowne uruchomienie
# za ten sam dzień zastępuje jego dane zamiast je dublować.
def load_partition(bq_client, records, report_date):
    table_ref = f"{bq_client.project}.{DATASET_ID}.{TABLE_ID}"           # projekt.dataset.tabela
    partition = f"{table_ref}${report_date.strftime('%Y%m%d')}"         # np. ...tabela$20261031 = tylko ten dzień
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,     # zastąp zawartość partycji
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,     # rekordy wysyłane jako JSON
    )
    # Zadanie ładowania (load job) zamiast wstawiania strumieniowego; .result() czeka,
    # aż BigQuery skończy, i rzuca wyjątek, jeśli ładowanie się nie uda.
    bq_client.load_table_from_json(records, partition, job_config=job_config).result()
    return table_ref


# KROK 8 — kontrola kompletności: ile wierszy jest w partycji po zapisie.
def count_partition_rows(bq_client, table_ref, report_date):
    # @day to parametr zapytania: wartość przekazujemy osobno, zamiast wklejać ją do
    # tekstu SQL — bezpieczniej i bez problemów z formatem daty.
    query = f"SELECT COUNT(*) AS n FROM `{table_ref}` WHERE date = @day"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("day", "DATE", report_date)]
    )
    # Wynik zapytania to jeden wiersz z kolumną n — zwracamy samą liczbę.
    return list(bq_client.query(query, job_config=job_config).result())[0].n


# KROK 1 — punkt wejścia funkcji HTTP (wywołuje go Cloud Scheduler).
def ga4_api_gads(request):
    try:
        report_date = resolve_report_date(request)

        # KROK 4 — klienci API przez Application Default Credentials: konto usługi
        # przypisane do funkcji, bez pliku klucza w kodzie i w repo.
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
# PRZED JAKIMI BŁĘDAMI CHRONI TEN KOD (odpowiedź na „na co Pan uważał?”)
#   1. Duplikaty przy ponownym uruchomieniu: load job z WRITE_TRUNCATE na partycji
#      dnia — ponowienie za ten sam dzień zastępuje dane zamiast je dublować.
#   2. Ucięty raport: pętla limit/offset do row_count — raport większy niż
#      10 000 wierszy (domyślny limit API) jest pobierany w całości.
#   3. Zły format daty: GA4 zwraca RRRRMMDD, kolumna DATE wymaga RRRR-MM-DD.
#   4. Niezgodne typy: liczniki jako liczby całkowite, zgodnie ze schematem INT64.
#   5. Cichy niekompletny zapis: liczba wierszy w partycji porównana z row_count;
#      niezgodność = log ERROR i kod 500 dla harmonogramu.
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
