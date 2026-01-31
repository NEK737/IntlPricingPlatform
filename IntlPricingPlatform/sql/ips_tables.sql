CREATE DATABASE IntlPricingDB;
GO
--- check for data insterted by ETL
USE IntlPricingDB;
SELECT TOP (20) * FROM AirlineMarketFare_Staging;

USE IntlPricingDB;
SELECT COUNT(*)

SELECT TOP (20) * FROM AirlineMarketFare_Staging;

USE IntlPricingDB;
GO

SELECT COUNT(*) AS Count
FROM dbo.AirlineMarketFare_Staging;
GO

USE IntlPricingDB;
GO
--1️ Create a dedicated schema
-- Optional, but keeps things tidy
CREATE SCHEMA ips;
GO

-- Create core tables
-- a) ips.DimMarket – one row per OD pair (origin–destination)
USE IntlPricingDB;
GO

CREATE TABLE ips.DimMarket (
    MarketKey           INT IDENTITY(1,1) PRIMARY KEY,
    ODPairID            INT NOT NULL UNIQUE,
    OriginCityMarketID  INT NOT NULL,
    DestCityMarketID    INT NOT NULL,
    OriginAirportID     INT NOT NULL,
    DestAirportID       INT NOT NULL,
    NonStopMiles        FLOAT NOT NULL,
    Circuity            FLOAT NULL,
    Multi_Airport       INT NOT NULL,
    LCC_Comp            INT NOT NULL,
    Slot                INT NOT NULL,
    Non_Stop            FLOAT NOT NULL
);
GO
---b) ips.DimCarrier – one row per carrier code

CREATE TABLE ips.DimCarrier (
    CarrierKey  INT IDENTITY(1,1) PRIMARY KEY,
    CarrierID   INT NOT NULL UNIQUE
);
GO

---c) ips.FactMarketFare – metrics per Market + Carrier
CREATE TABLE ips.FactMarketFare (
    FactKey                 BIGINT IDENTITY(1,1) PRIMARY KEY,
    MarketKey               INT NOT NULL,
    CarrierKey              INT NOT NULL,
    MktCoupons              INT NOT NULL,
    RoundTrip               FLOAT NOT NULL,
    Pax                     FLOAT NOT NULL,
    CarrierPax              FLOAT NOT NULL,
    Average_Fare            FLOAT NOT NULL,
    Market_share            FLOAT NOT NULL,
    Market_HHI              FLOAT NOT NULL,
    MktMilesFlown           FLOAT NOT NULL,
    OriginCityMarketID_freq FLOAT NOT NULL,
    DestCityMarketID_freq   FLOAT NOT NULL,
    OriginAirportID_freq    FLOAT NOT NULL,
    DestAirportID_freq      FLOAT NOT NULL,
    Carrier_freq            FLOAT NOT NULL,
    ODPairID_freq           FLOAT NOT NULL,
    CONSTRAINT FK_Fact_Market
        FOREIGN KEY (MarketKey) REFERENCES ips.DimMarket(MarketKey),
    CONSTRAINT FK_Fact_Carrier
        FOREIGN KEY (CarrierKey) REFERENCES ips.DimCarrier(CarrierKey)
);
GO

--- 3 Populate the dimension tables from staging
USE IntlPricingDB;
GO

-- 1) Markets
TRUNCATE TABLE ips.DimMarket;
GO

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
    ODPairID,
    MIN(OriginCityMarketID),
    MIN(DestCityMarketID),
    MIN(OriginAirportID),
    MIN(DestAirportID),
    MIN(NonStopMiles),
    MIN(Circuity),
    MIN(Multi_Airport),
    MIN(LCC_Comp),
    MIN(Slot),
    MIN(Non_Stop)
FROM dbo.AirlineMarketFare_Staging
GROUP BY ODPairID;
GO

SELECT COUNT(*) AS MarketCount FROM ips.DimMarket;
GO

-- 2) Carriers
INSERT INTO ips.DimCarrier (CarrierID)
SELECT DISTINCT
    s.Carrier
FROM dbo.AirlineMarketFare_Staging AS s;
GO

SELECT COUNT(*) AS MarketCount FROM ips.DimMarket;
SELECT COUNT(*) AS CarrierCount FROM ips.DimCarrier;


--- 4)Populate the fact table
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
GO

SELECT COUNT(*) AS FactRows FROM ips.FactMarketFare;
