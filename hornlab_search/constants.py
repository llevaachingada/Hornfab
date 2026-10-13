"""Physical constants and design-check relations. Nothing else hardcodes these."""

C_AIR = 343.0        # m/s, 20 C. Use this everywhere. Not 344.
RHO_AIR = 1.204      # kg/m^3
REF_P = 20e-6        # Pa

# Pattern-control break frequency (Hughes, Understanding Horn Directivity Control).
#   f0 = KEELE_K / (mouth_dimension_m * coverage_angle_deg)
# Verified against the source's worked examples: 12 in / 90 deg -> 926 Hz.
KEELE_K = 25400.0    # m * deg * Hz

# First non-axisymmetric duct mode in a circular throat of radius a:
#   f11 = BESSEL_J1P_11 * C_AIR / (2 * pi * a)
# The sizes below are throat DIAMETERS (compute_metrics takes throat_radius_m):
# 0.5 in radius = 1.0 in dia -> 7914 Hz, 0.7 in dia -> 5653 Hz, 1.0 in dia -> 3957 Hz.
BESSEL_J1P_11 = 1.8412

# MEH quarter-wavelength entry rule: d <= C_AIR / (4 * f_crossover)
MEH_ENTRY_FRACTION = 0.25
