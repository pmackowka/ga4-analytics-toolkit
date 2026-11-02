# Google Ad Manager API — przykłady raportów

> **Folder archiwalny.** Skrypty w tym katalogu korzystają z SOAP API Ad Managera (biblioteka [`googleads-python-lib`](https://github.com/googleads/googleads-python-lib), wersja `v202402`). Google oznacza SOAP API jako starsze i zaleca [Ad Manager API (Beta) w REST](https://developers.google.com/ad-manager/api/beta/migration); każda wersja SOAP jest wspierana przez ok. rok ([harmonogram](https://developers.google.com/ad-manager/api/deprecation)), a `v202402` jest starsza niż najstarsza wersja w harmonogramie. Zostają jako materiał referencyjny. Aktualny odpowiednik raportu delivery w REST: [`rest/run_delivery_report.py`](rest/run_delivery_report.py).

## REST — `rest/run_delivery_report.py`

Ten sam raport co `run_delivery_report.py` (wymiary zamówienia, wyświetlenia, kliknięcia, CTR, przychód i eCPM z ostatnich 8 dni, jedno zamówienie, wynik w `.csv.gz`) przez bibliotekę [`google-ads-admanager`](https://googleapis.dev/python/google-ads-admanager/latest/admanager_v1/report_service.html), która łączy się z API przez REST.

| | SOAP (`run_delivery_report.py`) | REST (`rest/run_delivery_report.py`) |
|---|---|---|
| Biblioteka | `googleads` | `google-ads-admanager` (`admanager_v1`) |
| Przebieg | `WaitForReport` → `DownloadReportToFile` | `create_report` → `run_report` (operacja długotrwała) → `fetch_report_result_rows` (paginacja) |
| Filtr | PQL z bind variable (`ORDER_ID = :id`) | struktura `Filter` (`ORDER_ID IN [id]`) |
| Atrybuty zamówienia | `dimensionAttributes` | zwykłe wymiary |
| Przychód i eCPM | `AD_SERVER_CPM_AND_CPC_REVENUE`, `AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM` | `AD_SERVER_REVENUE_WITHOUT_CPD`, `AD_SERVER_AVERAGE_ECPM_WITHOUT_CPD` |
| Uwierzytelnianie | plik `googleads.yaml` | Application Default Credentials |

Setup:

1. W projekcie GCP włącz Ad Manager API.
2. `pip install google-ads-admanager`
3. Uwierzytelnienie: `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/admanager,https://www.googleapis.com/auth/cloud-platform` albo konto usługi dodane jako użytkownik w sieci Ad Managera.
4. `python rest/run_delivery_report.py --network-code <kod_sieci> --order-id <id_zamówienia>`

Skrypt tworzy przy każdym uruchomieniu ukryty raport (`HIDDEN`). Przy cyklicznym uruchamianiu utwórz raport raz i podawaj `--report-id`.

### Przykładowy wynik (dane syntetyczne)

Plik `.csv.gz` ma jeden wiersz na zamówienie i dziesięć kolumn: pięć wymiarów, potem pięć metryk, w kolejności z `DIMENSIONS` i `METRICS`. Przy filtrze `--order-id` raport zwraca jeden wiersz — tabela pokazuje sześć zamówień naraz, żeby było widać zakres wartości. Wszystkie wartości są zmyślone.

| ORDER_ID | ORDER_NAME | ORDER_TRAFFICKER | ORDER_START_DATE_TIME | ORDER_END_DATE_TIME | AD_SERVER_IMPRESSIONS | AD_SERVER_CLICKS | AD_SERVER_CTR | AD_SERVER_REVENUE_WITHOUT_CPD | AD_SERVER_AVERAGE_ECPM_WITHOUT_CPD |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| 3412000001 | 2026-10 - Marka A - Display homepage | Trafficker A | 2026-10-01 00:00 | 2026-10-31 23:59 | 1854200 | 2967 | 0.0016 | 8901.60 | 4.80 |
| 3412000002 | 2026-10 - Marka B - Video pre-roll | Trafficker B | 2026-10-15 00:00 | 2026-11-15 23:59 | 642300 | 1092 | 0.0017 | 15415.20 | 24.00 |
| 3412000003 | Q4 - Marka C - Sponsoring sekcji Sport | Trafficker A | 2026-10-01 00:00 | 2026-12-31 23:59 | 2310500 | 3466 | 0.0015 | 9242.00 | 4.00 |
| 3412000004 | 2026-10 - Marka D - Native artykuł | Trafficker C | 2026-10-20 00:00 | 2026-10-27 23:59 | 187400 | 749 | 0.0040 | 1124.40 | 6.00 |
| 3412000005 | House - Autopromocja serwisu | Trafficker B | 2026-01-01 00:00 |  | 3980100 | 2388 | 0.0006 | 0.00 | 0.00 |
| 3412000006 | 2026-10 - Marka E - Mobile interstitial | Trafficker C | 2026-10-25 00:00 | 2026-11-08 23:59 | 421900 | 1561 | 0.0037 | 4219.00 | 10.00 |

- `AD_SERVER_CTR` to ułamek (kliknięcia / wyświetlenia), nie procent.
- `AD_SERVER_AVERAGE_ECPM_WITHOUT_CPD` = przychód / wyświetlenia × 1000.
- Puste `ORDER_END_DATE_TIME` = zamówienie bez daty końca; przychód 0 = kampania wewnętrzna (house).
- Formatu dat i jednostki przychodu (waluta sieci czy mikrojednostki, jak w SOAP) nie sprawdzono na prawdziwej sieci — zweryfikuj przy pierwszym uruchomieniu.

## SOAP (archiwalne)

### Co jest czyje

- `ad-manager.py`, `run_delivery_report.py`, `run_inventory_report.py`, `run_reach_report.py`, `run_reach_report_with_ad_unit_dimensions.py` — oficjalne przykłady kodu z biblioteki Google (Apache 2.0), zachowane jako materiał referencyjny, w kilku miejscach z drobną adaptacją (patrz nagłówki plików).
- `run_reach_report-2.py` — własna wersja raportu reach z innym zestawem wymiarów/kolumn (device category, creative, line item, order) i zapisem wyniku jako skompresowany `.csv.gz`.

### Setup

1. `pip install googleads`
2. Utwórz plik `googleads.yaml` wg [instrukcji Google](https://github.com/googleads/googleads-python-lib#configuration) i umieść go w katalogu domowym (`~/googleads.yaml`) — `AdManagerClient.LoadFromStorage()` znajdzie go tam automatycznie bez podawania ścieżki.
3. Uruchom dowolny skrypt, np. `python ad-manager.py`.

### Przykładowe wyniki (dane syntetyczne)

Raporty SOAP zapisują plik w formacie `CSV_DUMP` (`.csv.gz`): nagłówki z przedrostkiem `Dimension.`, `DimensionAttribute.` albo `Column.`, kwoty w **mikrojednostkach** waluty sieci (1 zł = 1 000 000), CTR jako ułamek. Wartości są zmyślone; dokładne nagłówki (SOAP potrafi dopisać kolumnę ID do wymiaru z nazwą, np. `Dimension.COUNTRY_CRITERIA_ID`) i format dat sprawdź przy pierwszym uruchomieniu.

#### `ad-manager.py` → tylko komunikat w konsoli

```
Current network has network code '21800000' and display name 'Przykładowa sieć'.
```

#### `run_delivery_report.py` — jedno zamówienie, ostatnie 8 dni

Przy filtrze na jedno zamówienie raport ma jeden wiersz; dwa wiersze pokazują dwa uruchomienia dla różnych zamówień. 8 901 600 000 mikro = 8 901,60 zł.

| Dimension.ORDER_ID | Dimension.ORDER_NAME | DimensionAttribute.ORDER_TRAFFICKER | DimensionAttribute.ORDER_START_DATE_TIME | DimensionAttribute.ORDER_END_DATE_TIME | Column.AD_SERVER_IMPRESSIONS | Column.AD_SERVER_CLICKS | Column.AD_SERVER_CTR | Column.AD_SERVER_CPM_AND_CPC_REVENUE | Column.AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| 3412000001 | 2026-10 - Marka A - Display homepage | Trafficker A | 2026-10-01T00:00:00+02:00 | 2026-10-31T23:59:00+01:00 | 1854200 | 2967 | 0.0016 | 8901600000 | 4800777 |
| 3412000002 | 2026-10 - Marka B - Video pre-roll | Trafficker B | 2026-10-15T00:00:00+02:00 | 2026-11-15T23:59:00+01:00 | 642300 | 1092 | 0.0017 | 15415200000 | 24000000 |

#### `run_inventory_report.py` — jednostki reklamowe, poprzedni tydzień

Jeden wiersz na dzień i jednostkę reklamową, widok hierarchiczny (pełna ścieżka). Wyświetlenia z ad servera + z Ad Exchange = `TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS`.

| Dimension.DATE | Dimension.AD_UNIT_NAME | Column.AD_SERVER_IMPRESSIONS | Column.AD_SERVER_CLICKS | Column.AD_EXCHANGE_LINE_ITEM_LEVEL_IMPRESSIONS | Column.AD_EXCHANGE_LINE_ITEM_LEVEL_CLICKS | Column.TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS | Column.TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-10-26 | serwis » strona-glowna » top_billboard | 213900 | 417 | 198400 | 201 | 412300 | 3215940000 |
| 2026-10-26 | serwis » strona-glowna » rectangle_1 | 145200 | 225 | 210900 | 274 | 356100 | 1816110000 |
| 2026-10-26 | serwis » artykul » inside_text | 197500 | 454 | 301200 | 693 | 498700 | 3191680000 |
| 2026-10-26 | serwis » artykul » sticky_bottom_mobile | 166100 | 581 | 455300 | 1594 | 621400 | 2423460000 |
| 2026-10-27 | serwis » strona-glowna » top_billboard | 228873 | 446 | 212288 | 215 | 441161 | 3441055800 |
| 2026-10-27 | serwis » strona-glowna » rectangle_1 | 155364 | 240 | 225663 | 293 | 381027 | 1943237700 |
| 2026-10-27 | serwis » artykul » inside_text | 211325 | 485 | 322284 | 741 | 533609 | 3415097600 |
| 2026-10-27 | serwis » artykul » sticky_bottom_mobile | 177727 | 621 | 487171 | 1705 | 664898 | 2593102200 |

#### `run_reach_report.py` — zasięg unikalny w całym okresie pozycji

`UNIQUE_REACH_FREQUENCY` = wyświetlenia / unikalni użytkownicy.

| Dimension.COUNTRY_NAME | Dimension.LINE_ITEM_ID | Dimension.LINE_ITEM_NAME | Column.UNIQUE_REACH_FREQUENCY | Column.UNIQUE_REACH_IMPRESSIONS | Column.UNIQUE_REACH |
|---|---|---|---:|---:|---:|
| Polska | 6012000101 | Marka A - Display homepage - CPM | 3.62 | 1854200 | 512400 |
| Polska | 6012000102 | Marka B - Video pre-roll - CPM | 2.13 | 642300 | 301500 |
| Niemcy | 6012000101 | Marka A - Display homepage - CPM | 2.18 | 41200 | 18900 |
| Wielka Brytania | 6012000102 | Marka B - Video pre-roll - CPM | 1.73 | 12800 | 7400 |
| Polska | 6012000103 | Marka C - Sponsoring Sport - CPD | 3.36 | 2310500 | 688100 |

#### `run_reach_report_with_ad_unit_dimensions.py` — zasięg w poprzednim miesiącu, widok płaski jednostek

| Dimension.MONTH_AND_YEAR | Dimension.COUNTRY_NAME | Dimension.AD_UNIT_ID | Dimension.AD_UNIT_NAME | Column.UNIQUE_REACH_FREQUENCY | Column.UNIQUE_REACH_IMPRESSIONS | Column.UNIQUE_REACH |
|---|---|---|---|---:|---:|---:|
| 2026-10 | Polska | 21800000101 | top_billboard | 3.99 | 12455000 | 3120400 |
| 2026-10 | Polska | 21800000102 | rectangle_1 | 3.61 | 10780000 | 2988100 |
| 2026-10 | Polska | 21800000103 | inside_text | 4.41 | 15020000 | 3402700 |
| 2026-10 | Niemcy | 21800000101 | top_billboard | 2.89 | 284000 | 98200 |
| 2026-10 | Wielka Brytania | 21800000103 | inside_text | 2.34 | 96500 | 41300 |

#### `run_reach_report-2.py` — wczoraj, poziom kreacji (plik po rozpakowaniu, data jako `RRRRMMDD`)

Skrypt rozpakowuje `.csv.gz` do `.csv` i zamienia datę z `RRRR-MM-DD` na `RRRRMMDD`. Pozycja `SPONSORSHIP` rozliczana za dzień (CPD) ma przychód tylko w kolumnach „ALL_REVENUE”; pozycja `AD_EXCHANGE` ma przychód tylko w `TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE`.

| Dimension.DATE | Dimension.DEVICE_CATEGORY_NAME | Dimension.CREATIVE_NAME | Dimension.CREATIVE_ID | Dimension.LINE_ITEM_NAME | Dimension.LINE_ITEM_ID | Dimension.LINE_ITEM_TYPE | Dimension.ORDER_ID | Dimension.ORDER_NAME | Column.AD_SERVER_IMPRESSIONS | Column.AD_SERVER_CLICKS | Column.AD_SERVER_CTR | Column.AD_SERVER_CPM_AND_CPC_REVENUE | Column.AD_SERVER_ALL_REVENUE | Column.AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM | Column.TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE | Column.AD_EXCHANGE_COST_PER_CLICK |
|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261101 | Desktop | MarkaA_billboard_970x250 | 138000201 | Marka A - Display homepage - CPM | 6012000101 | STANDARD | 3412000001 | 2026-10 - Marka A - Display homepage | 152300 | 198 | 0.0013 | 731040000 | 731040000 | 4800000 | 731040000 | 0 |
| 20261101 | Smartphone | MarkaA_mobile_300x250 | 138000202 | Marka A - Display homepage - CPM | 6012000101 | STANDARD | 3412000001 | 2026-10 - Marka A - Display homepage | 98400 | 271 | 0.0028 | 472320000 | 472320000 | 4800000 | 472320000 | 0 |
| 20261101 | Desktop | MarkaB_preroll_15s | 138000301 | Marka B - Video pre-roll - CPM | 6012000102 | STANDARD | 3412000002 | 2026-10 - Marka B - Video pre-roll | 41200 | 63 | 0.0015 | 988800000 | 988800000 | 24000000 | 988800000 | 0 |
| 20261101 | Smartphone | MarkaC_sponsoring_sport | 138000401 | Marka C - Sponsoring Sport - CPD | 6012000103 | SPONSORSHIP | 3412000003 | Q4 - Marka C - Sponsoring sekcji Sport | 76800 | 112 | 0.0015 | 0 | 300000000 | 0 | 300000000 | 0 |
| 20261101 | Tablet | AdX_backfill | 138000901 | AdX - backfill | 6012000999 | AD_EXCHANGE | 3412000099 | Ad Exchange | 22100 | 19 | 0.0009 | 0 | 0 | 0 | 40885000 | 420000 |
