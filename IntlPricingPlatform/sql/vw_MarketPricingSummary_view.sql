USE IntlPricingDB;
GO

IF OBJECT_ID('ips.vw_MarketPricingSummary', 'V') IS NOT NULL
    DROP VIEW ips.vw_MarketPricingSummary;
GO

CREATE VIEW ips.vw_MarketPricingSummary
AS
SELECT
    m.ODPairID,
    m.OriginAirportID,
    m.DestAirportID,
    m.NonStopMiles,
    c.CarrierID,

    -- Core KPIs
    AVG(f.Average_Fare)       AS AvgFare,
    SUM(f.Pax)                AS TotalPax,
    SUM(f.CarrierPax)         AS CarrierPax,
    AVG(f.Market_share)       AS AvgMarketShare,
    AVG(f.Market_HHI)         AS AvgMarketHHI,
    SUM(f.MktMilesFlown)      AS TotalMilesFlown,

    -- Derived metric: yield
    CASE 
        WHEN SUM(f.MktMilesFlown) = 0 THEN NULL
        ELSE SUM(f.Average_Fare * f.Pax) / SUM(f.MktMilesFlown)
    END AS Yield_FarePerMile
FROM ips.FactMarketFare AS f
JOIN ips.DimMarket      AS m ON f.MarketKey  = m.MarketKey
JOIN ips.DimCarrier     AS c ON f.CarrierKey = c.CarrierKey
GROUP BY
    m.ODPairID,
    m.OriginAirportID,
    m.DestAirportID,
    m.NonStopMiles,
    c.CarrierID;
GO
