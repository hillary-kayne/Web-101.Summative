# Source: WRAP UK, "Textiles 2030 Annual Progress Update 2022-23"
# https://www.wrap.ngo/resources/report/textiles-2030-annual-progress-update-2022-23
CO2_KG_SAVED_PER_KG = {
    "resold": 4.0,
    "recycled": 0.7,
}

# Not from WRAP directly, I derived this from their reuse/recycling totals
# (385M m3 water / 233,500 t textiles ~= 1649 L/kg). WRAP doesn't split
# water by method like it does CO2, so I use one blended rate for both.
WATER_LITRES_SAVED_PER_KG = 1649.0

# EFSA adequate intake guidance, ~2L/day, just for the "days of drinking
# water" framing on the dashboard.
AVG_DAILY_DRINKING_WATER_L = 2.0

# Rough averages, not sourced, just typical garment weights for when the
# user skips the weight field.
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

GENERIC_FALLBACK_WEIGHT_KG = 0.5


def default_weight_for_category(category):
    return DEFAULT_CATEGORY_WEIGHTS_KG.get(category, GENERIC_FALLBACK_WEIGHT_KG)


def calc_impact(weight_kg, method):
    co2_rate = CO2_KG_SAVED_PER_KG.get(method, CO2_KG_SAVED_PER_KG["recycled"])
    water_saved_l = round(weight_kg * WATER_LITRES_SAVED_PER_KG, 1)
    co2_saved_kg = round(weight_kg * co2_rate, 2)
    return water_saved_l, co2_saved_kg
