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

## SOAP (archiwalne)

### Co jest czyje

- `ad-manager.py`, `run_delivery_report.py`, `run_inventory_report.py`, `run_reach_report.py`, `run_reach_report_with_ad_unit_dimensions.py` — oficjalne przykłady kodu z biblioteki Google (Apache 2.0), zachowane jako materiał referencyjny, w kilku miejscach z drobną adaptacją (patrz nagłówki plików).
- `run_reach_report-2.py` — własna wersja raportu reach z innym zestawem wymiarów/kolumn (device category, creative, line item, order) i zapisem wyniku jako skompresowany `.csv.gz`.

### Setup

1. `pip install googleads`
2. Utwórz plik `googleads.yaml` wg [instrukcji Google](https://github.com/googleads/googleads-python-lib#configuration) i umieść go w katalogu domowym (`~/googleads.yaml`) — `AdManagerClient.LoadFromStorage()` znajdzie go tam automatycznie bez podawania ścieżki.
3. Uruchom dowolny skrypt, np. `python ad-manager.py`.
