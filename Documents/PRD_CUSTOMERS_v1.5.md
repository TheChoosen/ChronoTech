# PRD — CUSTOMERS (v1.5)

Résumé rapide
- Objectif: centraliser et gérer les clients (individuels, entreprises, gouvernements) avec suivi CRM fluide, tolérance du schéma et filtres réactifs.

Checklist (éléments couverts dans ce document)
- Filtrage réactif (AJAX) + statistiques exactes (COUNT(*) côté DB)
- Persistance et normalisation de `customer_type`
- Tolérance aux colonnes optionnelles absentes
- `is_active` vs `status` : sémantique distincte
- Migration idempotente pour `customer_type`
- Tests automatisés minimaux et critères DoD
- RBAC, personas et KPI

## 1.5 — 📊 Tableau comparatif

| Dimension | Version actuelle (ton PRD) | Version enrichie v1.5 (proposée) | Valeur ajoutée |
|---|---:|---|---|
| Fonction principale | Absente (pas de phrase synthétique) | « Centraliser et gérer les clients (individuels, entreprises, gouvernements) avec suivi CRM fluide. » | Clarifie immédiatement l’objectif métier pour tout lecteur |
| Résultats concrets | Pas explicités | Réduction des doublons (-30%), temps d’ajout < 1 min, réactivation clients inactifs en 1 clic, temps de recherche < 5s | Donne des objectifs mesurables à l’équipe et priorise les optimisations |
| Synergies modules | Non listées | Lien direct avec Facturation, Location, Entretien, F&I, WorkOrders, Vehicles, Marketing | Montre l’importance transversale et aide le planning d’intégration |
| Personas / User Journeys | Pas spécifiques | Scénarios : Commercial, Superviseur, Technicien, Invité (avec cas d'usage) | Aide devs/designers à concevoir flows et écrans pertinents |
| KPI (succès produit) | Non définis | % complétion fiches, temps moyen ajout, taux détection doublons, latence recherche, taux réactivation | Permet mesurer adoption et qualité, prioriser features |
| RBAC (permissions) | Admin, supervisor, commercial | Admin, Superviseur, Commercial, Technicien, Invité (granularité CRUD/soft-delete/export) | Sécurité cohérente et compréhensible pour Ops/DSI |
| UX/UI | Filtres AJAX, icônes colorées | + Avatars/logos, badges Actif/Inactif, compteur véhicules/contrats, responsive, Glass/Clay tokens | Améliore clarté, engagement utilisateur et adoption mobile |
| IA & automatisation | Non prévu | Détection doublons (score), suggestions IA pour préfill, rappels automatiques | Ajoute intelligence métier et vitesse de traitement |
| Interopérabilité | Migration DB mentionnée | Connecteurs: QuickBooks, Airtable, WooCommerce, DealerTrack, Webhooks / MultiRESTServer | Facilite synchronisation compta/CRM/marketplace |
| Support & doc | Pas détaillés | FAQ intégrée, tutoriels pas à pas, chatbot interne, changelog migration | Réduit besoin de support manuel / accélère onboarding |
| Tests & critères DoD | Centrés sur AJAX/filter/migration | + Tests doublons, avatars, tolérance colonne absente, soft-delete, e2e edit/save | Couverture QA plus complète, moins de régressions |
| Roadmap | Hotfix + CRUD/filter | Phase 1: CRUD + filtre & migration; Phase 2: IA doublons + QuickBooks; Phase 3: Marketing IA & analytics | Clarifie étapes et priorités de livraison |

## Recommandations opérationnelles
1. Adopter v1.5 pour le prochain sprint planning et découper Phase 1 en 3 US testables (CRUD, filtres AJAX + stats, migration idempotente).
2. Transformer chaque ligne « Valeur ajoutée » en critères d’acceptation (DoD) chiffrés (p.ex. recherche <5s sur dataset X).
3. Ajouter 3 tests d’intégration immédiats :
   - edit/save (multipart + form) -> DB persists
   - filter + stats AJAX -> counts match COUNT(*)
   - migration idempotente -> no-op si déjà appliquée
4. Créer un guide de migration (backup, apply, rollback) et exécution sur staging avant prod.

## KPI & Mesures proposées (exemples)
- Taux de complétion des fiches clients >= 85% (dans 3 mois)
- Temps moyen pour ajouter un client < 60s (mesuré sur 100 actions)
- Réduction doublons détectés >= 30% après IA semi-automatique
- Latence recherche < 200ms (cache/index) ou <5s sans cache sur dataset production

## DoD (Phase 1 minimal)
- Filtrage AJAX fonctionnel (navigable, pagination) et stats cohérentes (COUNT(*)). ✅
- Add/Edit persiste `customer_type` quand la colonne existe. ✅
- Templates tolèrent l'absence de `customer_type` (no runtime errors). ✅
- Soft-delete (is_active = 0) disponible et testée.
- Tests automatisés ajoutés (unit/integ) pour les 3 flows ci‑dessus.

## Next steps & PR
- Ce fichier ajoute la section 1.5 du PRD `Documents/PRD_CUSTOMERS_v1.5.md`.
- Je crée la branche `prd/customers-v1.5`, commit et pousse la branche locale; ensuite ouvrez un PR depuis GitHub si le push distant a fonctionné.

---

*Fichier généré automatiquement par l'outil d'assistance — mettre à jour si vous souhaitez plus de détails ou transformer en page Confluence.*
