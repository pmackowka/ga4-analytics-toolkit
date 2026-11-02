# Własna wersja raportu reach: inne wymiary/kolumny niż w oficjalnym przykładzie Google
# (device category, creative, line item, order) i zapis odpowiedzi jako spakowany .csv.gz
# zamiast trzymania całości w pamięci.
import tempfile
import gzip
import shutil
import os
from datetime import datetime

from googleads import ad_manager
from googleads import errors


def main(client):
    # Initialize a DataDownloader.
    report_downloader = client.GetDataDownloader(version='v202402')

    report_job = {
        'reportQuery': {
            'dimensions': ['DATE', 'DEVICE_CATEGORY_NAME', 'CREATIVE_NAME', 'CREATIVE_ID', 'LINE_ITEM_NAME', 'LINE_ITEM_ID', 'LINE_ITEM_TYPE', 'ORDER_ID', 'ORDER_NAME'],
            'columns': ['AD_SERVER_IMPRESSIONS', 'AD_SERVER_CLICKS', 'AD_SERVER_CTR', 'AD_SERVER_CPM_AND_CPC_REVENUE', 'AD_SERVER_ALL_REVENUE', 'AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM', 'TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE', 'AD_EXCHANGE_COST_PER_CLICK'],
            'dateRangeType': 'YESTERDAY'
        }
    }

    try:
        report_job_id = report_downloader.WaitForReport(report_job)
    except errors.AdManagerReportError as e:
        print('Failed to generate report. Error was: %s' % e)

    export_format = 'CSV_DUMP'

    report_file = tempfile.NamedTemporaryFile(suffix='.csv.gz', delete=False)

    report_downloader.DownloadReportToFile(report_job_id, export_format, report_file)

    report_file.close()

    # Wypakowanie pliku .gz do formatu CSV
    with gzip.open(report_file.name, 'rb') as f_in:
        with open(report_file.name[:-3], 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Usunięcie pliku .gz
    os.remove(report_file.name)

    # Zmiana formatu daty w pliku CSV
    with open(report_file.name[:-3], 'r', encoding='utf-8') as file:
        lines = file.readlines()
    with open(report_file.name[:-3], 'w', encoding='utf-8') as file:
        for line in lines:
            parts = line.split(',')
            if parts[0] != 'Dimension.DATE':
                date = datetime.strptime(parts[0], '%Y-%m-%d').strftime('%Y%m%d')
                parts[0] = date
                file.write(','.join(parts))
            else:
                file.write(line)

    print('Report job with id "%s" downloaded, extracted, and date format changed to:\n%s' % (
        report_job_id, report_file.name[:-3]))


if __name__ == '__main__':
    # LoadFromStorage() bez argumentu szuka pliku googleads.yaml w katalogu domowym (patrz README).
    ad_manager_client = ad_manager.AdManagerClient.LoadFromStorage()
    main(ad_manager_client)


# ----------------------------------------------------------------------------
# Przykładowy wynik (dane syntetyczne): plik .csv po rozpakowaniu
#
# Data przepisana na RRRRMMDD. Pozycja SPONSORSHIP (CPD) ma przychód tylko w kolumnach ALL_REVENUE,
# pozycja AD_EXCHANGE tylko w TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE.
# Kwoty w mikrojednostkach waluty sieci (1 zł = 1 000 000), CTR jako ułamek.
# Dokładne nagłówki CSV_DUMP i format dat sprawdź przy pierwszym uruchomieniu.
#
# | Dimension.DATE | Dimension.DEVICE_CATEGORY_NAME | Dimension.CREATIVE_NAME | Dimension.CREATIVE_ID | Dimension.LINE_ITEM_NAME | Dimension.LINE_ITEM_ID | Dimension.LINE_ITEM_TYPE | Dimension.ORDER_ID | Dimension.ORDER_NAME | Column.AD_SERVER_IMPRESSIONS | Column.AD_SERVER_CLICKS | Column.AD_SERVER_CTR | Column.AD_SERVER_CPM_AND_CPC_REVENUE | Column.AD_SERVER_ALL_REVENUE | Column.AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM | Column.TOTAL_LINE_ITEM_LEVEL_ALL_REVENUE | Column.AD_EXCHANGE_COST_PER_CLICK |
# |---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
# | 20261101 | Desktop | MarkaA_billboard_970x250 | 138000201 | Marka A - Display homepage - CPM | 6012000101 | STANDARD | 3412000001 | 2026-10 - Marka A - Display homepage | 152300 | 198 | 0.0013 | 731040000 | 731040000 | 4800000 | 731040000 | 0 |
# | 20261101 | Smartphone | MarkaA_mobile_300x250 | 138000202 | Marka A - Display homepage - CPM | 6012000101 | STANDARD | 3412000001 | 2026-10 - Marka A - Display homepage | 98400 | 271 | 0.0028 | 472320000 | 472320000 | 4800000 | 472320000 | 0 |
# | 20261101 | Desktop | MarkaB_preroll_15s | 138000301 | Marka B - Video pre-roll - CPM | 6012000102 | STANDARD | 3412000002 | 2026-10 - Marka B - Video pre-roll | 41200 | 63 | 0.0015 | 988800000 | 988800000 | 24000000 | 988800000 | 0 |
# | 20261101 | Smartphone | MarkaC_sponsoring_sport | 138000401 | Marka C - Sponsoring Sport - CPD | 6012000103 | SPONSORSHIP | 3412000003 | Q4 - Marka C - Sponsoring sekcji Sport | 76800 | 112 | 0.0015 | 0 | 300000000 | 0 | 300000000 | 0 |
# | 20261101 | Tablet | AdX_backfill | 138000901 | AdX - backfill | 6012000999 | AD_EXCHANGE | 3412000099 | Ad Exchange | 22100 | 19 | 0.0009 | 0 | 0 | 0 | 40885000 | 420000 |
