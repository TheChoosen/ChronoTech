-- Données de test Customer 360 - Version simplifiée

-- Données pour customer_activities (nos nouvelles activités)
INSERT IGNORE INTO customer_activities (customer_id, activity_type, title, description, actor_type, actor_name, metadata) VALUES
(1, 'note', 'Client créé', 'Nouveau client ajouté au système ChronoTech', 'system', 'ChronoTech System', '{"source": "system", "customer_type": "individual"}'),
(1, 'email', 'Email de bienvenue', 'Email automatique de bienvenue envoyé', 'system', 'ChronoTech System', '{"template": "welcome", "status": "sent"}'),
(2, 'note', 'Client entreprise créé', 'Nouveau client entreprise ajouté', 'system', 'ChronoTech System', '{"source": "system", "customer_type": "company"}'),
(3, 'call', 'Premier contact', 'Premier contact téléphonique', 'user', 'Commercial Team', '{"duration": 15, "outcome": "interested"}');

-- Données pour customer_consents (structure adaptée)
INSERT IGNORE INTO customer_consents (customer_id, consent_type, purpose_description, legal_basis, is_active, consent_given_at, source) VALUES
(1, 'data_processing', 'Traitement des données contractuelles', 'contract', 1, '2025-01-10 10:00:00', 'website'),
(1, 'marketing_email', 'Envoi emails commerciaux', 'consent', 1, '2025-01-10 10:00:00', 'website'),
(2, 'data_processing', 'Traitement des données contractuelles', 'contract', 1, '2025-01-12 14:30:00', 'website'),
(2, 'marketing_email', 'Envoi emails commerciaux', 'consent', 1, '2025-01-12 14:30:00', 'website');

-- Données pour customer_communications (structure adaptée)
INSERT IGNORE INTO customer_communications (customer_id, communication_type, direction, channel, subject, content, status, recipient_address, delivered_at) VALUES
(1, 'email', 'outbound', 'system', 'Bienvenue chez ChronoTech', 'Email de bienvenue automatique', 'delivered', 'jean.dupont@email.com', '2025-01-10 10:05:00'),
(1, 'sms', 'outbound', 'system', 'Rappel RDV', 'Rappel rendez-vous demain', 'delivered', '+33123456789', '2025-01-22 18:00:00'),
(2, 'email', 'outbound', 'sales', 'Devis personnalisé', 'Votre devis sur mesure', 'opened', 'contact@entreprise-abc.com', '2025-01-12 15:00:00');

-- Données pour customer_preferences (nouvelles)
INSERT IGNORE INTO customer_preferences (customer_id, preference_category, preference_key, preference_value, preference_type) VALUES
(1, 'communication', 'preferred_contact_method', 'email', 'string'),
(1, 'communication', 'contact_frequency', '2', 'number'),
(1, 'service', 'preferred_time_slot', 'afternoon', 'string'),
(2, 'communication', 'preferred_contact_method', 'phone', 'string'),
(2, 'billing', 'invoice_format', 'pdf', 'string');

-- Données pour customer_rfm_scores (nouvelles)
INSERT IGNORE INTO customer_rfm_scores (customer_id, recency_score, frequency_score, monetary_score, rfm_segment, total_orders, total_revenue, avg_order_value, loyalty_tier) VALUES
(1, 4, 3, 3, 'Potential Loyalists', 3, 2500.00, 833.33, 'silver'),
(2, 5, 4, 5, 'Champions', 8, 15000.00, 1875.00, 'platinum'),
(3, 2, 1, 1, 'New Customer', 0, 0.00, 0.00, 'bronze');

-- Test des API - Insertion de quelques activités basées sur les work_orders existants
INSERT IGNORE INTO customer_activities (customer_id, activity_type, title, description, reference_id, reference_type, actor_type, actor_name, metadata)
SELECT 
    wo.customer_id,
    'workorder' as activity_type,
    CONCAT('Intervention: ', SUBSTRING(wo.description, 1, 50)) as title,
    CONCAT('Bon de travail #', wo.id, ' - ', wo.status) as description,
    wo.id as reference_id,
    'work_orders' as reference_type,
    'system' as actor_type,
    'ChronoTech System' as actor_name,
    JSON_OBJECT(
        'work_order_id', wo.id,
        'status', wo.status,
        'amount', COALESCE(wo.actual_cost, wo.estimated_cost, 0)
    ) as metadata
FROM work_orders wo
WHERE wo.customer_id IS NOT NULL 
AND wo.id NOT IN (SELECT DISTINCT COALESCE(reference_id, 0) FROM customer_activities WHERE reference_type = 'work_orders')
LIMIT 10;

-- Vérification finale
SELECT 'customer_activities' as table_name, COUNT(*) as count FROM customer_activities
UNION ALL
SELECT 'customer_consents', COUNT(*) FROM customer_consents
UNION ALL
SELECT 'customer_communications', COUNT(*) FROM customer_communications
UNION ALL
SELECT 'customer_preferences', COUNT(*) FROM customer_preferences
UNION ALL
SELECT 'customer_rfm_scores', COUNT(*) FROM customer_rfm_scores;
