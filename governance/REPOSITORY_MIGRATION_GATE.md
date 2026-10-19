# Repository Migration Gate

The Generative Origami repository migration is not complete until the entire effective project has been organized and represented in Git.

## Required in normal Git
- current source code;
- current tests;
- project/governance documents;
- Q4-B01 and POC01-010A implementation;
- experiment scripts, inputs, summaries and reproducible metadata;
- current FOLD/SVG samples and demo assets;
- tooling required to reproduce the accepted results.

## Large experimental evidence
Historical C3 evidence expands to roughly 1.4 GB and includes individual generated files far larger than normal source files. These artifacts must not be silently discarded or duplicated as ordinary Git history.

They are handled as large immutable evidence assets (Git LFS or equivalent artifact storage) with:
- SHA-256 manifest;
- experiment/version identifier;
- source code and parameters needed for regeneration;
- explicit link/reference from the experiment directory.

## Completion criteria
Migration status may be marked COMPLETE only after:
1. obsolete and duplicate snapshots are removed;
2. a single current project tree exists;
3. core regression suite passes;
4. current Q4 regression suite passes;
5. all effective project files are committed or represented by immutable large-asset references;
6. the Git main branch is the authoritative project baseline.

Current verified pre-migration tests:
- core engine: 112/112 PASS;
- Q4 / POC01-010A: 28/28 PASS.
