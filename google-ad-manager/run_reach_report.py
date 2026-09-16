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