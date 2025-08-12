# PRD — Intervention (ChronoTech)

## Objectif
Permettre aux techniciens de gérer les interventions terrain étape par étape, avec association de produits, suivi chronométré, notes vocales, et expérience utilisateur moderne.

## Utilisateurs cibles
- Techniciens
- Administrateurs
- Clients (consultation)

## Fonctionnalités principales
1. **Création d’une intervention**
   - Saisie client, adresse, technicien, statut
   - Affectation d’un technicien
2. **Gestion des étapes**
   - Ajout, modification, suppression d’étapes
   - Description, date, chronométrage
   - Association d’un produit (table BDM.inprix)
   - Quantité, prix (à venir)
3. **Sélecteur de produit avancé**
   - Recherche dynamique (nom/code)
   - Pagination, filtres
   - Sélection intuitive
4. **Suivi chronométré**
   - Démarrage/arrêt du chrono par étape
   - Calcul automatique de la durée
5. **Notes vocales**
   - Enregistrement et transcription (JS, à venir)
6. **Gestion des techniciens**
   - CRUD techniciens (admin)
7. **Authentification**
   - Login, logout, hash mot de passe
8. **Expérience utilisateur moderne**
   - UI responsive (Tailwind/Bootstrap)
   - Feedback visuel, confirmation
   - Navigation fluide
9. **Offline & API REST (à venir)**
   - Synchronisation locale
   - Endpoints API pour mobile
10. **Gestion des erreurs**
    - Affichage des erreurs backend
    - Gestion absence table inprix

## Données principales
- Intervention
  - id, client, adresse, statut, technicien, début, fin
- Étape
  - id, intervention_id, description, timestamp, product_id, durée, note vocale
- Produit (BDM.inprix)
  - CODEAP, DESCR, prix, quantité
- Technicien
  - id, nom, email, rôle

## Parcours utilisateur
1. Login
2. Accès au dashboard
3. Création ou sélection d’une intervention
4. Ajout d’étapes avec produits
5. Suivi chronométré et notes
6. Validation et clôture

## Contraintes techniques
- Backend Python/Flask, MySQL
- Frontend HTML5, Tailwind, Bootstrap
- Table inprix dans BDM (accès direct)
- Sécurité (hash, permissions)

## Évolutions prévues
- Gestion des quantités/prix produits
- API REST mobile
- Offline
- Signature/photo
- Tests unitaires
- Documentation API

---
Ce document sert de PRD pour la gestion des interventions dans ChronoTech. Toute évolution doit être validée par l’équipe produit.
