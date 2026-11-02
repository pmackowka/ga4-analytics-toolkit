# GA4 Data API

Przykłady użycia [GA4 Data API](https://developers.google.com/analytics/devguides/reporting/data/v1) w Pythonie — od jednorazowego raportu do automatycznego codziennego importu do BigQuery.

## Setup (wspólny dla wszystkich skryptów)

1. Utwórz projekt GCP i włącz Google Analytics Data API.
2. Utwórz konto serwisowe i klucz JSON do niego.
3. Dodaj to konto serwisowe jako "Viewer" do właściwości GA4 (Admin -> Zarządzanie dostępem do usługi).
4. `pip install google-analytics-data`
5. Ustaw zmienne środowiskowe:
   - `GA4_CREDENTIALS_PATH` — ścieżka do pliku JSON z kroku 2
   - `GA4_PROPERTY_ID` — ID właściwości GA4 (liczba, bez prefiksu `properties/`)

## Zawartość

- **`ga4_python_report_tutorial.ipynb`** — wprowadzenie: `run_report` → `pandas.DataFrame` → wykres/eksport CSV/Excel.
- **`reports/`** — gotowe, jednorazowe raporty CLI (demografia użytkowników, koszty/konwersje Google Ads widoczne w GA4).
- **`bigquery-pipeline/`** — Cloud Function pobierająca codziennie dane kosztów Ads z GA4 i dogrywająca je do BigQuery (`create_table_bq.sql` + `gads_costs_to_bigquery_cloud_function.py`). Cloud Function korzysta z Application Default Credentials konta usługi funkcji, a nie z pliku JSON — potrzebuje zmiennych `GA4_PROPERTY_ID`, `BQ_DATASET_ID`, `BQ_TABLE_ID`.

## Linki

- [Quickstart](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries)
- [Wymiary i metryki API](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)
- [Referencja Python](https://googleapis.dev/python/analyticsdata/latest/data_v1beta/beta_analytics_data.html)
