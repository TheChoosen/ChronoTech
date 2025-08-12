PRD Fusionné : Module Interventions & Travaux (ChronoTech)
Version : 2.0

Date : Août 2025

Produit : SEI Web – Module Interventions

Auteur : Équipe Produit

1. Objectif Global
Problème à résoudre
Le suivi des travaux et des interventions sur le terrain (atelier, service mobile) est actuellement fragmenté, reposant sur des notes papier, des appels et des fichiers Excel. Cette dispersion entraîne une perte d'informations critiques (pièces, temps réel), une communication inefficace entre les équipes et avec le client, des retards de facturation et une maintenance préventive compromise.

Solution proposée
Développer un module SaaS intégré à SEI Web, nommé ChronoTech, conçu pour centraliser et optimiser l'ensemble du cycle de vie des interventions. Le module offrira :

Une centralisation des travaux à faire depuis toutes les sources.

Une interface moderne et responsive (Claymorphism) pour les superviseurs et les techniciens.

Des outils d'IA intégrés (transcription vocale, traduction trilingue, suggestions) pour minimiser la saisie manuelle et accélérer les opérations.

Une traçabilité complète pour améliorer la communication interne et la transparence client.

2. Personas et Parcours Utilisateurs
Personas Clés
Marie – Technicienne : A besoin d'un accès rapide à ses tâches du jour. Veut passer moins de temps sur la saisie administrative et plus sur les réparations. Privilégie une interface rapide, mobile et utilisable au clavier.

Luc – Superviseur : Doit avoir une vue d'ensemble du planning, assigner les tâches efficacement, suivre la progression en temps réel et être alerté des urgences.

Le Client : Souhaite suivre l'avancement des travaux sur son véhicule, comprendre les actions menées et être notifié des étapes clés.

Parcours Utilisateur Typique (Technicien)
Début de journée : Marie ouvre sa tablette et consulte la vue "Aujourd'hui" qui liste ses interventions priorisées.

Lancement d'une tâche : Elle sélectionne un travail et clique sur "Démarrer".

Capture d'informations : Elle dicte une note vocale ("Le roulement avant droit est bruyant, remplacement nécessaire"). La note est instantanément transcrite, corrigée et traduite. Elle prend une photo de la pièce défectueuse.

Ajout de pièces : Elle ajoute la nouvelle pièce utilisée depuis le catalogue intégré.

Clôture : Une fois le travail terminé, elle le marque comme "Complété". Une notification est automatiquement envoyée au superviseur et au client.

3. Sources des Travaux et Prérequis
Sources des travaux à faire
Demandes directes du client (via portail, formulaire, courriel).

Travaux suggérés par les plans d'entretien préventif.

Travaux archivés non terminés lors d'interventions précédentes.

Rendez-vous planifiés dans le calendrier.

Création manuelle par un superviseur.

Prérequis à la création d'entités
Client : Nom complet / raison sociale, contact principal (nom, téléphone, courriel), adresse.

Véhicule : Associé à un client, Année, Marque, Modèle, NIV (VIN).

Bon de travail : Client et véhicule associés, travaux à faire définis, technicien(s) assigné(s).

4. Fonctionnalités Clés (UI/UX et IA)
Interface et Expérience Utilisateur (Claymorphism)
Vue Technicien : Liste des travaux du jour avec filtres (priorité, statut).

Navigation Efficace : Bascule rapide entre la vue tableau et la vue carte (F2), recherche globale (F4), et navigation clavier pour changer les statuts et valider (F8, F9, Entrée).

Design Moderne : Effets visuels soignés (ripple effect, ombres progressives) et badges de statut clairs.

Accessibilité : Conforme aux standards (aria-label, focus visible) pour une utilisation avec des lecteurs d'écran.

Responsive & Offline : Interface optimisée pour mobile, tablette et ordinateur. Un mode déconnecté avec synchronisation automatique est prévu.

