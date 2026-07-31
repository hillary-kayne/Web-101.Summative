# Avoided-impact factors: these estimate the gap between manufacturing a NEW
# replacement garment from raw fiber versus the old one being reused or
# recycled instead. They are not measurements of the specific item logged.
#
# Source: WRAP (Waste & Resources Action Programme, UK), "Textiles 2030 Annual
# Progress Update 2022-23" (published 2023, reporting on 2022 signatory activity).
# https://www.wrap.ngo/resources/report/textiles-2030-annual-progress-update-2022-23
#
# CO2: WRAP reports an average net carbon saving of 4.0 tonnes CO2e per tonne
# of clothing reused, and 0.7 tonnes CO2e per tonne recycled, each relative to
# the equivalent new garment being manufactured. That's 4.0 kg / 0.7 kg CO2e
# avoided per kg diverted.
CO2_KG_SAVED_PER_KG = {
    "resold": 4.0,
    "recycled": 0.7,
}

# Water: the same WRAP update reports that 2022 reuse-and-recycling activity
# (233,500 tonnes of textiles handled) avoided roughly 385 million cubic
# metres of water versus producing that volume of clothing new. WRAP doesn't
# split this figure by reuse vs. recycling the way it does for CO2, so we use
# the blended rate for both methods: 385,000,000 m3 / 233,500 t = ~1,649 m3/t
# = ~1,649 litres avoided per kg diverted. Derived by us from WRAP's public
# figures, not a number WRAP itself publishes per kg.
WATER_LITRES_SAVED_PER_KG = 1649.0

# Average adult daily drinking-water intake, used only to translate the water
# total into a relatable "X days of drinking water" figure on the dashboard.
# Source: European Food Safety Authority (EFSA) adequate intake guidance,
# ~2.0 litres/day (women) - we use 2.0 L/day as a simple round figure.
AVG_DAILY_DRINKING_WATER_L = 2.0

# Sensible default weights (kg) per garment category, used when the user
# doesn't know the exact weight of an item. Rough real-world averages, not
# from a cited study - just typical garment weights.
DEFAULT_CATEGORY_WEIGHTS_KG = {
    "cotton_tshirt": 0.2,
    "jeans": 0.8,
    "wool_sweater": 0.6,
    "synthetic_jacket": 0.9,
    "dress": 0.4,
    "shoes": 0.9,
    "bedding_linens": 1.2,
    "other": 0.5,
}

# Fallback for categories the user typed that we don't recognize at all -
# entries are never rejected for an unknown category, just costed generically.
GENERIC_FALLBACK_WEIGHT_KG = 0.5


def default_weight_for_category(category):
    return DEFAULT_CATEGORY_WEIGHTS_KG.get(category, GENERIC_FALLBACK_WEIGHT_KG)


def calc_impact(weight_kg, method):
    co2_rate = CO2_KG_SAVED_PER_KG.get(method, CO2_KG_SAVED_PER_KG["recycled"])
    water_saved_l = round(weight_kg * WATER_LITRES_SAVED_PER_KG, 1)
    co2_saved_kg = round(weight_kg * co2_rate, 2)
    return water_saved_l, co2_saved_kg
