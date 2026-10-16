---
type: "concept"
title: "Explainable Machine Learning-Based Approach to Developing Potent EGFR Inhibitors for Ovarian Cancer"
tags: ["project","Python","Scikit-Learn","RDKit","Mordred","SHAP","Gradient Boosting","Random Forest","ChEMBL"]
source: "portfolio_data.json#projects/Explainable Machine Learning-Based Approach to Developing Potent EGFR Inhibitors for Ovarian Cancer"
---

# Explainable Machine Learning-Based Approach to Developing Potent EGFR Inhibitors for Ovarian Cancer

- **Type:** Research / Explainable ML

- **Subtitle:** M.Tech Thesis · Explainable AI · Drug Discovery

- **Description:** M.Tech thesis developing an explainable ML framework for EGFR inhibitor discovery in ovarian cancer. More than 1,800 RDKit and Mordred descriptors were reduced through LASSO selection. Six classifiers were tuned using GridSearchCV and four-fold cross-validation. Random Forest reached 93% accuracy and tuned Gradient Boosting reached 98.28%. SHAP force and waterfall plots explained activity-driving descriptors.

## Tech Stack

- Python
- Scikit-Learn
- RDKit
- Mordred
- SHAP
- Gradient Boosting
- Random Forest
- ChEMBL

## Thesis Details

- **Dataset:** 310 molecules from ChEMBL, EGFR target CHEMBL3009

- **Descriptors:** More than 1,800 RDKit + Mordred descriptors, reduced through LASSO selection

- **Best Model:** Tuned Gradient Boosting — 98.28% accuracy

- **Second Best:** Random Forest — 93% accuracy

- **Xai Tool:** SHAP (force plots + waterfall plots)

### Key Descriptors

- PEOE_VSA9
- SM_VSA10
- fr_bicyclic
- pIC50
- BCUT2D_MRLOW

- **Institution:** SASTRA Deemed University, M.Tech Big Data Biology

- **Validation:** GridSearchCV with four-fold cross-validation
