-- All markets, all carriers
EXEC ips.usp_GetMarketPricingSummary;

-- Only markets longer than 2000 miles
EXEC ips.usp_GetMarketPricingSummary @MinNonStopMiles = 2000;

-- Only one carrier (e.g., CarrierID 6)
EXEC ips.usp_GetMarketPricingSummary @CarrierID = 6;

-- Only markets where carrier share is between 20% and 60%
EXEC ips.usp_GetMarketPricingSummary
    @MinMarketShare = 0.2,
    @MaxMarketShare = 0.6;
