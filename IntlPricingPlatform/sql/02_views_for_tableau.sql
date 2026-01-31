/*
File: sql/02_views_for_tableau.sql

Purpose
-------
Expose clean, analysis-ready views for Tableau / BI.

Views
-----
1. ips.vw_MarketPricingSummary
   - One row per carrier × OD pair market
2. ips.vw_RoutePoints
   - Origin + Destination points with lat/long for Route Map
*/

------------------------------------------------------------
-- 1. Market Pricing Summary View
------------------------------------------------------------
IF OBJECT_ID('ips.vw_MarketPricingSummary', 'V') IS NOT NULL
    DROP VIEW ips.vw_MarketPricingSummary;
GO

CREATE VIEW ips.vw_MarketPricingSummary
AS
SELECT
    f.ODPairID              AS [OD Pair ID],
    f.OriginAirportID       AS [Origin Airport ID],
    f.DestAirportID         AS [Dest Airport ID],
    f.CarrierID             AS [Carrier ID],

    f.NonStopMiles          AS [Non Stop Miles],
    f.TotalMilesFlown       AS [Total Miles Flown],
    f.TotalPax              AS [Total Pax],

    f.AvgFare               AS [Avg Fare],
    f.AvgMarketShare        AS [Avg Market Share],
    f.AvgMarketHHI          AS [Avg Market HHI],

    -- Yield metric used in the Carrier Yield bar chart
    f.YieldFarePerMile      AS [Yield FarePerMile]
FROM ips.FactMarketFare f;
GO


------------------------------------------------------------
-- 2. Route Points View
--    Used to draw routes on a map in Tableau.
--    Assumes you have a dbo.airports table with:
--       AirportID (int), AirportName, iata (3-letter code),
--       Latitude, Longitude.
------------------------------------------------------------
IF OBJECT_ID('ips.vw_RoutePoints', 'V') IS NOT NULL
    DROP VIEW ips.vw_RoutePoints;
GO

CREATE VIEW ips.vw_RoutePoints
AS
    -- Origin point
    SELECT
        f.ODPairID,
        'Origin'          AS PointType,
        f.OriginAirportID AS AirportID,
        a.AirportName,
        a.iata            AS AirportCode,
        a.Latitude,
        a.Longitude,

        f.DestAirportID   AS OtherAirportID,

        f.AvgFare,
        f.TotalPax,
        f.AvgMarketShare,
        f.AvgMarketHHI
    FROM ips.FactMarketFare f
    JOIN dbo.airports a
        ON f.OriginAirportID = a.AirportID

    UNION ALL

    -- Destination point
    SELECT
        f.ODPairID,
        'Destination'     AS PointType,
        f.DestAirportID   AS AirportID,
        a.AirportName,
        a.iata            AS AirportCode,
        a.Latitude,
        a.Longitude,

        f.OriginAirportID AS OtherAirportID,

        f.AvgFare,
        f.TotalPax,
        f.AvgMarketShare,
        f.AvgMarketHHI
    FROM ips.FactMarketFare f
    JOIN dbo.airports a
        ON f.DestAirportID = a.AirportID;
GO
