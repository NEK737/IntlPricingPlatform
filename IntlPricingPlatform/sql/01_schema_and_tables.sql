/*
File: sql/01_schema_and_tables.sql

Purpose
-------
Create a clean, minimal data warehouse layer for the airline pricing project.

Objects created
---------------
- Schema: ips
- Staging table: dbo.AirlineMarketFare_Staging
- Fact table: ips.FactMarketFare
- Dimension tables (lightweight):
  - ips.DimCarrier
  - ips.DimAirport     (numeric AirportID; details come from dbo.airports)
  - ips.DimMarket      (OD pair & distance)
*/

------------------------------------------------------------
-- 0. Create schema if it does not exist
------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ips')
BEGIN
    EXEC('CREATE SCHEMA ips');
END;
GO


------------------------------------------------------------
-- 1. Staging table for raw CSV load
--    Loaded by: etl/load_airline_market_fare.py
------------------------------------------------------------
IF OBJECT_ID('dbo.AirlineMarketFare_Staging', 'U') IS NOT NULL
    DROP TABLE dbo.AirlineMarketFare_Staging;
GO

CREATE TABLE dbo.AirlineMarketFare_Staging
(
    MktCoupons                   INT             NOT NULL,
    OriginCityMarketID           INT             NOT NULL,
    DestCityMarketID             INT             NOT NULL,
    OriginAirportID              INT             NOT NULL,
    DestAirportID                INT             NOT NULL,
    Carrier                      INT             NOT NULL,
    NonStopMiles                 FLOAT           NULL,
    RoundTrip                    FLOAT           NULL,
    ODPairID                     INT             NOT NULL,
    Pax                          FLOAT           NULL,
    CarrierPax                   FLOAT           NULL,
    AvgFare                      FLOAT           NULL,
    MarketShare                  FLOAT           NULL,
    MarketHHI                    FLOAT           NULL,
    LCC_Comp                     INT             NULL,
    Multi_Airport                INT             NULL,
    Circuity                     FLOAT           NULL,
    Slot                         INT             NULL,
    Non_Stop                     FLOAT           NULL,
    MktMilesFlown                FLOAT           NULL,
    OriginCityMarketID_freq      FLOAT           NULL,
    DestCityMarketID_freq        FLOAT           NULL,
    OriginAirportID_freq         FLOAT           NULL,
    DestAirportID_freq           FLOAT           NULL,
    Carrier_freq                 FLOAT           NULL,
    ODPairID_freq                FLOAT           NULL
);
GO


------------------------------------------------------------
-- 2. Dimension: Carrier
--    Simple numeric surrogate + original carrier code
------------------------------------------------------------
IF OBJECT_ID('ips.DimCarrier', 'U') IS NOT NULL
    DROP TABLE ips.DimCarrier;
GO

CREATE TABLE ips.DimCarrier
(
    CarrierID   INT IDENTITY(1,1) PRIMARY KEY,
    CarrierCode INT NOT NULL,          -- from raw data "Carrier"
    CarrierName NVARCHAR(100) NULL     -- optional lookup
);
GO


------------------------------------------------------------
-- 3. Dimension: Airport
--    Keyed by numeric AirportID from the raw file.
--    Detailed attributes (name, city, lat/long) can stay in dbo.airports.
------------------------------------------------------------
IF OBJECT_ID('ips.DimAirport', 'U') IS NOT NULL
    DROP TABLE ips.DimAirport;
GO

CREATE TABLE ips.DimAirport
(
    AirportID   INT PRIMARY KEY,       -- matches dbo.airports.AirportID
    IsActive    BIT NOT NULL DEFAULT 1
);
GO


------------------------------------------------------------
-- 4. Dimension: Market (Origin–Destination pair)
------------------------------------------------------------
IF OBJECT_ID('ips.DimMarket', 'U') IS NOT NULL
    DROP TABLE ips.DimMarket;
GO

CREATE TABLE ips.DimMarket
(
    MarketID        INT IDENTITY(1,1) PRIMARY KEY,
    ODPairID        INT NOT NULL,
    OriginAirportID INT NOT NULL,
    DestAirportID   INT NOT NULL,
    NonStopMiles    FLOAT NULL,
    CONSTRAINT UQ_DimMarket_OD UNIQUE (ODPairID)
);
GO


------------------------------------------------------------
-- 5. Fact table: Market-level pricing metrics
------------------------------------------------------------
IF OBJECT_ID('ips.FactMarketFare', 'U') IS NOT NULL
    DROP TABLE ips.FactMarketFare;
GO

CREATE TABLE ips.FactMarketFare
(
    FactMarketFareID INT IDENTITY(1,1) PRIMARY KEY,

    MarketID         INT NOT NULL,
    CarrierID        INT NOT NULL,

    -- Degenerate / redundant keys for easier Tableau usage
    ODPairID         INT NOT NULL,
    OriginAirportID  INT NOT NULL,
    DestAirportID    INT NOT NULL,

    NonStopMiles     FLOAT NULL,
    TotalMilesFlown  FLOAT NULL,
    TotalPax         FLOAT NULL,

    AvgFare          FLOAT NULL,
    AvgMarketShare   FLOAT NULL,
    AvgMarketHHI     FLOAT NULL,
    YieldFarePerMile FLOAT NULL,   -- can be derived later but stored for convenience

    CONSTRAINT FK_FactMarketFare_DimMarket
        FOREIGN KEY (MarketID) REFERENCES ips.DimMarket (MarketID),

    CONSTRAINT FK_FactMarketFare_DimCarrier
        FOREIGN KEY (CarrierID) REFERENCES ips.DimCarrier (CarrierID)
);
GO
