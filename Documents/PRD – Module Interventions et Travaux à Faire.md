PRD – Module Interventions et Travaux à Faire
Version : 1.0
Date : Août 2025
Produit : SEI Web – Module Interventions
Auteur : [Ton nom / Équipe Produit]

1. Objectif global
Problème à résoudre :
Dans les opérations terrain (atelier, service mobile), le suivi des travaux à effectuer et des interventions est souvent éclaté (notes papier, appels, Excel). Les superviseurs perdent du temps à répartir les tâches, les techniciens saisissent les infos de façon incomplète, et le client n’a pas toujours une vision claire de l’avancement.
Cela entraîne :

Perte d’informations critiques (pièces utilisées, temps réels, observations terrain).

Mauvaise communication interne et avec le client.

Retards dans la facturation et l’entretien préventif.

Duplications ou oublis sur les interventions récurrentes.

Solution proposée :
Un module SaaS intégré à SEI Web qui :

Centralise les travaux à faire provenant de différentes sources (client, entretien préventif, archives, rendez-vous).

Permet aux superviseurs d’assigner plusieurs intervenants.

Offre aux techniciens une interface responsive, rapide et adaptée mobile/tablette.

Capture les données visibles client (commentaires, pièces, photos) et internes (notes privées, constats).

Intègre des outils d’IA et d’API (OpenAI, transcription vocale multilingue, traduction trilingue) pour optimiser la saisie.

2. Sources des travaux à faire
Demandes client (formulaires, appels, courriels intégrés).

Travaux suggérés par l’entretien préventif (règles automatiques).

Travaux archivés non terminés lors d’interventions passées.

Rendez-vous planifiés (mêmes prérequis qu’un bon de travail).

Création manuelle par le superviseur.

3. Prérequis
Pour créer un Client :
Nom complet / raison sociale

Contact principal (nom, téléphone, courriel)

Adresse complète

Pour créer un Véhicule propriétaire :
Associé à un client existant

Champs obligatoires : Année, Marque, Modèle, VIN

Pour créer un Bon de travail :
Client et véhicule associés

Travaux à faire définis

Technicien(s) assigné(s)

4. Entités SQL principales
En plus des tables existantes (users, work_orders, work_order_lines, etc.), on introduit :

sql
Copier
Modifier
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
5. API clés
POST /work_orders/:id/assign → Assigner un ou plusieurs techniciens

POST /work_orders/:id/note → Ajouter une note (publique ou privée)

POST /work_orders/:id/media → Upload de médias (photo/vidéo/audio)

GET /work_orders/:id/details → Récupérer l’ensemble des travaux, notes, pièces, temps

POST /media/:id/transcribe → Transcription et correction via OpenAI

POST /media/:id/translate → Traduction FR/EN/ES

6. Fonctionnalités UI/UX
Vue technicien : liste des interventions du jour, filtrage par priorité/statut.

Édition rapide : ajout de temps, pièces, notes vocales depuis mobile.

Synchro offline : mode déconnecté avec push en ligne.

IA intégrée :

Transcription vocale + correction orthographique.

Traduction trilingue automatique.

Suggestions contextuelles (pièces à prévoir, anomalies fréquentes).

Client portal :

Voir l’avancement, les photos, les commentaires publics.

Recevoir des notifications (travail commencé, terminé).

7. Innovations et API interconnectées
OpenAI Whisper : transcription audio rapide.

DeepL API : traduction automatique FR/EN/ES.

API pièces : connexion au catalogue pour ajout rapide.

API calendrier : synchro avec Google/Outlook pour rendez-vous.

Notifications push : via OneSignal ou Firebase.

8. Sécurité et permissions
RBAC :

Technicien : modifie uniquement ses interventions.

Superviseur : gère affectations, valide travaux.

Client : lecture seule des infos publiques.

Journalisation complète (qui modifie quoi et quand).

Authentification 2FA pour superviseurs.

9. Indicateurs de succès (KPI)
Temps moyen de saisie d’une intervention < 5 min.

90% des notes vocales transcrites et traduites automatiquement.

80% de satisfaction technicien après 1 mois.

Réduction de 30% des travaux incomplets ou oubliés.

10. Roadmap
M1-M2 : Module interventions de base + UI responsive.

M3-M4 : Intégration transcription + traduction.

M5-M6 : Portail client et IA contextuelle.

M7 : Synchro offline et optimisation UX mobile.

