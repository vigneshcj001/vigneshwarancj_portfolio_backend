---
type: project
title: 'GlycanBench: a unified resource for working with glycans'
order: 1
data:
  type: AI/Research Platform
  subtitle: Glycoinformatics Web Server + Python Package · SASTRA University
  description: Full-stack glycoinformatics platform and installable Python package built with Ashok Palaniappan at SASTRA's
    Systems Computational Biology Lab. React 19 and FastAPI expose 20 tools for glycan creation, SNFG 2D and on-demand 3D
    conformers, format conversion, molecular descriptors, fingerprint comparison, GLYSUM Needleman-Wunsch alignment, clustering,
    immunogenicity prediction, and literature-aware chat. The PyTorch Geometric MPNN uses 1,344 curated glycans after correcting
    12 contradictory labels across two datasets. GlycomicsChat routes Groq/LangChain requests to PubMed, ArXiv, and GlyTouCan.
    Distributed as web app, SDK, CLI, and FastAPI server with tests and notebooks. The deduplicated training set is balanced
    (672 immunogenic, 672 non-immunogenic) with a stratified 80/20 split. On the evaluation set reported in the submitted
    paper (633 glycans, 179 immunogenic), the MPNN reaches AUC-ROC 0.983, MCC 0.899, accuracy 0.959 and F1 0.927. GAT, GIN
    and LSTM baselines were trained for comparison.
  evaluation:
    model: MPNN immunogenicity classifier (PyTorch Geometric), compared with GAT, GIN and LSTM baselines
    training_data: 1,344 unique glycans after resolving 12 contradictory labels (672 positive, 672 negative); stratified 80/20 split
    reported_evaluation_set: 633 glycans (179 immunogenic, 454 non-immunogenic), as reported in the submitted paper's Table 1
    auc_roc: '0.983'
    auc_pr: '0.952'
    mcc: '0.899'
    accuracy: '0.959'
    balanced_accuracy: '0.949'
    f1_immunogenic: '0.927'
    confusion_matrix: TN 441, FP 13, FN 13, TP 166
  novel_contributions:
  - 'First web aligner using the GLYSUM glycan substitution matrix (Needleman-Wunsch with fuzzy token resolution); earlier
    web alignment (SweetAlign, 2006) used simple match/mismatch scoring'
  - 'On-demand 3D conformers for any IUPAC glycan (ETKDGv3, then MMFF94s, with a UFF fallback); GLYCAM-Web offers higher-quality
    force fields but only for a pre-built library'
  - 'Public web immunogenicity predictor (MPNN with AlphaGal, Neu5Gc and complex N-glycan rule flags); GlyNet and glycowork
    classifiers are programmatic only'
  - 'Interactive motif mutation tool with pentamer glycoword frequencies; no published interactive equivalent was found'
  - 'One request returns IUPAC, SMILES, GlycoCT and WURCS, with unsupported conversions reported explicitly'
  - 'Multi-fingerprint comparison (Morgan R2/R3, Atom Pair, Torsion, RDKit) and clustering with runtime-selectable metrics,
    including glycowork graph similarity'
  - 'GlycomicsChat: glycomics-restricted assistant whose LLM router selects PubMed, ArXiv or GlyTouCan per question, with
    a keyword fallback'
  tech_stack:
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
  developer: Vigneshwaran CJ
  guide: Ashok Palaniappan
  institution: Systems Computational Biology Lab, Bioinformatics Center, School of Chemical & Biotechnology, SASTRA Deemed
    University
  contact: apalania@scbt.sastra.edu
  citation: 'Vigneshwaran CJ & Ashok Palaniappan. GlycanBench: a unified resource for working with glycans, 2026 [submitted]'
  role: Full-stack development, ML model integration, glycoinformatics pipeline, Python package
  live_link: https://glycanbench.sastra.edu/
  github: https://github.com/APalaniaLab/GlycanBench
  features:
  - 'Create: Glycan Molecule builder (SNFG 2D + 3D conformer), Biosynthetic Networks (Cytoscape.js), Format Converter (IUPAC/WURCS/GlycoCT/SMILES)'
  - 'Visualize: 2D SNFG draw with motif highlight, 3D viewer (3Dmol.js, 4 styles), KEGG pathway maps with search'
  - 'Analyse: Monosaccharide characterisation, Glycan Insight (species, phyla, motifs, diseases, GlyTouCan ID), Molecule Descriptors,
    Motif Mutation'
  - 'Compare: Tanimoto similarity across Morgan R2/R3, AtomPair, Torsion and RDKit fingerprints'
  - 'Align: Needleman-Wunsch with GLYSUM glycan substitution matrix or custom scoring'
  - 'Cluster: agglomerative/K-means with Tanimoto/Dice/Cosine/Euclidean/glycowork metrics, elbow plot, outlier detection'
  - 'Predict: MPNN immunogenicity with confidence score and rule-based motif flags'
  - 'Chat: GlycomicsChat — Groq gpt-oss-120b, LLM tool router over PubMed, ArXiv, GlyTouCan'
  - 'Python package: glycanbench SDK, CLI and server modes (MIT)'
  note: Public source repository maintained in the APalaniaLab GitHub organisation.
  pypi: https://pypi.org/project/glycanbench/
  doi: https://doi.org/10.5281/zenodo.22756268
---

# GlycanBench: a unified resource for working with glycans

Full-stack glycoinformatics platform and installable Python package built with Ashok Palaniappan at SASTRA's Systems Computational Biology Lab. React 19 and FastAPI expose 20 tools for glycan creation, SNFG 2D and on-demand 3D conformers, format conversion, molecular descriptors, fingerprint comparison, GLYSUM Needleman-Wunsch alignment, clustering, immunogenicity prediction, and literature-aware chat. The PyTorch Geometric MPNN uses 1,344 curated glycans after correcting 12 contradictory labels across two datasets. GlycomicsChat routes Groq/LangChain requests to PubMed, ArXiv, and GlyTouCan. Distributed as web app, SDK, CLI, and FastAPI server with tests and notebooks.

On the evaluation set reported in the submitted paper (633 glycans, 179 immunogenic), the MPNN immunogenicity classifier reaches AUC-ROC 0.983, MCC 0.899, accuracy 0.959 and F1 0.927, compared against GAT, GIN and LSTM baselines.

Compared with existing tools, GlycanBench adds the first web aligner using the GLYSUM substitution matrix, on-demand 3D conformers for any IUPAC glycan rather than a pre-built library, a public web immunogenicity predictor, an interactive motif mutation tool, single-request conversion across four glycan formats, and a glycomics-restricted chat assistant that routes questions to PubMed, ArXiv, or GlyTouCan.
