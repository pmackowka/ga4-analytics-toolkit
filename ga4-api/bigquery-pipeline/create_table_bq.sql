-- Tabela docelowa dla codziennego importu kosztów/konwersji Google Ads z GA4 Data API.
-- Podmień YOUR_PROJECT / YOUR_DATASET / YOUR_TABLE na własne (patrz gads_costs_to_bigquery_cloud_function.py).

CREATE OR REPLACE TABLE `YOUR_PROJECT.YOUR_DATASET.YOUR_TABLE` (
    date DATE,
    googleAdsCampaignName STRING,
    googleAdsCampaignId STRING,
    keyEvents INT64,
    advertiserAdCost FLOAT64,
    advertiserAdCostPerKeyEvent FLOAT64,
    advertiserAdImpressions INT64,
    advertiserAdClicks INT64,
    advertiserAdCostPerClick FLOAT64,
    purchaseRevenue FLOAT64,
    returnOnAdSpend FLOAT64
);

-- Odpowiednik przez bq CLI, jeśli wolisz nie tworzyć tabeli w konsoli:
-- bq mk --table \
--   YOUR_PROJECT:YOUR_DATASET.YOUR_TABLE \
--   date:DATE,googleAdsCampaignName:STRING,googleAdsCampaignId:STRING,keyEvents:INTEGER,advertiserAdCost:FLOAT,advertiserAdCostPerKeyEvent:FLOAT,advertiserAdImpressions:INTEGER,advertiserAdClicks:INTEGER,advertiserAdCostPerClick:FLOAT,purchaseRevenue:FLOAT,returnOnAdSpend:FLOAT
