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
