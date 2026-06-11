# FTAS SEM — Stage 0 (CFA) and Stage 1 (full sample)

## CFA: do the three satisfaction items form one latent?
Verdict: ACCEPTABLE — latent retained
```
         lval op          rval  Estimate  Est. Std  Std. Err p-value
  sat_overall  ~  SATISFACTION  1.000000  0.866797         -       -
sat_transport  ~  SATISFACTION  0.697967  0.527609  0.009866     0.0
  sat_product  ~  SATISFACTION  1.022773  0.860334  0.011386     0.0
 SATISFACTION ~~  SATISFACTION  0.352064  1.000000  0.005714     0.0
  sat_overall ~~   sat_overall  0.116520  0.248664  0.003631     0.0
  sat_product ~~   sat_product  0.129278  0.259825  0.003823     0.0
sat_transport ~~ sat_transport  0.444612  0.721629  0.004775     0.0
```

## Stage 1: friction -> satisfaction -> intention (n=15,776 deduplicated respondents)
Exposure = reported_inconvenience (asked of all respondents; selection-bias-free).
Indicators standardized; friction left binary, so paths are in SD units per friction exposure.
```
          lval op           rval  Estimate  Est. Std  Std. Err p-value
  SATISFACTION  ~       friction -0.475746 -0.206473  0.019574     0.0
     INTENTION  ~   SATISFACTION  0.391986  0.801159  0.009518     0.0
     INTENTION  ~       friction -0.072501 -0.064310  0.010462     0.0
   sat_overall  ~   SATISFACTION  1.000000  0.871088         -       -
 sat_transport  ~   SATISFACTION  0.589079  0.513064  0.009269     0.0
   sat_product  ~   SATISFACTION  0.966718  0.842061  0.009386     0.0
intent_revisit  ~      INTENTION  1.000000  0.426162         -       -
    intent_nps  ~      INTENTION  1.656678  0.706010  0.040826     0.0
     INTENTION ~~      INTENTION  0.060428  0.332732  0.004106     0.0
  SATISFACTION ~~   SATISFACTION  0.726306  0.957369  0.011852     0.0
    intent_nps ~~     intent_nps  0.501548  0.501550  0.012937     0.0
intent_revisit ~~ intent_revisit  0.818377  0.818386  0.010144     0.0
   sat_overall ~~    sat_overall  0.241159  0.241206  0.006288     0.0
   sat_product ~~    sat_product  0.290902  0.290933  0.006254     0.0
 sat_transport ~~  sat_transport  0.736837  0.736765  0.008789     0.0
```

## Fit indices
```
                    model       chi2   df      CFI      TLI    RMSEA     n
         CFA_satisfaction   0.006844  0.0 1.000000      NaN      inf 19768
       Stage1_full_sample 253.323472  8.0 0.989977 0.979953 0.044090 15776
Stage2_friction_reporters 282.935508 52.0 0.906406 0.886607 0.042131  2503
```

Caveats: indicators are 5-point ordinal treated as continuous (ML); at this
n everything is significant — interpret standardized magnitudes, not p-values.