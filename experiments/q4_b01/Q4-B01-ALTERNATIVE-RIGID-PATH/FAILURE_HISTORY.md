# Retained failure history

## Scientific experiments

The complete 62 rejected interior target trials (31 in each direction) are
retained in search_report.json, with actual angles, closure/seam/progress
errors, initial guesses, solver termination and evaluation count. The two
endpoint-only interpolants fail all three checked interior samples. These
negative outcomes remain FAIL; alternative-path existence remains UNKNOWN.

## Implementation verification

After adding the analytic positive-hinge control, the exact manifest test
correctly failed because the test source hash had changed. The other nine
tests passed. Expected prior test-source digest:
f88d833c8c56963ddf5599b20df86df4ca0386c744be7796214771533766201b.
Updated test-source digest:
53351a78cc95cc8641e8020b3796989a96dfa6a5a91e4fd11749be9b8be0f30b.
The evidence manifest is regenerated after final source/document changes;
this bookkeeping failure is not a scientific success or a CP failure.
