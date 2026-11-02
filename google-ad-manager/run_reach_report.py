# Źródło: oficjalne przykłady kodu do Google Ad Manager API (biblioteka googleads-python-lib),
# licencja Apache 2.0 — https://github.com/googleads/googleads-python-lib
"""This code example runs a reach report."""

import tempfile

# Import appropriate modules from the client library.
from googleads import ad_manager
from googleads import errors


def main(client):
  # Initialize a DataDownloader.
  report_downloader = client.GetDataDownloader(version='v202402')

  # Create report job.
  report_job = {
      'reportQuery': {
          'dimensions': ['COUNTRY_NAME', 'LINE_ITEM_ID', 'LINE_ITEM_NAME'],
          'columns': ['UNIQUE_REACH_FREQUENCY', 'UNIQUE_REACH_IMPRESSIONS',
                      'UNIQUE_REACH'],
          'dateRangeType': 'REACH_LIFETIME'
      }
  }

  try:
    # Run the report and wait for it to finish.
    report_job_id = report_downloader.WaitForReport(report_job)
  except errors.AdManagerReportError as e:
    print('Failed to generate report. Error was: %s' % e)

  # Change to your preferred export format.
  export_format = 'CSV_DUMP'

  report_file = tempfile.NamedTemporaryFile(suffix='.csv.gz', delete=False)

  # Download report data.
  report_downloader.DownloadReportToFile(
      report_job_id, export_format, report_file)

  report_file.close()

  # Display results.
  print('Report job with id "%s" downloaded to:\n%s' % (
      report_job_id, report_file.name))


if __name__ == '__main__':
  # Initialize client object.
  # LoadFromStorage() bez argumentu szuka pliku googleads.yaml w katalogu domowym (patrz README).
  ad_manager_client = ad_manager.AdManagerClient.LoadFromStorage()
  main(ad_manager_client)


# ----------------------------------------------------------------------------
# Przykładowy wynik (dane syntetyczne): plik CSV_DUMP (.csv.gz)
#
# UNIQUE_REACH_FREQUENCY = wyświetlenia / unikalni użytkownicy.
# Dokładne nagłówki CSV_DUMP i format dat sprawdź przy pierwszym uruchomieniu.
#
# | Dimension.COUNTRY_NAME | Dimension.LINE_ITEM_ID | Dimension.LINE_ITEM_NAME | Column.UNIQUE_REACH_FREQUENCY | Column.UNIQUE_REACH_IMPRESSIONS | Column.UNIQUE_REACH |
# |---|---|---|---:|---:|---:|
# | Polska | 6012000101 | Marka A - Display homepage - CPM | 3.62 | 1854200 | 512400 |
# | Polska | 6012000102 | Marka B - Video pre-roll - CPM | 2.13 | 642300 | 301500 |
# | Niemcy | 6012000101 | Marka A - Display homepage - CPM | 2.18 | 41200 | 18900 |
# | Wielka Brytania | 6012000102 | Marka B - Video pre-roll - CPM | 1.73 | 12800 | 7400 |
# | Polska | 6012000103 | Marka C - Sponsoring Sport - CPD | 3.36 | 2310500 | 688100 |
