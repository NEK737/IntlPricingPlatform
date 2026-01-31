---1. Create the Master Tableau View
USE IntlPricingDB;
GO

USE IntlPricingDB;
GO

IF OBJECT_ID('ips.vw_AirlinePricingAnalytics', 'V') IS NOT NULL
    DROP VIEW ips.vw_AirlinePricingAnalytics;
GO

USE IntlPricingDB;
GO

CREATE VIEW ips.vw_AirlinePricingAnalytics AS
SELECT
    f.FactKey,
    m.MarketKey,
    m.ODPairID,
    m.OriginCityMarketID,
    m.DestCityMarketID,
    m.OriginAirportID,
    m.DestAirportID,
    m.NonStopMiles,
    m.Circuity,
    m.Multi_Airport,
    m.LCC_Comp,
    m.Slot,
    m.Non_Stop,

    c.CarrierKey,
    c.CarrierID,          -- we’ll use this in Tableau as “Carrier”

    f.MktCoupons,
    f.RoundTrip,
    f.Pax,
    f.CarrierPax,
    f.Average_Fare,
    f.Market_share,
    f.Market_HHI,
    f.MktMilesFlown,

    f.OriginCityMarketID_freq,
    f.DestCityMarketID_freq,
    f.OriginAirportID_freq,
    f.DestAirportID_freq,
    f.Carrier_freq,
    f.ODPairID_freq
FROM ips.FactMarketFare AS f
JOIN ips.DimMarket      AS m ON f.MarketKey  = m.MarketKey
JOIN ips.DimCarrier     AS c ON f.CarrierKey = c.CarrierKey;
GO

SELECT TOP (20) *
FROM ips.vw_AirlinePricingAnalytics;
GO


---3) For Tableau, just alias CarrierID as a name (for now)
CREATE OR ALTER VIEW ips.vw_AirlinePricing_Tableau AS
SELECT
    m.ODPairID,
    m.OriginAirportID,
    m.DestAirportID,
    m.NonStopMiles,
    c.CarrierID       AS Carrier,   -- use as dimension
    f.Average_Fare,
    f.Pax,
    f.CarrierPax,
    f.Market_share,
    f.Market_HHI,
    f.MktMilesFlown
FROM ips.FactMarketFare AS f
JOIN ips.DimMarket      AS m ON f.MarketKey  = m.MarketKey
JOIN ips.DimCarrier     AS c ON f.CarrierKey = c.CarrierKey;
GO
