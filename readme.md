# ChronoTech – Product Requirements Document (PRD)

## 1. Introduction
ChronoTech est une application web progressive (PWA) intelligente pour les techniciens terrain (CVC, électricité, plomberie, maintenance industrielle). Elle vise à remplacer la paperasse par une expérience fluide, mobile et intelligente, intégrée à SEI Web.

## 2. Problème à résoudre
- Perte de données clés
- Retards de facturation
- Erreurs fréquentes
- Frustration des techniciens et des clients

## 3. Objectifs & KPIs
- Réduction du temps de documentation de 60 %
- Facturation accélérée de 50 %
- Qualité des données à 95 %
- Satisfaction technicien : +30 pts NPS

## 4. Personas
- **Marie** : Technicienne terrain, peu technophile, veut une interface simple et rapide
- **Luc** : Directeur d’exploitation, veut un suivi fluide et des alertes d’activité

## 5. Fonctionnalités clés
### F1. Journal d'intervention dynamique
- Démarrage/arrêt par bouton ou commande vocale
- Ajout d’étapes (bouton + ou voix)
- Horodatage automatique
- Lien avec SEI Web

### F2. Dictée vocale intelligente (IA)
- Transcription temps réel
- Compréhension sémantique (numéros de série, actions, diagnostics)
- Classement automatique : Diagnostic, Actions, Pièces, Recommandations

### F3. Capture photo/vidéo + annotation vocale
- Photos liées à chaque étape
- Description dictée liée à la photo
- Synchronisation avec intervention et inventaire

### F4. Mode hors-ligne robuste
- Fonctionne sans connexion (dictée, journal, pièces)
- Synchronisation automatique dès reconnexion
- Journalisation locale (SQLite) + MultiRESTServer SEI

### F5. Catalogue de pièces & inventaire camion
- Recherche vocale ou texte
- Déduction automatique du stock
- API SEI intégrée : /stock/camion, /pieces/scan

### F6. Génération de rapport + signature client
- Rapport PDF généré automatiquement
- Signature sur tablette ou téléphone
- Envoi automatique au client + SEI Web

## 6. Parcours utilisateur
1. Notification intervention
2. Démarrage intervention
3. Prise photo, dictée annotation
4. Remplacement pièce, dictée inventaire
5. Finalisation, génération rapport
6. Signature client
7. Synchronisation et facturation

## 7. Stack technologique
- **Backend** : Flask + REST API + SQLAlchemy
- **Base de données** : MySQL 8.0 + SQLite local (offline)
- **Frontend** : PWA HTML5, Bootstrap 5.3, SignaturePad.js
- **Dictée/IA** : Web Speech API + moteur IA Python (NLP)
- **Interopérabilité** : API REST compatible SEI Web

## 8. Sécurité & Permissions
- Authentification technicien par QR ou 2FA
- Chiffrement des rapports et signatures
- Journalisation complète (intervention_id, auteur, temps, GPS)

## 9. Vision à long terme
- Maintenance prédictive (données + IA SEI)
- Assistance en réalité augmentée
- Génération automatique de tâches récurrentes
- Intégration continue avec QuickBooks / Stripe / SEI Web

## 10. Exigences non-fonctionnelles
- Performance : lancement < 3s, transcription quasi-temps réel
- Sécurité : données cryptées au repos et en transit
- Compatibilité : Chrome, Safari, Firefox, responsive mobile/tablette
- Fiabilité : uptime 99.9 %

---

## 11. Structure du projet
- `/app.py` : Application Flask principale
- `/models.py` : Modèles SQLAlchemy (Intervention, Étape, Pièce, Utilisateur)
- `/static/` : Fichiers statiques (JS, CSS, images)
- `/templates/` : Templates Jinja2 (HTML)
- `/requirements.txt` : Dépendances Python
- `/readme.md` : Documentation projet
- `/database.sql` : Schéma de la base MySQL
- `/offline.sqlite` : Base locale pour mode hors-ligne

## 12. Installation & lancement
```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l’application
python app.py
```

## 13. API REST principales
- `POST /login` : Authentification
- `GET /interventions` : Liste des interventions
- `POST /intervention` : Création intervention
- `POST /intervention/<id>/step` : Ajout étape
- `POST /intervention/<id>/photo` : Upload photo + annotation
- `POST /intervention/<id>/finish` : Clôture intervention + génération rapport
- `POST /intervention/<id>/sign` : Signature client
- `GET /pieces` : Catalogue pièces
- `POST /sync` : Synchronisation offline/online

## 14. Liens utiles
- [SEI Web API Documentation](https://seiweb.example.com/api)
- [Bootstrap 5.3](https://getbootstrap.com/)
- [SignaturePad.js](https://github.com/szimek/signature_pad)
- [Web Speech API](https://developer.mozilla.org/fr/docs/Web/API/Web_Speech_API)

---

## 15. Auteur & contact
- Projet ChronoTech – 2025
- Contact : techlead@chronotech.com