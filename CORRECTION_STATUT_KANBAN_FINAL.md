# CORRECTION DE L'ERREUR DE CHANGEMENT DE STATUT - CHRONOTECH

## 🔍 Problème Identifié

L'erreur lors du changement de statut des bons de travail provenait d'un **décalage entre les noms de colonnes** de la table `kanban_history` et ceux utilisés dans l'API.

### ❌ Erreur trouvée

L'API essayait d'insérer dans la table `kanban_history` avec des noms de colonnes incorrects :

```sql
-- ❌ Code erroné dans routes/api.py
INSERT INTO kanban_history (work_order_id, previous_status, new_status, 
                          changed_by_user_id, changed_at, notes)
```

Mais la vraie structure de la table est :

```sql
-- ✅ Structure réelle dans corrections_chronochat_db.sql
CREATE TABLE IF NOT EXISTS kanban_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,           -- ← task_id, pas work_order_id
    old_status VARCHAR(50),         -- ← old_status, pas previous_status  
    new_status VARCHAR(50) NOT NULL,
    moved_by INT,                   -- ← moved_by, pas changed_by_user_id
    move_reason TEXT,               -- ← move_reason, pas notes
    moved_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- ← Auto-généré
    duration_in_status INT,
    ...
);
```

## ✅ Corrections Appliquées

### 1. Correction API - Mise à jour de statut

**Fichier** : `/routes/api.py` - Ligne ~408

```python
# ✅ CORRIGÉ
history_query = """
    INSERT INTO kanban_history (task_id, old_status, new_status, 
                              moved_by, move_reason)
    VALUES (%s, %s, %s, %s, %s)
"""

cursor.execute(history_query, (
    work_order_id, old_status, new_status, 
    user_id, f"Statut changé de {old_status} à {new_status}"
))
```

### 2. Correction API - Assignment des techniciens  

**Fichier** : `/routes/api.py` - Ligne ~479

```python
# ✅ CORRIGÉ
cursor.execute("""
    INSERT INTO kanban_history (task_id, old_status, new_status, 
                              moved_by, move_reason)
    VALUES (%s, %s, %s, %s, %s)
""", (work_order_id, 'assignment_change', 'assignment_change', 
      user_id, notes))
```

### 3. Amélioration gestion d'erreurs

```python
# ✅ AJOUTÉ
except Exception as e:
    log_error(f"Erreur mise à jour statut work order {work_order_id}: {e}")
    
    import traceback
    log_error(f"Traceback: {traceback.format_exc()}")
    
    # Message d'erreur spécifique
    error_msg = str(e)
    if "kanban_history" in error_msg:
        error_msg = "Erreur lors de l'enregistrement dans l'historique"
    elif "work_orders" in error_msg:
        error_msg = "Erreur lors de la mise à jour du bon de travail"
    else:
        error_msg = "Erreur interne du serveur"
        
    return jsonify({
        'error': error_msg,
        'debug_info': str(e)
    }), 500
```

## 🧪 Test de Validation

Pour tester si la correction fonctionne :

### 1. Test via Dashboard

1. Ouvrir le dashboard : `http://127.0.0.1:5011/dashboard`
2. Faire glisser une carte d'une colonne à l'autre
3. Vérifier dans la console du navigateur (F12) :
   - ✅ Message : `✅ Statut sauvegardé: WO-{id} -> {nouveau_statut}`
   - ❌ Si erreur : `❌ Erreur sauvegarde WO-{id}: [détails]`

### 2. Test via API directe

```bash
# Récupérer un work order existant
curl "http://127.0.0.1:5011/api/work-orders" | head -5

# Tester le changement de statut (remplacer {ID} par un vrai ID)
curl -X PUT "http://127.0.0.1:5011/api/work-orders/{ID}/status" \
     -H "Content-Type: application/json" \
     -d '{"status": "in_progress"}' \
     -w "Status: %{http_code}\n"
```

### 3. Vérification en base de données

```sql
-- Vérifier que l'historique est bien enregistré
SELECT * FROM kanban_history 
ORDER BY moved_at DESC 
LIMIT 5;

-- Vérifier les statuts des work orders
SELECT id, claim_number, status, updated_at 
FROM work_orders 
WHERE status IN ('in_progress', 'completed') 
ORDER BY updated_at DESC 
LIMIT 5;
```

## 🔧 Fonctions JavaScript du Dashboard

Les fonctions côté client qui gèrent le drag & drop :

```javascript
// ✅ Ces fonctions sont déjà présentes et correctes dans le dashboard

function handleWorkOrderDrop(e) {
    // Gère le drop des cartes Kanban
    // Appelle moveWorkOrderToModalStatus()
}

function moveWorkOrderToModalStatus(cardId, fromStatus, toStatus) {
    // Déplace visuellement la carte
    // Appelle saveWorkOrderStatusChange()
}

function saveWorkOrderStatusChange(cardId, newStatus) {
    // Appel API PUT /api/work-orders/{id}/status
    // Gestion des erreurs et feedback visuel
}
```

## 📊 Statuts Valides

L'API accepte ces statuts :

- `draft` - Brouillon
- `pending` - En attente  
- `assigned` - Assigné
- `in_progress` - En cours
- `completed` - Terminé
- `cancelled` - Annulé

## 🎯 Résultat Attendu

Après correction, le changement de statut doit :

1. ✅ Mettre à jour le statut dans `work_orders`
2. ✅ Enregistrer l'historique dans `kanban_history`
3. ✅ Retourner une réponse JSON de succès
4. ✅ Afficher un feedback visuel positif dans le dashboard
5. ✅ Mettre à jour les compteurs des colonnes Kanban

## 🚨 Problèmes Potentiels Restants

1. **Serveur instable** : Le serveur de développement Flask peut être instable
2. **Table manquante** : Vérifier que `kanban_history` existe en base
3. **Permissions** : Vérifier les permissions MySQL
4. **Session utilisateur** : S'assurer que `session.get('user_id')` retourne une valeur valide

---

**Status** : ✅ Correction appliquée - Test requis pour validation finale
