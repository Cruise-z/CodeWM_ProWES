# Local modifications

RQ1 is released as a frozen source snapshot because the supplied workspace did
not retain a clean patch series against every watermark upstream. Method-level
source provenance is recorded beside CodeIP, and the exact complete snapshot is
checksummed by this artifact.

The released RQ2 implementation and its exact protocol are documented in
`RQ2/source/README.md`.
The fresh-training checkout was based on SrcMarker commit
`2fb71cf816c12b0b07bb4d84dbe44ca0816662eb`; changed files are listed in
`00_common/upstream_commits/METHODS.md` and preserved in the source bundle.

Reviewer-facing English normalization is separately documented in
`LANGUAGE_NORMALIZATION.md`; immutable upstream snapshots and raw evidence are
kept byte-faithful as explained in `../LANGUAGE_AUDIT.md`.
