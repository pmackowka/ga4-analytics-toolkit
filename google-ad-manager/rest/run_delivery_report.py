"""
Raport dostarczenia (delivery) jednego zamówienia przez Ad Manager API (REST).

Odpowiednik ../run_delivery_report.py, który korzysta z archiwalnego SOAP API
(biblioteka googleads). Ten sam zakres danych: wymiary zamówienia, wyświetlenia,
kliknięcia, CTR, przychód i eCPM z ostatnich 8 dni, filtr na jedno zamówienie,
wynik zapisany do pliku .csv.gz.

Różnice względem wersji SOAP:
- biblioteka google-ads-admanager (moduł admanager_v1) gada z API przez REST;
- raport to zasób: najpierw create_report (definicja), potem run_report
  (operacja długotrwała), na końcu fetch_report_result_rows (wiersze, z paginacją);
- filtr to struktura Filter zamiast zapytania PQL z bind variables;
- atrybuty wymiarów (ORDER_TRAFFICKER, daty zamówienia) są zwykłymi wymiarami.

Uwierzytelnianie: Application Default Credentials. Lokalnie:
    gcloud auth application-default login \
        --scopes=https://www.googleapis.com/auth/admanager,https://www.googleapis.com/auth/cloud-platform
albo konto usługi dodane jako użytkownik w sieci Ad Managera
(GOOGLE_APPLICATION_CREDENTIALS wskazuje plik klucza). W projekcie GCP musi być
włączone Ad Manager API.

Użycie:
    python run_delivery_report.py --network-code 123456 --order-id 987654
    python run_delivery_report.py --network-code 123456 --order-id 987654 --report-id 4455
"""

import argparse
import csv
import gzip
import tempfile
from datetime import date, timedelta

from google.ads import admanager_v1
from google.type import date_pb2

RD = admanager_v1.ReportDefinition

DIMENSIONS = [
    RD.Dimension.ORDER_ID,
    RD.Dimension.ORDER_NAME,
    RD.Dimension.ORDER_TRAFFICKER,
    RD.Dimension.ORDER_START_DATE_TIME,
    RD.Dimension.ORDER_END_DATE_TIME,
]

# Kolumny SOAP AD_SERVER_CPM_AND_CPC_REVENUE i AD_SERVER_WITHOUT_CPD_AVERAGE_ECPM
# nie istnieją w REST — najbliższe odpowiedniki to metryki "bez CPD" poniżej.
METRICS = [
    RD.Metric.AD_SERVER_IMPRESSIONS,
    RD.Metric.AD_SERVER_CLICKS,
    RD.Metric.AD_SERVER_CTR,
    RD.Metric.AD_SERVER_REVENUE_WITHOUT_CPD,
    RD.Metric.AD_SERVER_AVERAGE_ECPM_WITHOUT_CPD,
]

DAYS_BACK = 8


def to_date(d: date) -> date_pb2.Date:
    return date_pb2.Date(year=d.year, month=d.month, day=d.day)


def build_report(order_id: int, end_date: date) -> admanager_v1.Report:
    """Definicja raportu: te same wymiary, metryki i zakres dat co w wersji SOAP."""
    start_date = end_date - timedelta(days=DAYS_BACK)
    order_filter = RD.Filter(
        field_filter=RD.Filter.FieldFilter(
            field=RD.Field(dimension=RD.Dimension.ORDER_ID),
            operation=RD.Filter.Operation.IN,
            values=[admanager_v1.ReportValue(int_value=order_id)],
        )
    )
    return admanager_v1.Report(
        display_name=f"Delivery report — order {order_id}",
        # HIDDEN: raport nie zaśmieca listy raportów w interfejsie Ad Managera
        visibility=admanager_v1.ReportVisibilityEnum.ReportVisibility.HIDDEN,
        report_definition=RD(
            dimensions=DIMENSIONS,
            metrics=METRICS,
            filters=[order_filter],
            date_range=RD.DateRange(
                fixed=RD.DateRange.FixedDateRange(
                    start_date=to_date(start_date), end_date=to_date(end_date)
                )
            ),
            report_type=RD.ReportType.HISTORICAL,
        ),
    )


def report_value(value: admanager_v1.ReportValue):
    """Wartość z ReportValue niezależnie od typu (int, double, string, lista...)."""
    kind = admanager_v1.ReportValue.pb(value).WhichOneof("value")
    if kind is None:
        return None
    raw = getattr(value, kind)
    if kind.endswith("_list_value"):
        return "|".join(str(v) for v in raw.values)
    return raw


def header() -> list[str]:
    return [d.name for d in DIMENSIONS] + [m.name for m in METRICS]


def run(network_code: str, order_id: int, report_id: str | None) -> str:
    client = admanager_v1.ReportServiceClient()

    # 1. Definicja raportu. Przy --report-id używana jest zapisana definicja
    #    (jej filtr i zakres dat), a --order-id nie ma wpływu na wynik.
    if report_id:
        report_name = client.report_path(network_code, report_id)
    else:
        report = client.create_report(
            parent=f"networks/{network_code}",
            report=build_report(order_id, date.today()),
        )
        report_name = report.name
        print(f"Utworzono raport: {report_name}")

    # 2. Uruchomienie: operacja długotrwała, result() czeka na jej koniec.
    operation = client.run_report(name=report_name)
    result_name = operation.result(timeout=600).report_result

    # 3. Wiersze: pager sam pobiera kolejne strony (next_page_token).
    rows = client.fetch_report_result_rows(
        request=admanager_v1.FetchReportResultRowsRequest(name=result_name, page_size=1000)
    )

    out = tempfile.NamedTemporaryFile(suffix=".csv.gz", delete=False)
    out.close()
    with gzip.open(out.name, "wt", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header())
        for row in rows:
            dims = [report_value(v) for v in row.dimension_values]
            # Bez porównań okresów jest jedna grupa metryk na cały zakres dat.
            mets = [report_value(v) for v in row.metric_value_groups[0].primary_values]
            writer.writerow(dims + mets)
    return out.name


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--network-code", required=True, help="kod sieci Ad Managera")
    parser.add_argument("--order-id", required=True, type=int, help="ID zamówienia z URL-a Ad Managera")
    parser.add_argument("--report-id", help="ID istniejącego raportu: pomija create_report i używa jego zapisanej definicji")
    args = parser.parse_args()
    path = run(args.network_code, args.order_id, args.report_id)
    print(f"Raport zapisany do:\n{path}")


if __name__ == "__main__":
    main()
