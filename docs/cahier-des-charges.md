# Cahier des Charges — P2DP

## Predictive DevSecOps Deployment and Protection

**Auteurs :** Mouadh Boukari, Rim Menzli, Yossri Hedhli  
**Encadrant :** Mme AMENI BEN KHALIFA  
**Établissement :** Université Tek-Up  
**Version :** v1.0  
**Date :** 20/02  
**Année universitaire :** 2025  

---

## 1. Contexte & Problématique

Les pipelines DevOps déploient vite, mais la sécurité reste souvent réactive (post-incident, post-audit).  
Les erreurs de configuration (IaC, Kubernetes, policies, exposition réseau) sont une cause fréquente d’exposition.

P2DP est une plateforme DevSecOps multi-couches visant à sécuriser l’infrastructure sur tout son cycle de vie :

- **Layer 1** : Déploiement automatisé (Infrastructure Deployment Engine)
- **Layer 2** : Détection de mauvaises configurations (Rule-Based Engine extensible)
- **Layer 3** : Prévision du risque (Risk Forecasting)
- **Layer 4** : Détection de menaces post-déploiement (Continuous Monitoring)

## 2. Objectifs du Projet

### 2.1 Objectif général

Passer d’une défense réactive à une protection proactive et prédictive, en intégrant sécurité, déploiement, analyse de risque et monitoring continu.

### 2.2 Objectifs spécifiques

- Uploader, valider, simuler puis déployer de l’IaC.
- Détecter les misconfigurations avant/après déploiement (scanners + policies custom).
- Générer un score de risque prédictif (0–100) et/ou une classe (Low/Medium/High).
- Monitorer l’environnement live et détecter des comportements anormaux.
- Fournir un dashboard clair (état, findings, score, alertes, recommandations).
- Assurer la traçabilité bout-en-bout via GitOps + OpenTelemetry.

## 3. Périmètre (Scope)

### 3.1 Inclus (In-scope)

- Exécution 100% open-source en Kubernetes local (k3d/kind).
- Gestion de projets/environnements (au moins 1 environnement type).
- Upload IaC (Terraform / Docker / Kubernetes manifests / Helm) + versioning basique.
- Validation statique + simulation (dry-run / plan).
- Déploiement reproductible via GitOps (Argo CD).
- Moteur de règles de misconfiguration :
  - Trivy / Checkov
  - OPA / Conftest
  - Option admission control : Gatekeeper ou Kyverno
- Risk scoring (heuristique en MVP, ML en extension).
- Monitoring/alerting runtime (Falco) + observabilité (Grafana).
- Traces distribuées OpenTelemetry (API + jobs) visualisées dans Jaeger.
- Dashboard global + export de rapport.

### 3.2 Exclu (Out-of-scope MVP)

- Support multi-cloud complet simultané (AWS/Azure/GCP).
- SIEM complet/corrélation avancée à grande échelle.
- Remédiation automatique (auto-fix).

## 4. Parties prenantes & Utilisateurs

- **Équipe projet** : Dev, Sécu, Data.
- **Encadrant / Jury** : validation académique et technique.
- **Utilisateurs simulés** :
  - **Admin** : configure intégrations, règles/policies, accès, environnements.
  - **DevOps / Platform Engineer** : déploie, consulte état, corrige l’IaC, suit GitOps.
  - **Security Engineer (Viewer)** : lit rapports, alertes, risques, tendances.

## 5. Architecture Fonctionnelle (vue d’ensemble)

1. Upload IaC  
2. Validation & simulation  
3. Scan misconfiguration pré-déploiement  
4. Commit GitOps (état désiré)  
5. Argo CD Sync  
6. Scan misconfiguration post-déploiement  
7. Risk Forecast  
8. Monitoring & Threat Detection  
9. Traces/Logs/Metrics (OpenTelemetry)  
10. Dashboard & reporting

## 6. Exigences Fonctionnelles par couche

### 6.1 Layer 1 — Infrastructure Deployment Engine

