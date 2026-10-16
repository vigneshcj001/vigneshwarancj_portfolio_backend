---
type: "concept"
title: "GlycanBench: a unified resource for working with glycans"
tags: ["project","Python","FastAPI","Pydantic","React 19","TypeScript","Vite","Tailwind CSS 4","PyTorch","PyTorch Geometric"]
source: "portfolio_data.json#projects/GlycanBench: a unified resource for working with glycans"
---

# GlycanBench: a unified resource for working with glycans

- **Type:** AI/Research Platform

- **Subtitle:** Glycoinformatics Web Server + Python Package · SASTRA University

- **Description:** Full-stack glycoinformatics platform and installable Python package built with Ashok Palaniappan at SASTRA's Systems Computational Biology Lab. React 19 and FastAPI expose 20 tools for glycan creation, SNFG 2D and on-demand 3D conformers, format conversion, molecular descriptors, fingerprint comparison, GLYSUM Needleman-Wunsch alignment, clustering, immunogenicity prediction, and literature-aware chat. The PyTorch Geometric MPNN uses 1,344 curated glycans after correcting 12 contradictory labels across two datasets. GlycomicsChat routes Groq/LangChain requests to PubMed, ArXiv, and GlyTouCan. Distributed as web app, SDK, CLI, and FastAPI server with tests and notebooks.

## Tech Stack

- Python
- FastAPI
- Pydantic
- React 19
- TypeScript
- Vite
- Tailwind CSS 4
- PyTorch
- PyTorch Geometric
- RDKit
- glycowork
- glypy
- BioPython
- scikit-learn
- SciPy
- LangChain
- Groq
- 3Dmol.js
- Cytoscape.js
- Chart.js

- **Developer:** Vigneshwaran CJ

- **Guide:** Ashok Palaniappan

- **Institution:** Systems Computational Biology Lab, Bioinformatics Center, School of Chemical & Biotechnology, SASTRA Deemed University

- **Contact:** apalania@scbt.sastra.edu

- **Citation:** Vigneshwaran CJ & Ashok Palaniappan. GlycanBench: a unified resource for working with glycans, 2026 [submitted]

- **Role:** Full-stack development, ML model integration, glycoinformatics pipeline, Python package

- **Live Link:** https://glycanbench.sastra.edu/

- **Github:** https://github.com/APalaniaLab/GlycanBench

## Features

- Create: Glycan Molecule builder (SNFG 2D + 3D conformer), Biosynthetic Networks (Cytoscape.js), Format Converter (IUPAC/WURCS/GlycoCT/SMILES)
- Visualize: 2D SNFG draw with motif highlight, 3D viewer (3Dmol.js, 4 styles), KEGG pathway maps with search
- Analyse: Monosaccharide characterisation, Glycan Insight (species, phyla, motifs, diseases, GlyTouCan ID), Molecule Descriptors, Motif Mutation
- Compare: Tanimoto similarity across Morgan R2/R3, AtomPair, Torsion and RDKit fingerprints
- Align: Needleman-Wunsch with GLYSUM glycan substitution matrix or custom scoring
- Cluster: agglomerative/K-means with Tanimoto/Dice/Cosine/Euclidean/glycowork metrics, elbow plot, outlier detection
- Predict: MPNN immunogenicity with confidence score and rule-based motif flags
- Chat: GlycomicsChat — Groq gpt-oss-120b, LLM tool router over PubMed, ArXiv, GlyTouCan
- Python package: glycanbench SDK, CLI and server modes (MIT)

- **Note:** Public source repository maintained in the APalaniaLab GitHub organisation.

- **Pypi:** https://pypi.org/project/glycanbench/

- **Doi:** https://doi.org/10.5281/zenodo.22756268