Intelligence Artificielle et Automatisation
Saisie Vocale : Transcription des notes audio en texte via OpenAI Whisper, avec correction orthographique automatique.

Traduction Multilingue : Traduction instantanée des notes en Français, Anglais et Espagnol via DeepL API.

Suggestions Contextuelles : L'IA proposera des actions pertinentes basées sur l'historique du véhicule (ex: pièces à prévoir, anomalies fréquentes).

Notifications Intelligentes : Des notifications push (via OneSignal/Firebase), courriels ou alertes portail informent les parties prenantes de l'avancement (travail commencé, en attente de pièce, terminé).

5. Architecture Technique et API
Entités SQL Principales
En complément des tables existantes (users, work_orders, etc.), deux nouvelles tables seront créées pour structurer les données d'intervention.

SQL

CREATE TABLE intervention_notes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  work_order_id INT NOT NULL,
  technician_id INT NOT NULL,
  note_type ENUM('public', 'private') NOT NULL DEFAULT 'private',
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE intervention_media (
  id INT AUTO_INCREMENT PRIMARY KEY,
  work_order_id INT NOT NULL,
  technician_id INT NOT NULL,
  media_type ENUM('photo', 'video', 'audio') NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  transcription TEXT NULL,
  translation_fr TEXT NULL,
  translation_en TEXT NULL,
  translation_es TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE
);
API REST Principales
Gestion des Bons de Travail

GET    /work_orders : Lister tous les bons de travail.

POST   /work_orders : Créer un nouveau bon de travail.

GET    /work_orders/:id/details : Récupérer les détails complets (travaux, notes, pièces, médias).

POST   /work_orders/:id/assign : Assigner un ou plusieurs techniciens.

Gestion des Interventions

POST   /work_orders/:id/note : Ajouter une note (publique ou privée).

POST   /work_orders/:id/media : Uploader un média (photo, vidéo, audio).

POST   /work_orders/:id/products/add : Ajouter un produit/pièce utilisé.

Services IA

POST   /media/:id/transcribe : Lancer la transcription d'un média audio.

POST   /media/:id/translate : Traduire le contenu textuel d'une note ou d'une transcription.

GET    /ai/suggestions : Obtenir des suggestions contextuelles pour un bon de travail.

6. Sécurité et Permissions
Un système de Rôles (RBAC) strict sera implémenté pour garantir la sécurité des données.

Technicien : Peut voir et modifier uniquement les interventions qui lui sont assignées.

Superviseur (Manager) : Accès complet à la création, assignation et validation des travaux.

Client / Autre : Lecture seule des informations publiques (notes publiques, statut, photos partagées) via le portail client.

Admin : Accès complet, incluant la suppression.

Toutes les actions (création, modification, suppression) seront journalisées. Une authentification à deux facteurs (2FA) sera obligatoire pour les superviseurs et admins. Les protections standards (CSRF, XSS, requêtes préparées) seront appliquées.

7. Indicateurs de Succès (KPI)
Efficacité : Temps moyen de saisie d'une intervention complet (notes, pièces, temps) inférieur à 5 minutes.

Adoption IA : 90% des notes vocales transcrites et traduites automatiquement avec succès.

Satisfaction Utilisateur : 80% de satisfaction des techniciens mesurée après le premier mois d'utilisation.

Qualité : Réduction de 30% des travaux incomplets ou des oublis signalés.

8. Roadmap
Mois 1-2 : Développement du CRUD de base pour les interventions et de l'interface Claymorphism responsive avec filtres.

Mois 3-4 : Intégration des API d'IA pour la transcription et la traduction.

Mois 5-6 : Lancement du portail client et déploiement des suggestions contextuelles de l'IA.

Mois 7 : Implémentation du mode offline avec synchronisation et de la vue calendrier (synchro Google/Outlook).

9. Améliorations Futures
Export PDF des bons de travail avec signatures numériques.

Création de templates pour les travaux récurrents.

Statistiques prédictives pour optimiser la maintenance préventive.

Géolocalisation des techniciens mobiles.