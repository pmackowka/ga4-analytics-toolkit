-- Tabela docelowa dla gads_costs_to_bigquery_cloud_function_v2.py.
-- Partycjonowanie po `date` pozwala funkcji nadpisywać dane jednego dnia
-- (tabela$RRRRMMDD + WRITE_TRUNCATE) zamiast dogrywać wiersze.
-- Podmień YOUR_PROJECT / YOUR_DATASET / YOUR_TABLE.

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT.YOUR_DATASET.YOUR_TABLE` (
    date DATE,                          -- dzień raportu (z GA4 RRRRMMDD, przeformatowany w funkcji)
    googleAdsCampaignName STRING,
    googleAdsCampaignId STRING,
    keyEvents INT64,                    -- liczba kluczowych zdarzeń
    advertiserAdCost FLOAT64,           -- koszt reklam
    advertiserAdCostPerKeyEvent FLOAT64,
    advertiserAdImpressions INT64,
    advertiserAdClicks INT64,
    advertiserAdCostPerClick FLOAT64,
    purchaseRevenue FLOAT64,
    returnOnAdSpend FLOAT64             -- przychód / koszt (ułamek)
)
PARTITION BY date                       -- jedna partycja na dzień = jednostka nadpisywania
OPTIONS (require_partition_filter = FALSE);
