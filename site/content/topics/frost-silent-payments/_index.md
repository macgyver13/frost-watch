---
title: "FROST + Silent Payments overlap"
---


> Working notes. FROST Watch aggregates public-source activity related to FROST and directly related dependencies. Inclusion means only that a source matched the monitoring criteria. This site does not provide technical review, endorsement, security assessment, production-readiness judgment, or a canonical roadmap.

This topic tracks the intersection between FROST and Silent Payments integration work.

## Initial areas to track

- Verification-share availability: FROST verifying shares are DKG outputs and must be available to DLEQ verifiers.
- Key management and hardware-signer UX: FROST shares are Shamir shares and require persistence/recovery beyond ordinary BIP-32 seed derivation.
- Epoch consistency: refreshed or reshared participant shares must not be mixed across epochs.
- PSBT/group-config surfaces for FROST configuration, signing commitments, signature shares, and participant verifying shares.

Future updates should link back to structured feed items and public sources.
