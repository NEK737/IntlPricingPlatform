/*
File: sql/03_stored_procs.sql

Purpose
-------
Expose a parameterized stored procedure that Tableau (or a nightly
Delta job) can call to get a filtered market pricing summary.

Procedure
---------
- ips.usp_GetMarketPricingSummary
    @CarrierID (optional)
    @MinTotalPax (optional)
*/

------------------------------------------------------------
-- Stored Procedure: usp_GetMarketPricingSummary
------------------------------------------------------------
IF OBJECT_ID('ips.usp_GetMarketPricingSummary', 'P') IS NOT NULL
    DROP PROCEDURE ips.usp_GetMarketPricingSummary;
GO

CREATE PROCEDURE ips.usp_GetMarketPricingSummary
    @CarrierID   INT      = NULL,
    @MinTotalPax FLOAT    = NULL
AS
BEGIN
    SET NOCOUNT ON;

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
        f.YieldFarePerMile      AS [Yield FarePerMile]
    FROM ips.FactMarketFare f
    WHERE
        (@CarrierID   IS NULL OR f.CarrierID = @CarrierID)
        AND (@MinTotalPax IS NULL OR f.TotalPax >= @MinTotalPax);
END;
GO
