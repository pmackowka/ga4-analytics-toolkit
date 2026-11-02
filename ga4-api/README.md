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

## Przykładowe wyniki (dane syntetyczne)

Struktura plików wynikowych każdego skryptu: wszystkie kolumny w kolejności z kodu, 5–7 zmyślonych wierszy. GA4 Data API zwraca każdą wartość jako tekst — `date` w formacie `RRRRMMDD`, liczby jako ciągi znaków; poniżej tak, jak trafiają do CSV.

### `reports/gads_conversions_report.py` → `output_gads_conversions.csv`

Jeden wiersz na kampanię Google Ads i dzień. `advertiserAdCostPerKeyEvent` = koszt / kluczowe zdarzenia, `advertiserAdCostPerClick` = koszt / kliknięcia, `returnOnAdSpend` = przychód / koszt (ułamek, nie procent).

| date | googleAdsCampaignName | googleAdsCampaignId | keyEvents | advertiserAdCost | advertiserAdCostPerKeyEvent | advertiserAdImpressions | advertiserAdClicks | advertiserAdCostPerClick | purchaseRevenue | returnOnAdSpend |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20240601 | PL_Search_Brand | 21034567811 | 48 | 312.40 | 6.51 | 4120 | 655 | 0.48 | 9420.50 | 30.16 |
| 20240601 | PL_Search_Generic | 21034567812 | 61 | 1840.90 | 30.18 | 52300 | 2210 | 0.83 | 41230.00 | 22.40 |
| 20240601 | PL_PMax_Wszystkie_produkty | 21034567813 | 97 | 2950.00 | 30.41 | 210400 | 3120 | 0.95 | 69870.25 | 23.68 |
| 20240601 | PL_Display_Remarketing | 21034567814 | 12 | 640.20 | 53.35 | 380500 | 1015 | 0.63 | 6210.80 | 9.70 |
| 20240601 | PL_YouTube_Zasięg | 21034567815 | 3 | 1200.00 | 400.00 | 455000 | 690 | 1.74 | 590.00 | 0.49 |

### `reports/user_demographics_report.py` → `output_user_demographics.csv`

Jeden wiersz na przedział wiekowy. `unknown` to użytkownicy bez danych demograficznych (brak sygnałów Google lub próg prywatności).

| date | userAgeBracket | activeUsers |
|---|---|---:|
| 20240701 | 18-24 | 4120 |
| 20240701 | 25-34 | 9875 |
| 20240701 | 35-44 | 8430 |
| 20240701 | 45-54 | 5210 |
| 20240701 | 55-64 | 2380 |
| 20240701 | 65+ | 1105 |
| 20240701 | unknown | 14630 |

### `reports/test_imports.py` → tylko komunikat w konsoli

```
Wszystkie biblioteki zostały zaimportowane poprawnie.
```

### `bigquery-pipeline/gads_costs_to_bigquery_cloud_function.py` → wiersze w tabeli BigQuery

Te same kolumny co w `gads_conversions_report.py`, jeden dzień (sprzed 2 dni) na uruchomienie, typy wg `create_table_bq.sql`. Funkcja zwraca HTTP 200 z `{"message": "Dane zostały pomyślnie zapisane."}` albo 500 z opisem błędu.

| date | googleAdsCampaignName | googleAdsCampaignId | keyEvents | advertiserAdCost | advertiserAdCostPerKeyEvent | advertiserAdImpressions | advertiserAdClicks | advertiserAdCostPerClick | purchaseRevenue | returnOnAdSpend |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-31 | PL_Search_Brand | 21034567811 | 48 | 312.40 | 6.51 | 4120 | 655 | 0.48 | 9420.50 | 30.16 |
| 2026-10-31 | PL_Search_Generic | 21034567812 | 61 | 1840.90 | 30.18 | 52300 | 2210 | 0.83 | 41230.00 | 22.40 |
| 2026-10-31 | PL_PMax_Wszystkie_produkty | 21034567813 | 97 | 2950.00 | 30.41 | 210400 | 3120 | 0.95 | 69870.25 | 23.68 |
| 2026-10-31 | PL_Display_Remarketing | 21034567814 | 12 | 640.20 | 53.35 | 380500 | 1015 | 0.63 | 6210.80 | 9.70 |
| 2026-10-31 | PL_YouTube_Zasięg | 21034567815 | 3 | 1200.00 | 400.00 | 455000 | 690 | 1.74 | 590.00 | 0.49 |

## Linki

- [Quickstart](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries)
- [Wymiary i metryki API](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)
- [Referencja Python](https://googleapis.dev/python/analyticsdata/latest/data_v1beta/beta_analytics_data.html)
