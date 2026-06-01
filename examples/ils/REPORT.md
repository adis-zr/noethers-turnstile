# ILS Blind Audit — Report

Generated: 2026-06-01T06:05:25.478177+00:00
Pre-registration sealed: 2026-06-01T05:13:50.655722+00:00

## Setup

Pre-registration was sealed before any FAA document was opened.
All geometric values were derived from constants in `geometry.py`.
The compiler was run on sweeps and compared against FAA thresholds afterward.

## Geometric Constants

- Glideslope: 3.0°
- TCH: 50.0 ft AGL
- Roll bar distance: 1000.0 ft before threshold
- Approach speed: 130.0 kt
- Saturation DH: 102.41 ft
- RVR floor at DH=200 ft: 1862.2 ft
- DH at RVR floor = 1800 ft: 196.7 ft
- Time to threshold at DH=200 ft: 13.0 sec
- Time to threshold at DH=100 ft: 4.3 sec

## Sweep A (f3 absent)

```
=== Sweep_A_f3_absent (DH=200.0 ft, f3=absent) ===
  RVR (ft)     f2    Permission
----------------------------------
      2400      Y           REV
      2300      Y           REV
      2200      Y           REV
      2100      Y           REV
      2000      Y           REV
      1900      Y           REV
      1800      N           DIA
      1700      N           DIA
      1600      N           DIA
      1500      N           DIA
      1400      N           DIA
      1300      N           DIA
      1200      N           DIA
      1100      N           DIA
      1000      N           DIA
       900      N           DIA
       800      N           DIA
       700      N           DIA
       600      N           DIA
       500      N           DIA
       400      N           DIA
       300      N           DIA
       200      N           DIA
       100      N           DIA
         0      N           DIA

Transitions (RVR where permission changes):
  1800 ft: REV → DIA
```

## Sweep B (f3 present)

```
=== Sweep_B_f3_present (DH=200.0 ft, f3=present) ===
  RVR (ft)     f2    Permission
----------------------------------
      2400      Y           ALR
      2300      Y           ALR
      2200      Y           ALR
      2100      Y           ALR
      2000      Y           ALR
      1900      Y           ALR
      1800      N           ALR
      1700      N           ALR
      1600      N           ALR
      1500      N           ALR
      1400      N           ALR
      1300      N           ALR
      1200      N           ALR
      1100      N           ALR
      1000      N           ALR
       900      N           ALR
       800      N           ALR
       700      N           ALR
       600      N           ALR
       500      N           ALR
       400      N           ALR
       300      N           ALR
       200      N           ALR
       100      N           ALR
         0      N           ALR

No transitions (permission constant across sweep)
```

## FAA Regulatory Correspondence

```
=== FAA Regulatory Correspondence ===

Category        FAA RVR (ft)   Compiler (ft)  Classification              
----------------------------------------------------------------------------
CAT_I                   1800            1800  EXACT                       
CAT_II                  1200               —  OFFSET_DIFFERENT_AXIS       
CAT_IIIa                 700               —  COMPILER_PERMISSIVE         
CAT_IIIb                 150               —  COMPILER_PERMISSIVE         
CAT_IIIc                none               —  COMPILER_PERMISSIVE         

=== Explanations ===

CAT_I (EXACT):
  Compiler transition at 1800 ft matches FAA CAT I minimum of 1800 ft (within sweep resolution of 100 ft). Physical geometry recovers the regulatory boundary without consulting FAA documents.

CAT_II (OFFSET_DIFFERENT_AXIS):
  At DH=100 ft (below saturation ~102 ft), f2 is always clear (aircraft has passed roll bar at DH). Compiler grants LAND_MANUAL at all RVR values — no geometric floor remains. FAA CAT II minimum of 1200 ft exists on a different evidence axis: human factors / reaction time (4.3 sec to threshold), not recoverable from RVR geometry. The boundary exists but is orthogonal to the compiler's evidence space.

CAT_IIIa (COMPILER_PERMISSIVE):
  CAT_IIIa: FAA minimum is 700 ft. Compiler has no basis for any positive RVR floor once f2 saturates. Autoland certification and operator qualification are orthogonal to the RVR evidence space — the evidence type is wrong, not merely the threshold. This is a structural absence, not an offset.

CAT_IIIb (COMPILER_PERMISSIVE):
  CAT_IIIb: FAA minimum is 150 ft. Compiler has no basis for any positive RVR floor once f2 saturates. Autoland certification and operator qualification are orthogonal to the RVR evidence space — the evidence type is wrong, not merely the threshold. This is a structural absence, not an offset.

CAT_IIIc (COMPILER_PERMISSIVE):
  CAT_IIIc: FAA minimum is none (zero-zero). Compiler has no basis for any positive RVR floor once f2 saturates. Autoland certification and operator qualification are orthogonal to the RVR evidence space — the evidence type is wrong, not merely the threshold. This is a structural absence, not an offset.
```

## Summary

**CAT_I** (EXACT): Compiler transition at 1800 ft matches FAA CAT I minimum of 1800 ft (within sweep resolution of 100 ft). Physical geometry recovers the regulatory boundary without consulting FAA documents.

**CAT_II** (OFFSET_DIFFERENT_AXIS): At DH=100 ft (below saturation ~102 ft), f2 is always clear (aircraft has passed roll bar at DH). Compiler grants LAND_MANUAL at all RVR values — no geometric floor remains. FAA CAT II minimum of 1200 ft exists on a different evidence axis: human factors / reaction time (4.3 sec to threshold), not recoverable from RVR geometry. The boundary exists but is orthogonal to the compiler's evidence space.

**CAT_IIIa** (COMPILER_PERMISSIVE): CAT_IIIa: FAA minimum is 700 ft. Compiler has no basis for any positive RVR floor once f2 saturates. Autoland certification and operator qualification are orthogonal to the RVR evidence space — the evidence type is wrong, not merely the threshold. This is a structural absence, not an offset.

**CAT_IIIb** (COMPILER_PERMISSIVE): CAT_IIIb: FAA minimum is 150 ft. Compiler has no basis for any positive RVR floor once f2 saturates. Autoland certification and operator qualification are orthogonal to the RVR evidence space — the evidence type is wrong, not merely the threshold. This is a structural absence, not an offset.

**CAT_IIIc** (COMPILER_PERMISSIVE): CAT_IIIc: FAA minimum is none (zero-zero). Compiler has no basis for any positive RVR floor once f2 saturates. Autoland certification and operator qualification are orthogonal to the RVR evidence space — the evidence type is wrong, not merely the threshold. This is a structural absence, not an offset.

## Architectural Finding

The ILS framework is architecturally different from 3GPP. In 3GPP, the compiler recovered all boundaries from a single evidence axis (mean-like SNR vs worst-case error floor). In ILS, the compiler recovers the CAT I physical floor (EXACT) but cannot recover CAT II/III boundaries — those require evidence types orthogonal to RVR geometry (human factors certification, autoland qualification). This is a COMPILER_PERMISSIVE failure, not an OFFSET: the evidence axis is wrong, not merely the threshold on a shared axis. Predicted before any FAA document is consulted.
