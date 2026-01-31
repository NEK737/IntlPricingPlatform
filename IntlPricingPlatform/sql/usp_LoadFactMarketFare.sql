---2)Proc: Load Fact Table from Staging
--This uses your dims to populate ips.FactMarketFare.
--You’ll typically run this after usp_RefreshDimensions.
USE IntlPricingDB;
GO

IF OBJECT_ID('ips.usp_LoadFactMarketFare', 'P') IS NOT NULL
    DROP PROCEDURE ips.usp_LoadFactMarketFare;
GO

CREATE PROCEDURE ips.usp_LoadFactMarketFare
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRAN;

    ----------------------------------------------------------------------
    -- 1. Clear Fact table
    ----------------------------------------------------------------------
    PRINT 'Truncating FactMarketFare...';
    TRUNCATE TABLE ips.FactMarketFare;

    ----------------------------------------------------------------------
    -- 2. Insert fresh data from staging joined to dimensions
    ----------------------------------------------------------------------
    PRINT 'Inserting into FactMarketFare...';

    INSERT INTO ips.FactMarketFare (
        MarketKey,
        CarrierKey,
        MktCoupons,
        RoundTrip,
        Pax,
        CarrierPax,
        Average_Fare,
        Market_share,
        Market_HHI,
        MktMilesFlown,
        OriginCityMarketID_freq,
        DestCityMarketID_freq,
        OriginAirportID_freq,
        DestAirportID_freq,
        Carrier_freq,
        ODPairID_freq
    )
    SELECT
        m.MarketKey,
        c.CarrierKey,
        s.MktCoupons,
        s.RoundTrip,
        s.Pax,
        s.CarrierPax,
        s.Average_Fare,
        s.Market_share,
        s.Market_HHI,
        s.MktMilesFlown,
        s.OriginCityMarketID_freq,
        s.DestCityMarketID_freq,
        s.OriginAirportID_freq,
        s.DestAirportID_freq,
        s.Carrier_freq,
        s.ODPairID_freq
    FROM dbo.AirlineMarketFare_Staging AS s
    JOIN ips.DimMarket  AS m ON m.ODPairID  = s.ODPairID
    JOIN ips.DimCarrier AS c ON c.CarrierID = s.Carrier;

    PRINT CONCAT('FactMarketFare rows: ', @@ROWCOUNT);

    COMMIT TRAN;

    PRINT 'usp_LoadFactMarketFare completed successfully.';
END;
GO

--How to run:
EXEC ips.usp_LoadFactMarketFare;