- Upload templates (.tf, manifests K8s, Helm values, Dockerfile)
- Validation syntaxique + structure projet
- Simulation (Terraform plan / K8s dry-run)
- Déploiement GitOps (render, commit, sync Argo CD, rollback/historique)
- Monitoring d’état (Synced / OutOfSync / Failed / Drift suspected)
- Traçabilité par `deployment_id`

### 6.2 Layer 2 — Misconfiguration Detection

Moteurs MVP :

- Trivy
- Checkov
- OPA + Conftest

Catalogue de risques MVP :

- Exposition publique non nécessaire
- Chiffrement absent
- IAM/RBAC trop permissif
- Workloads dangereux (privileged/runAsRoot/hostPath/capabilities)
- Segmentation réseau manquante (NetworkPolicies)
- Logging/Audit insuffisant

### 6.3 Layer 3 — Risk Forecasting

Option MVP (heuristique) :

```text
Risk Score =
 (Exposure Weight × Internet Facing Resources)
+(Privilege Weight × RBAC Wildcards)
+(Workload Weight × Privileged Containers)
+(Segmentation Weight × No NetworkPolicies)
```

Sortie attendue :

- score 0–100
- facteurs explicatifs (top contributors)
- classe d’impact (Low/Medium/High)

Option extension : classification assistée ML (Random Forest / XGBoost).

### 6.4 Layer 4 — Threat Detection

Sources :

- logs applicatifs / conteneurs
- événements Kubernetes
- logs système
- alertes Falco

Patterns MVP :

- scan de ports anormal
- tentatives SSH excessives (brute-force)
- exécution de process suspects en conteneurs
- signal de mouvement latéral (heuristique)

## 7. Observabilité & Traçabilité (OpenTelemetry)

- Instrumentation FastAPI (requêtes, erreurs, latence)
- Instrumentation Celery (jobs scan/deploy/risk/report)
- Propagation `deployment_id` + `project_id`
- OTel Collector
- Visualisation Jaeger

## 8. Dashboard & UX

Vues principales :

- Login
- Projets/Environnements
- Deployment Dashboard
- Findings (L2)
- Risk Forecast (L3)
- Threat Alerts (L4)
- Traces (Jaeger)
- Observabilité (Grafana)

Exigences UX :

- vue synthèse (statut, score, alertes)
- filtres pertinents
- explication du risque + recommandations de correction
- statut GitOps Argo CD + historique + rollback

## 9. Modèle de Données (minimal)

Entités attendues :

- User
- Project
- Environment
- TemplateVersion
- DeploymentRun
- Artifact
- Finding
- RiskAssessment
- ThreatAlert

## 10. Stack Technique

- Frontend : React (Vite), TypeScript, MUI, Recharts
- Backend : FastAPI, Pydantic
- Jobs : Celery, Redis
- DB : PostgreSQL
- Artefacts : MinIO
- Runtime : Docker, Kubernetes local (k3d/kind), Helm
- CD : Argo CD
- CI : GitHub Actions
- Scan : Trivy, Checkov
- Policies : OPA/Conftest (+ Gatekeeper/Kyverno option)
- Threat detection : Falco
- Observabilité : OpenTelemetry, Jaeger, Prometheus, Loki, Grafana
- Log shipping : Fluent Bit

## 11. Livrables & Critères d’Acceptation

Validation du projet si l’utilisateur peut :

1. uploader un template,
2. obtenir une simulation,
3. recevoir findings L2,
4. obtenir un risk score justifié L3,
5. produire des alertes L4 via scénarios de test,
6. relier le flux avec traçabilité GitOps + traces OpenTelemetry.

Livrables :

- code source + README + cahier des charges,
- diagrammes d’architecture/flux,
- démo end-to-end.

## 12. Références (inspiration)

- Palo Alto Prisma Cloud
- Aqua Security
- Check Point CloudGuard

---

© 2026 Projet P2DP. Tous droits réservés.
