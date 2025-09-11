#!/usr/bin/env python3
"""
Script pour afficher les informations de connexion correctes
"""

print("=== CHRONOTECH - INFORMATIONS DE CONNEXION ===")
print()
print("✅ Application principale (avec toutes les fonctionnalités) :")
print("   URL: http://localhost:5011")
print("   - Dashboard: http://localhost:5011/dashboard")
print("   - Interventions: http://localhost:5011/interventions/")
print("   - Vue Kanban: http://localhost:5011/interventions/kanban")
print()
print("❌ Application obsolète (port 5020) :")
print("   URL: http://127.0.0.1:5020")
print("   - Cette version n'a pas toutes les fonctionnalités récentes")
print("   - L'endpoint kanban_view n'existe pas dans cette version")
print()
print("🔧 Solution :")
print("   Utilisez toujours le port 5011 pour accéder à ChronoTech")
print("   Les modals Kanban du dashboard sont également disponibles !")
print()
