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

# Oficjalny przykład kodu Google Ad Manager API (biblioteka googleads-python-lib), Apache 2.0,
# z drobną adaptacją docstringu.
"""Typowy raport dzienny na podstawie danych z systemu Google Ad Manager"""

import tempfile

from googleads import ad_manager
from googleads import errors


def main(client):
  # Inicjalizuje obiekt report_downloader, który będzie używany do pobierania danych z raportu.
  report_downloader = client.GetDataDownloader(version='v202402')

  # Tworzy obiekt report_job, który definiuje parametry raportu, takie jak wymiary, kolumny, zakres dat itp. 
  report_job = {
      'reportQuery': {
          'dimensions': ['DATE', 'AD_UNIT_NAME'],
          'adUnitView': 'HIERARCHICAL',
          'columns': ['AD_SERVER_IMPRESSIONS', 'AD_SERVER_CLICKS',
                      'AD_EXCHANGE_LINE_ITEM_LEVEL_IMPRESSIONS',
                      'AD_EXCHANGE_LINE_ITEM_LEVEL_CLICKS',
                      'TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS',
                      'TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE'],
          'dateRangeType': 'LAST_WEEK'
      }
  }

  try:
    # Pobiera i czeka na zakończenie generowania raportu
    report_job_id = report_downloader.WaitForReport(report_job)
  except errors.AdManagerReportError as e:
    print('Failed to generate report. Error was: %s' % e)

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
# Jeden wiersz na dzień i jednostkę reklamową (widok hierarchiczny).
# AD_SERVER_IMPRESSIONS + AD_EXCHANGE_LINE_ITEM_LEVEL_IMPRESSIONS = TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS.
# Kwoty w mikrojednostkach waluty sieci (1 zł = 1 000 000), CTR jako ułamek.
# Dokładne nagłówki CSV_DUMP i format dat sprawdź przy pierwszym uruchomieniu.
#
# | Dimension.DATE | Dimension.AD_UNIT_NAME | Column.AD_SERVER_IMPRESSIONS | Column.AD_SERVER_CLICKS | Column.AD_EXCHANGE_LINE_ITEM_LEVEL_IMPRESSIONS | Column.AD_EXCHANGE_LINE_ITEM_LEVEL_CLICKS | Column.TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS | Column.TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE |
# |---|---|---:|---:|---:|---:|---:|---:|
# | 2026-10-26 | serwis » strona-glowna » top_billboard | 213900 | 417 | 198400 | 201 | 412300 | 3215940000 |
# | 2026-10-26 | serwis » strona-glowna » rectangle_1 | 145200 | 225 | 210900 | 274 | 356100 | 1816110000 |
# | 2026-10-26 | serwis » artykul » inside_text | 197500 | 454 | 301200 | 693 | 498700 | 3191680000 |
# | 2026-10-26 | serwis » artykul » sticky_bottom_mobile | 166100 | 581 | 455300 | 1594 | 621400 | 2423460000 |
# | 2026-10-27 | serwis » strona-glowna » top_billboard | 228873 | 446 | 212288 | 215 | 441161 | 3441055800 |
# | 2026-10-27 | serwis » strona-glowna » rectangle_1 | 155364 | 240 | 225663 | 293 | 381027 | 1943237700 |
# | 2026-10-27 | serwis » artykul » inside_text | 211325 | 485 | 322284 | 741 | 533609 | 3415097600 |
# | 2026-10-27 | serwis » artykul » sticky_bottom_mobile | 177727 | 621 | 487171 | 1705 | 664898 | 2593102200 |
