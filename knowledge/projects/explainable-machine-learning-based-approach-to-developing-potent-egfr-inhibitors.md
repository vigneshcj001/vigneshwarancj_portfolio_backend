---
type: project
title: Explainable Machine Learning-Based Approach to Developing Potent EGFR Inhibitors for Ovarian Cancer
order: 2
data:
  type: Research / Explainable ML
  subtitle: M.Tech Thesis · Explainable AI · Drug Discovery
  description: M.Tech thesis developing an explainable ML framework for EGFR inhibitor discovery in ovarian cancer. More than
    1,800 RDKit and Mordred descriptors were reduced through LASSO selection. Six classifiers were tuned using GridSearchCV
    and four-fold cross-validation. Random Forest reached 93% accuracy and tuned Gradient Boosting reached 98.28%. SHAP force
    and waterfall plots explained activity-driving descriptors.
  tech_stack:
  - Python
  - Scikit-Learn
  - RDKit
  - Mordred
  - SHAP
  - Gradient Boosting
  - Random Forest
  - ChEMBL
  thesis_details:
    dataset: 310 molecules from ChEMBL, EGFR target CHEMBL3009
    descriptors: More than 1,800 RDKit + Mordred descriptors, reduced through LASSO selection
    best_model: Tuned Gradient Boosting — 98.28% accuracy
    second_best: Random Forest — 93% accuracy
    xai_tool: SHAP (force plots + waterfall plots)
    key_descriptors:
    - PEOE_VSA9
    - SM_VSA10
    - fr_bicyclic
    - pIC50
    - BCUT2D_MRLOW
    institution: SASTRA Deemed University, M.Tech Big Data Biology
    validation: GridSearchCV with four-fold cross-validation
---

# Explainable Machine Learning-Based Approach to Developing Potent EGFR Inhibitors for Ovarian Cancer

M.Tech thesis developing an explainable ML framework for EGFR inhibitor discovery in ovarian cancer. More than 1,800 RDKit and Mordred descriptors were reduced through LASSO selection. Six classifiers were tuned using GridSearchCV and four-fold cross-validation. Random Forest reached 93% accuracy and tuned Gradient Boosting reached 98.28%. SHAP force and waterfall plots explained activity-driving descriptors.
