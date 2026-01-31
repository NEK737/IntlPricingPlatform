/*
File: sql/04_usp_LoadFactMarketFare.sql

Purpose
-------
ETL from the raw staging table into the dimensional model:

    dbo.AirlineMarketFare_Staging  -->  ips.DimCarrier
                                     -->  ips.DimAirport
                                     -->  ips.DimMarket
                                     -->  ips.FactMarketFare

This procedure is designed to be:
- Idempotent for dimensions (only inserts new members)
- Rebuilds the fact table from scratch on each run (TRUNCATE + INSERT)
- Easy to call from SQL Agent, Delta job, or manually

Call
----
EXEC ips.usp_LoadFactMarketFare;
*/

IF OBJECT_ID('ips.usp_LoadFactMarketFare', 'P') IS NOT NULL
    DROP PROCEDURE ips.usp_LoadFactMarketFare;
GO

CREATE PROCEDURE ips.usp_LoadFactMarketFare
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @rows_carrier       INT = 0,
            @rows_airport       INT = 0,
            @rows_market        INT = 0,
            @rows_fact_inserted INT = 0;

    BEGIN TRY
        BEGIN TRAN;

        ------------------------------------------------------------
        -- 1. Ensure DimCarrier is populated
        --    One row per distinct Carrier code from staging
        ------------------------------------------------------------
        ;WITH DistinctCarriers AS
        (
            SELECT DISTINCT s.Carrier
            FROM dbo.AirlineMarketFare_Staging s
            WHERE s.Carrier IS NOT NULL
        )
        INSERT INTO ips.DimCarrier (CarrierCode)
        SELECT dc.Carrier
        FROM DistinctCarriers dc
        LEFT JOIN ips.DimCarrier c
            ON dc.Carrier = c.CarrierCode
        WHERE c.CarrierID IS NULL;

        SET @rows_carrier = @@ROWCOUNT;


        ------------------------------------------------------------
        -- 2. Ensure DimAirport is populated
        --    One row per distinct Origin/Dest AirportID from staging
        ------------------------------------------------------------
        ;WITH DistinctAirports AS
        (
            SELECT DISTINCT s.OriginAirportID AS AirportID
            FROM dbo.AirlineMarketFare_Staging s
            WHERE s.OriginAirportID IS NOT NULL

            UNION

            SELECT DISTINCT s.DestAirportID AS AirportID
            FROM dbo.AirlineMarketFare_Staging s
            WHERE s.DestAirportID IS NOT NULL
        )
        INSERT INTO ips.DimAirport (AirportID)
        SELECT da.AirportID
        FROM DistinctAirports da
        LEFT JOIN ips.DimAirport a
            ON da.AirportID = a.AirportID
        WHERE a.AirportID IS NULL;

        SET @rows_airport = @@ROWCOUNT;


        ------------------------------------------------------------
        -- 3. Ensure DimMarket is populated
        --    One row per ODPairID (Origin+Dest+NonStopMiles)
        ------------------------------------------------------------
        ;WITH DistinctMarkets AS
        (
            SELECT
                s.ODPairID,
                s.OriginAirportID,
                s.DestAirportID,
                AVG(s.NonStopMiles) AS NonStopMiles
            FROM dbo.AirlineMarketFare_Staging s
            WHERE s.ODPairID IS NOT NULL
            GROUP BY
                s.ODPairID,
                s.OriginAirportID,
                s.DestAirportID
        )
        INSERT INTO ips.DimMarket
        (
            ODPairID,
            OriginAirportID,
            DestAirportID,
            NonStopMiles
        )
        SELECT
            dm.ODPairID,
            dm.OriginAirportID,
            dm.DestAirportID,
            dm.NonStopMiles
        FROM DistinctMarkets dm
        LEFT JOIN ips.DimMarket m
            ON dm.ODPairID = m.ODPairID
        WHERE m.MarketID IS NULL;

        SET @rows_market = @@ROWCOUNT;


        ------------------------------------------------------------
        -- 4. Rebuild Fact table
        --    Aggregates staging to carrier × market grain
        ------------------------------------------------------------
        -- Clear existing data to avoid duplicates
        TRUNCATE TABLE ips.FactMarketFare;

        /*
            We aggregate per:
                - ODPairID
                - OriginAirportID
                - DestAirportID
                - Carrier

            Metrics:
                TotalPax         = SUM(CarrierPax)
                TotalMilesFlown  = SUM(MktMilesFlown)
                AvgFare          = AVG(AvgFare)
                AvgMarketShare   = AVG(MarketShare)
                AvgMarketHHI     = AVG(MarketHHI)
                YieldFarePerMile = AvgFare / NonStopMiles
        */

        ;WITH AggFact AS
        (
            SELECT
                s.ODPairID,
                s.OriginAirportID,
                s.DestAirportID,
                s.Carrier,

                -- metrics
                SUM(ISNULL(s.CarrierPax, s.Pax))              AS TotalPax,
                SUM(ISNULL(s.MktMilesFlown, s.NonStopMiles)) AS TotalMilesFlown,
                AVG(s.AvgFare)                                AS AvgFare,
                AVG(s.MarketShare)                            AS AvgMarketShare,
                AVG(s.MarketHHI)                              AS AvgMarketHHI,
                AVG(s.NonStopMiles)                           AS NonStopMiles
            FROM dbo.AirlineMarketFare_Staging s
            GROUP BY
                s.ODPairID,
                s.OriginAirportID,
                s.DestAirportID,
                s.Carrier
        )
        INSERT INTO ips.FactMarketFare
        (
            MarketID,
            CarrierID,
            ODPairID,
            OriginAirportID,
            DestAirportID,
            NonStopMiles,
            TotalMilesFlown,
            TotalPax,
            AvgFare,
            AvgMarketShare,
            AvgMarketHHI,
            YieldFarePerMile
        )
        SELECT
            m.MarketID,
            c.CarrierID,
            af.ODPairID,
            af.OriginAirportID,
            af.DestAirportID,
            af.NonStopMiles,
            af.TotalMilesFlown,
            af.TotalPax,
            af.AvgFare,
            af.AvgMarketShare,
            af.AvgMarketHHI,
            CASE
                WHEN af.NonStopMiles IS NULL OR af.NonStopMiles = 0
                    THEN NULL
                ELSE af.AvgFare / af.NonStopMiles
            END AS YieldFarePerMile
        FROM AggFact af
        JOIN ips.DimMarket m
            ON af.ODPairID        = m.ODPairID
           AND af.OriginAirportID = m.OriginAirportID
           AND af.DestAirportID   = m.DestAirportID
        JOIN ips.DimCarrier c
            ON af.Carrier = c.CarrierCode;

        SET @rows_fact_inserted = @@ROWCOUNT;


        ------------------------------------------------------------
        -- 5. Commit and return small summary to caller
        ------------------------------------------------------------
        COMMIT TRAN;

        SELECT
            @rows_carrier       AS CarriersInserted,
            @rows_airport       AS AirportsInserted,
            @rows_market        AS MarketsInserted,
            @rows_fact_inserted AS FactRowsInserted;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRAN;

        -- Re-throw the error with context
        DECLARE
            @ErrorMessage  NVARCHAR(4000),
            @ErrorSeverity INT,
            @ErrorState    INT;

        SELECT
            @ErrorMessage  = ERROR_MESSAGE(),
            @ErrorSeverity = ERROR_SEVERITY(),
            @ErrorState    = ERROR_STATE();

        RAISERROR (@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO
