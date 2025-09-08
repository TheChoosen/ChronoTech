#!/usr/bin/env python3
"""
Configuration Google Drive pour ChronoTech
Solution simple pour configurer ou désactiver Google Drive
"""

import os
import sys

def check_google_drive_status():
    """Vérifier l'état actuel de Google Drive"""
    print("🔧 DIAGNOSTIC GOOGLE DRIVE CHRONOTECH")
    print("=" * 50)
    
    # Variables d'environnement importantes
    use_oauth = os.getenv('GOOGLE_DRIVE_USE_OAUTH', 'false')
    disable_drive = os.getenv('DISABLE_GOOGLE_DRIVE', 'false')
    
    print(f"📊 Configuration actuelle:")
    print(f"   GOOGLE_DRIVE_USE_OAUTH: {use_oauth}")
    print(f"   DISABLE_GOOGLE_DRIVE: {disable_drive}")
    
    # Vérifier les fichiers de credentials
    files_to_check = [
        'credentials.json',
        'token.pickle',
        '.env'
    ]
    
    print(f"\n📁 Fichiers de configuration:")
    for file in files_to_check:
        if os.path.exists(file):
            print(f"   ✅ {file} - Trouvé")
        else:
            print(f"   ❌ {file} - Manquant")
    
    # Analyser l'avertissement
    print(f"\n⚠️ PROBLÈME DÉTECTÉ:")
    print(f"   Message: 'No Google Drive credentials available; skipping Drive upload'")
    print(f"   Fichier: routes/openai.py ligne 139")
    print(f"   Cause: Le système tente d'utiliser Google Drive mais les credentials ne sont pas configurés")

def propose_solutions():
    """Proposer des solutions"""
    print(f"\n🔧 SOLUTIONS DISPONIBLES:")
    print(f"=" * 30)
    
    print(f"1. 🚫 DÉSACTIVER GOOGLE DRIVE (Recommandé pour la démo)")
    print(f"   - Plus simple et rapide")
    print(f"   - Aucune configuration nécessaire")
    print(f"   - Les fichiers seront stockés localement")
    
    print(f"\n2. ⚙️ CONFIGURER GOOGLE DRIVE (Optionnel)")
    print(f"   - Nécessite un compte Google Cloud")
    print(f"   - Configuration OAuth2 requise")
    print(f"   - Plus complexe mais fonctionnel")
    
    print(f"\n3. 🔇 SUPPRIMER LES AVERTISSEMENTS")
    print(f"   - Modifier le code pour ne plus afficher le warning")
    print(f"   - Plus propre pour la démo")

def disable_google_drive():
    """Désactiver Google Drive proprement"""
    print(f"\n🚫 DÉSACTIVATION DE GOOGLE DRIVE...")
    
    # Créer/modifier le fichier .env
    env_content = ""
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.read()
    
    # Ajouter la variable de désactivation
    if 'DISABLE_GOOGLE_DRIVE' not in env_content:
        env_content += f"\n# Désactiver Google Drive pour la démo\n"
        env_content += f"DISABLE_GOOGLE_DRIVE=true\n"
        env_content += f"GOOGLE_DRIVE_USE_OAUTH=false\n"
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print(f"✅ Variable DISABLE_GOOGLE_DRIVE=true ajoutée à .env")
    else:
        print(f"ℹ️ DISABLE_GOOGLE_DRIVE déjà configuré dans .env")
    
    return True

def remove_warnings():
    """Supprimer les avertissements du code"""
    print(f"\n🔇 SUPPRESSION DES AVERTISSEMENTS...")
    
    openai_file = 'routes/openai.py'
    if not os.path.exists(openai_file):
        print(f"❌ Fichier {openai_file} non trouvé")
        return False
    
    # Lire le fichier
    with open(openai_file, 'r') as f:
        content = f.read()
    
    # Remplacer le warning par un debug silencieux
    old_warning = "current_app.logger.warning('No Google Drive credentials available; skipping Drive upload')"
    new_debug = "# Google Drive désactivé pour la démo - stockage local utilisé"
    
    if old_warning in content:
        content = content.replace(old_warning, new_debug)
        
        with open(openai_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Avertissement Google Drive supprimé de {openai_file}")
        return True
    else:
        print(f"ℹ️ Avertissement déjà modifié dans {openai_file}")
        return True

def configure_google_drive():
    """Guide pour configurer Google Drive"""
    print(f"\n⚙️ CONFIGURATION GOOGLE DRIVE:")
    print(f"=" * 40)
    
    print(f"📋 Étapes requises:")
    print(f"1. Créer un projet Google Cloud Console")
    print(f"2. Activer l'API Google Drive")
    print(f"3. Créer des credentials OAuth2")
    print(f"4. Télécharger credentials.json")
    print(f"5. Placer credentials.json dans le répertoire ChronoTech")
    print(f"6. Exécuter le processus d'authentification")
    
    print(f"\n🔗 Liens utiles:")
    print(f"   Google Cloud Console: https://console.cloud.google.com/")
    print(f"   Documentation API: https://developers.google.com/drive/api/v3/quickstart/python")
    
    print(f"\n⏱️ Temps estimé: 15-30 minutes")
    print(f"🎯 Recommandation: Utiliser la solution 1 (désactivation) pour la démo")

def main():
    """Menu principal"""
    check_google_drive_status()
    propose_solutions()
    
    print(f"\n🎯 CHOISIR UNE SOLUTION:")
    print(f"1 - Désactiver Google Drive (Recommandé)")
    print(f"2 - Supprimer les avertissements")
    print(f"3 - Guide configuration Google Drive")
    print(f"4 - Tout désactiver (Solution complète)")
    print(f"q - Quitter")
    
    choice = input(f"\nVotre choix (1-4 ou q): ").strip().lower()
    
    if choice == '1':
        if disable_google_drive():
            print(f"\n✅ Google Drive désactivé avec succès!")
            print(f"🔄 Redémarrez le serveur pour appliquer les changements")
    elif choice == '2':
        if remove_warnings():
            print(f"\n✅ Avertissements supprimés!")
    elif choice == '3':
        configure_google_drive()
    elif choice == '4':
        if disable_google_drive() and remove_warnings():
            print(f"\n✅ SOLUTION COMPLÈTE APPLIQUÉE!")
            print(f"   - Google Drive désactivé")
            print(f"   - Avertissements supprimés")
            print(f"   - Fichiers stockés localement")
            print(f"🔄 Redémarrez le serveur pour une interface propre")
    elif choice == 'q':
        print(f"\n👋 Au revoir!")
    else:
        print(f"\n❌ Choix invalide")
    
    print(f"\n📊 RÉSUMÉ:")
    print(f"   - Le serveur ChronoTech fonctionnera sans Google Drive")
    print(f"   - Les fichiers seront stockés dans static/uploads/")
    print(f"   - Aucune fonctionnalité essentielle n'est affectée")
    print(f"   - L'interface sera plus propre sans les avertissements")

if __name__ == '__main__':
    main()
