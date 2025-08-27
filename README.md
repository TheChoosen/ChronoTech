# 🚀 ChronoTech - Système de Gestion d'Interventions

**Version 2.0** - Application Flask moderne pour la gestion des bons de travail et interventions techniques.

## 📋 Description

ChronoTech est une application web complète pour la gestion des interventions techniques, développée avec Flask et MySQL. Elle offre une interface moderne avec design Claymorphism pour la gestion des bons de travail, clients, techniciens et analytics.

## ✨ Fonctionnalités

- 🔐 **Authentification sécurisée** avec gestion des rôles
- 📋 **Gestion des bons de travail** complète
- 👥 **Gestion des clients** et techniciens
- 📊 **Tableaux de bord** personnalisés par rôle
- 🔧 **Suivi des interventions** en temps réel
- 📱 **Interface responsive** moderne
- 📁 **Gestion des documents** et médias
- 🔔 **Système de notifications**

## 🛠️ Technologies

- **Backend**: Flask 2.2.2, PyMySQL
- **Frontend**: HTML5, CSS3 (Claymorphism), JavaScript
- **Base de données**: MySQL 8.0+
- **Authentification**: Session-based avec sécurisation
- **Design**: Responsive avec thème Claymorphism

## 🚀 Installation Rapide

### Prérequis
- Python 3.8+
- MySQL 8.0+
- Git

### Installation
```bash
# Cloner le projet
git clone <votre-repo>
cd ChronoTech

# Lancement automatique
./start_chronotech.sh
```

Le script `start_chronotech.sh` configure automatiquement :
- ✅ Environnement virtuel Python
- ✅ Installation des dépendances
- ✅ Configuration de la base de données
- ✅ Variables d'environnement
- ✅ Démarrage du serveur

## ⚙️ Configuration

### Variables d'environnement (.env)
```bash
# Base de données
MYSQL_HOST=192.168.50.101
MYSQL_USER=gsicloud
MYSQL_PASSWORD=VotreMotDePasse
MYSQL_DB=bdm

# Serveur
PORT=5010
HOST=0.0.0.0

# Sécurité
SECRET_KEY=votre-cle-secrete
```

## 📁 Structure du Projet

```
ChronoTech/
├── app.py                    # Application Flask principale
├── config.py                 # Configuration
├── database.py               # Gestionnaire de base de données
├── models.py                 # Modèles de données
├── utils.py                  # Utilitaires
├── requirements.txt          # Dépendances Python
├── start_chronotech.sh       # Script de démarrage
├── .env                      # Variables d'environnement
├── routes/                   # Routes et endpoints
├── templates/                # Templates HTML
├── static/                   # Ressources statiques
├── uploads/                  # Fichiers uploadés
└── venv/                     # Environnement virtuel
```

## 🔧 Utilisation

### Démarrage du serveur
```bash
# Méthode recommandée
./start_chronotech.sh

# Ou manuellement
source venv/bin/activate
python app.py
```

### Accès à l'application
- **URL**: http://localhost:5010
- **Comptes par défaut** (après installation):
  - Admin: `admin@chronotech.fr` / `admin123`
  - Technicien: `tech@chronotech.fr` / `tech123`

## 📊 Modules Disponibles

| Module | Description | URL |
|--------|-------------|-----|
| Dashboard | Tableau de bord principal | `/dashboard` |
| Bons de travail | Gestion des interventions | `/work_orders` |
| Clients | Gestion de la clientèle | `/customers` |
| Techniciens | Gestion des équipes | `/technicians` |
| Analytics | Statistiques et rapports | `/analytics` |
| API | Endpoints REST | `/api` |

## 🔐 Sécurité

- ✅ Authentification par session sécurisée
- ✅ Protection CSRF
- ✅ Validation des données côté serveur
- ✅ Hashage sécurisé des mots de passe
- ✅ Protection des uploads de fichiers
- ✅ Logs d'audit des actions

## 🎨 Interface

ChronoTech utilise un design moderne **Claymorphism** avec :
- Interface responsive pour tous les écrans
- Thème sombre/clair adaptatif
- Animations fluides
- UX optimisée pour les techniciens

## 📝 Logs et Monitoring

Les logs sont disponibles dans :
- Console de développement
- Fichiers de logs (si configuré)
- Interface d'administration

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou problème :
- 📧 Email: support@chronotech.fr
- 📋 Issues: GitHub Issues
- 📖 Documentation: `/docs`

## 🗂️ Gestion des templates legacy Client 360

Des pages legacy (finances, documents, analytics, consents) ont été remplacées par l'interface unifiée Client 360.

Workflow d'archivage / suppression:
1. Marquage DEPRECATED dans chaque template (fait).
2. Archivage (déplacement + manifest) :
  ```bash
  python scripts/archive_legacy_templates.py --archive
  ```
3. Période de grâce contrôlée via variable d'env:
  ```bash
  export LEGACY_TEMPLATES_REMOVE_AFTER=2025-10-01
  ```
4. Vérification pré-suppression (manuelle):
  ```bash
  python scripts/pre_remove_legacy_templates.py --access-log server.log
  ```
5. Suppression effective une fois conditions remplies (hook git empêche une suppression prématurée).

Installation hook pre-commit:
```bash
chmod +x scripts/pre_remove_legacy_templates.py scripts/git_hook_precommit_legacy_cleanup.sh
ln -s ../../scripts/git_hook_precommit_legacy_cleanup.sh .git/hooks/pre-commit
```

Restauration (si nécessaire) depuis un manifest d'archive:
```bash
python scripts/archive_legacy_templates.py --restore archive/templates_legacy/<horodatage>/manifest.json
```


---
**ChronoTech v2.0** - Développé avec ❤️ pour optimiser la gestion des interventions techniques.
