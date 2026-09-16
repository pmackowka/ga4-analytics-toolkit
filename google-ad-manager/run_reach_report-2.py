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
