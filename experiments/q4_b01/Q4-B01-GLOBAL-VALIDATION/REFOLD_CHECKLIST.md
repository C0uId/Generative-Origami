# Diagnostic physical-refold package

This is a traceable human-test kit, not a validated folding sequence or a
production tutorial. No successful specimen or independent refold is claimed.
The uniform-angle software trial fails closure; it must not be used as human
folding instructions. A human attempt may stop without producing a model.

## Intake and orientation

1. Record the candidate geometry hash from `global_validation.json`, the exact
   file hashes from `evidence_manifest.json`, operator and date in a copy of
   `physical_evidence_template.json`. Do not overwrite the blank template.
2. Use one square sheet, 200 x 200 mm, without cutting or glue. Record actual
   dimensions, material, thickness/weight if measurable, batch/source and front
   marking. Record deviations; they do not automatically pass the gate.
3. Print `printable_cp.svg` on A4 at 100%, without fit-to-page; measure the square
   as 200 x 200 mm. Check both axes and ruler calibration before transferring.
4. With the marked front facing the viewer, origin is lower-left, +x right and
   +y up. M is a ridge toward the viewer; V is a hollow toward the viewer.
   Reverse the viewing convention on the back; do not reassign edge IDs.
5. Cross-check every B/M/V edge with `candidate.fold` and `stable_ids.json`.
   Black solid B is the sheet boundary, red solid M is mountain, blue dashed V
   is valley. Grey dotted material-region guides are not fold instructions.
   Verify vertices V00..V10, edges E00..E17 and faces FACE_Q4_MM_00..07.

## Exploratory attempt and stop conditions

6. Photograph the flat front/back with scale and IDs visible. Record crease
   marking or precreasing actions individually; there is no approved action
   order. Do not claim that the printed CP supplies a complete folding sequence.
7. If an operator attempts to find a compatible folding sequence, record every
   macro-action in order: moved face/edge IDs, direction, approximate angles,
   reference front/back, contact observations, and video/photo references.
   Stop and record the state if the sheet requires stretching, tearing, cuts,
   glue, unrecorded new creases or forced penetration. Do not report an
   interrupted or modified attempt as a successful refold of this candidate.
8. For each observed contact distinguish touching from penetration and attach
   face/material correspondence, layer order and signed-gap measurements if
   available. Unmeasured quantities remain UNKNOWN; visual proximity is not a
   continuous collision certificate.
9. If a specimen is achieved, unfold and reconstruct/cross-check the full CP,
   including M/V, front/back and stable IDs. Map MAT_HEAD, MAT_BODY, MAT_FL,
   MAT_FR, MAT_HL, MAT_HR and MAT_TAIL to final parts with images and references.
   Record failures and ambiguity instead of silently changing semantic ownership.

## Evidence and independent repeats

10. Each media/data file needs its actual filename, SHA-256 and usage rights.
    Record design specimen and both independent refolds separately. Leave
    NOT_RUN and UNKNOWN in place until observations exist.
11. Only after an explicit reproducible sequence is documented should two
    independent operators/attempts beyond the first design specimen try that
    same candidate. Record independence, paper differences, complete sequence,
    outcome and material correspondence separately for each repeat.
12. Send the recorded package for technical review. No certification follows
    from the kit, local theorem checks, a sampled probe, or software tests.
