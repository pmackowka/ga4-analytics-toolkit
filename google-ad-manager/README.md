# Google Ad Manager API — przykłady raportów

Skrypty do [Ad Manager API](https://developers.google.com/ad-manager/api) przez bibliotekę [`googleads-python-lib`](https://github.com/googleads/googleads-python-lib).

## Co jest czyje

- `ad-manager.py`, `run_delivery_report.py`, `run_inventory_report.py`, `run_reach_report.py`, `run_reach_report_with_ad_unit_dimensions.py` — oficjalne przykłady kodu z biblioteki Google (Apache 2.0), zachowane jako materiał referencyjny, w kilku miejscach z drobną adaptacją (patrz nagłówki plików).
- `run_reach_report-2.py` — własna wersja raportu reach z innym zestawem wymiarów/kolumn (device category, creative, line item, order) i zapisem wyniku jako skompresowany `.csv.gz`.

## Setup

1. `pip install googleads`
2. Utwórz plik `googleads.yaml` wg [instrukcji Google](https://github.com/googleads/googleads-python-lib#configuration) i umieść go w katalogu domowym (`~/googleads.yaml`) — `AdManagerClient.LoadFromStorage()` znajdzie go tam automatycznie bez podawania ścieżki.
3. Uruchom dowolny skrypt, np. `python ad-manager.py`.
