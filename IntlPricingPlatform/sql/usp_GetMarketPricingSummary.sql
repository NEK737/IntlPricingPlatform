--3) Proc: Market Pricing Summary (Analytics / Tableau)
--This returns aggregated KPIs by OD pair and carrier.
--You can call it from SSMS for analysis or even build a Tableau extract off it.
USE IntlPricingDB;
GO

IF OBJECT_ID('ips.usp_GetMarketPricingSummary', 'P') IS NOT NULL
    DROP PROCEDURE ips.usp_GetMarketPricingSummary;
GO

CREATE PROCEDURE ips.usp_GetMarketPricingSummary
(
    @MinNonStopMiles   FLOAT = NULL,
    @MaxNonStopMiles   FLOAT = NULL,
    @CarrierID         INT   = NULL,
    @MinMarketShare    FLOAT = NULL,
    @MaxMarketShare    FLOAT = NULL
)
AS
BEGIN
    SET NOCOUNT ON;

    /*
        Returns pricing KPIs by OD pair and carrier.

        Parameters allow basic filtering:
        - @MinNonStopMiles, @MaxNonStopMiles: distance filters
        - @CarrierID: filter to one carrier
        - @MinMarketShare, @MaxMarketShare: carrier's market share filter
    */

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

        -- Simple derived metrics
        CASE 
            WHEN SUM(f.MktMilesFlown) = 0 THEN NULL
            ELSE SUM(f.Average_Fare * f.Pax) / SUM(f.MktMilesFlown)
        END AS Yield_FarePerMile
    FROM ips.FactMarketFare AS f
    JOIN ips.DimMarket      AS m ON f.MarketKey  = m.MarketKey
    JOIN ips.DimCarrier     AS c ON f.CarrierKey = c.CarrierKey
    WHERE
        (@MinNonStopMiles IS NULL OR m.NonStopMiles >= @MinNonStopMiles) AND
        (@MaxNonStopMiles IS NULL OR m.NonStopMiles <= @MaxNonStopMiles) AND
        (@CarrierID       IS NULL OR c.CarrierID   = @CarrierID) AND
        (@MinMarketShare  IS NULL OR f.Market_share >= @MinMarketShare) AND
        (@MaxMarketShare  IS NULL OR f.Market_share <= @MaxMarketShare)
    GROUP BY
        m.ODPairID,
        m.OriginAirportID,
        m.DestAirportID,
        m.NonStopMiles,
        c.CarrierID
    ORDER BY
        m.NonStopMiles,
        c.CarrierID;
END;
GO
