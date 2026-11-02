#!/usr/bin/env python
#
# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Oficjalny przykład kodu Google Ad Manager API (biblioteka googleads-python-lib), Apache 2.0.
"""Runs a report similar to the "Orders report" on the Ad Manager website.

Includes additional attributes and can filter to include just one order.
"""

from datetime import datetime
from datetime import timedelta
import tempfile

# Import appropriate modules from the client library.
from googleads import ad_manager
from googleads import errors

# ID zamówienia widoczny w URL-u Ad Managera, np.
# https://admanager.google.com/<network_code>#delivery/order/order_overview/order_id=<order_id>
ORDER_ID = 'INSERT_ORDER_ID_HERE'


def main(client, order_id):
  # Create statement object to filter for an order.
  statement = (ad_manager.StatementBuilder(version='v202402')
               .Where('ORDER_ID = :id') # Ograniczam się do jednego ID
               .WithBindVariable('id', int(order_id)) # To w jaki sposób biblioteki kliencie wiążą zmienną
               .Limit(None)  # No limit or offset for reports
               .Offset(None))

  # Set the start and end dates of the report to run (past 8 days).
  end_date = datetime.now().date()
  start_date = end_date - timedelta(days=8)

  # Create report job.
  report_job = {
      'reportQuery': {
          'dimensions': ['ORDER_ID', 'ORDER_NAME'],
          'dimensionAttributes': ['ORDER_TRAFFICKER', 'ORDER_START_DATE_TIME',
                                  'ORDER_END_DATE_TIME'],
          'statement': statement.ToStatement(),
          'columns': ['AD_SERVER_IMPRESSIONS', 'AD_SERVER_CLICKS',
                      'AD_SERVER_CTR', 'AD_SERVER_CPM_AND_CPC_REVENUE',
                      'AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM'],
          'dateRangeType': 'CUSTOM_DATE',
          'startDate': start_date,
          'endDate': end_date
      }
  }

  # Initialize a DataDownloader.
  report_downloader = client.GetDataDownloader(version='v202402')

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
  # LoadFromStorage() bez argumentu szuka pliku googleads.yaml w katalogu domowym (patrz README).
  ad_manager_client = ad_manager.AdManagerClient.LoadFromStorage()


# ----------------------------------------------------------------------------
# Przykładowy wynik (dane syntetyczne): plik CSV_DUMP (.csv.gz)
#
# Filtr na jedno zamówienie = jeden wiersz; dwa wiersze to dwa uruchomienia.
# Kwoty w mikrojednostkach waluty sieci (1 zł = 1 000 000), CTR jako ułamek.
# Dokładne nagłówki CSV_DUMP i format dat sprawdź przy pierwszym uruchomieniu.
#
# | Dimension.ORDER_ID | Dimension.ORDER_NAME | DimensionAttribute.ORDER_TRAFFICKER | DimensionAttribute.ORDER_START_DATE_TIME | DimensionAttribute.ORDER_END_DATE_TIME | Column.AD_SERVER_IMPRESSIONS | Column.AD_SERVER_CLICKS | Column.AD_SERVER_CTR | Column.AD_SERVER_CPM_AND_CPC_REVENUE | Column.AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM |
# |---|---|---|---|---|---:|---:|---:|---:|---:|
# | 3412000001 | 2026-10 - Marka A - Display homepage | Trafficker A | 2026-10-01T00:00:00+02:00 | 2026-10-31T23:59:00+01:00 | 1854200 | 2967 | 0.0016 | 8901600000 | 4800777 |
# | 3412000002 | 2026-10 - Marka B - Video pre-roll | Trafficker B | 2026-10-15T00:00:00+02:00 | 2026-11-15T23:59:00+01:00 | 642300 | 1092 | 0.0017 | 15415200000 | 24000000 |
