---Below are three stored procedures  create in IntlPricingDB:
--1) ips.usp_RefreshDimensions – rebuilds DimMarket and DimCarrier from staging
--2) ips.usp_LoadFactMarketFare – reloads the fact table from staging & dims
--3) ips.usp_GetMarketPricingSummary – returns aggregated pricing metrics (for Tableau/analysts)

---1️) Proc: Refresh Dimensions from Staging
USE IntlPricingDB;
GO

IF OBJECT_ID('ips.usp_RefreshDimensions', 'P') IS NOT NULL
    DROP PROCEDURE ips.usp_RefreshDimensions;
GO

CREATE PROCEDURE ips.usp_RefreshDimensions
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRAN;

    ----------------------------------------------------------------------
    -- 1. Clear Fact table first (it depends on dims via FK constraints)
    ----------------------------------------------------------------------
    PRINT 'Truncating FactMarketFare...';
    TRUNCATE TABLE ips.FactMarketFare;

    ----------------------------------------------------------------------
    -- 2. Clear dimension tables
    ----------------------------------------------------------------------
    PRINT 'Deleting from DimMarket...';
    DELETE FROM ips.DimMarket;

    PRINT 'Deleting from DimCarrier...';
    DELETE FROM ips.DimCarrier;

    ----------------------------------------------------------------------
    -- 3. Rebuild DimMarket (one row per ODPairID)
    ----------------------------------------------------------------------
    PRINT 'Inserting into DimMarket...';

    INSERT INTO ips.DimMarket (
        ODPairID,
        OriginCityMarketID,
        DestCityMarketID,
        OriginAirportID,
        DestAirportID,
        NonStopMiles,
        Circuity,
        Multi_Airport,
        LCC_Comp,
        Slot,
        Non_Stop
    )
    SELECT
        s.ODPairID,
        MIN(s.OriginCityMarketID),
        MIN(s.DestCityMarketID),
        MIN(s.OriginAirportID),
        MIN(s.DestAirportID),
        MIN(s.NonStopMiles),
        MIN(s.Circuity),
        MIN(s.Multi_Airport),
        MIN(s.LCC_Comp),
        MIN(s.Slot),
        MIN(s.Non_Stop)
    FROM dbo.AirlineMarketFare_Staging AS s
    GROUP BY
        s.ODPairID;

    PRINT CONCAT('DimMarket rows: ', @@ROWCOUNT);

    ----------------------------------------------------------------------
    -- 4. Rebuild DimCarrier
    ----------------------------------------------------------------------
    PRINT 'Inserting into DimCarrier...';

    INSERT INTO ips.DimCarrier (CarrierID)
    SELECT DISTINCT
        s.Carrier
    FROM dbo.AirlineMarketFare_Staging AS s;

    PRINT CONCAT('DimCarrier rows: ', @@ROWCOUNT);

    COMMIT TRAN;

    PRINT 'usp_RefreshDimensions completed successfully.';
END;
GO

---How to run----
EXEC ips.usp_RefreshDimensions;
