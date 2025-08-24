-- Insertion de données de test pour Customer 360 Phase 3

-- Données de test pour customer_activities
INSERT IGNORE INTO customer_activities (customer_id, activity_type, title, description, actor_type, actor_name, metadata) VALUES
(1, 'note', 'Client créé', 'Nouveau client ajouté au système ChronoTech', 'system', 'ChronoTech System', '{"source": "system", "customer_type": "individual"}'),
(1, 'email', 'Email de bienvenue envoyé', 'Email automatique de bienvenue envoyé au nouveau client', 'system', 'ChronoTech System', '{"template": "welcome", "status": "sent"}'),
(2, 'note', 'Client créé', 'Nouveau client entreprise ajouté', 'system', 'ChronoTech System', '{"source": "system", "customer_type": "company"}'),
(3, 'call', 'Appel commercial', 'Premier contact téléphonique avec le prospect', 'user', 'Commercial Team', '{"duration": 15, "outcome": "interested"}');

-- Données de test pour customer_documents (structure existante)
INSERT IGNORE INTO customer_documents (customer_id, title, filename, file_path, file_size, mime_type, document_type, description) VALUES
(1, 'Contrat de service 2025', 'contract_001_2025.pdf', '/uploads/documents/customer_1/contract_001_2025.pdf', 245760, 'application/pdf', 'contract', 'Contrat de maintenance annuelle'),
(1, 'Photo véhicule avant intervention', 'vehicle_before_001.jpg', '/uploads/documents/customer_1/vehicle_before_001.jpg', 1024000, 'image/jpeg', 'photo', 'Photo du véhicule avant intervention'),
(2, 'Devis installation', 'quote_002_2025.pdf', '/uploads/documents/customer_2/quote_002_2025.pdf', 189440, 'application/pdf', 'quote', 'Devis pour installation système sécurité');

-- Données de test pour customer_analytics
INSERT IGNORE INTO customer_analytics (customer_id, metric_name, metric_value, metric_type, period_type, period_start, period_end, metadata) VALUES
(1, 'total_revenue', 2500.00, 'revenue', 'yearly', '2025-01-01', '2025-12-31', '{"currency": "EUR"}'),
(1, 'service_frequency', 4, 'frequency', 'yearly', '2025-01-01', '2025-12-31', '{"unit": "visits"}'),
(1, 'satisfaction_score', 4.5, 'satisfaction', 'quarterly', '2025-01-01', '2025-03-31', '{"scale": "1-5", "survey_id": "Q1_2025"}'),
(2, 'total_revenue', 15000.00, 'revenue', 'yearly', '2025-01-01', '2025-12-31', '{"currency": "EUR"}'),
(2, 'loyalty_score', 85, 'loyalty', 'monthly', '2025-01-01', '2025-01-31', '{"scale": "0-100"}');

-- Données de test pour customer_rfm_scores
INSERT IGNORE INTO customer_rfm_scores (customer_id, recency_score, frequency_score, monetary_score, rfm_segment, last_order_date, total_orders, total_revenue, avg_order_value, days_since_last_order, loyalty_tier) VALUES
(1, 4, 3, 3, 'Potential Loyalists', '2025-01-15', 3, 2500.00, 833.33, 8, 'silver'),
(2, 5, 4, 5, 'Champions', '2025-01-20', 8, 15000.00, 1875.00, 3, 'platinum'),
(3, 2, 1, 1, 'New Customer', NULL, 0, 0.00, 0.00, NULL, 'bronze');

-- Données de test pour customer_consents
INSERT IGNORE INTO customer_consents (customer_id, consent_type, is_granted, granted_at, source, legal_basis, purpose) VALUES
(1, 'data_processing', TRUE, '2025-01-10 10:00:00', 'registration', 'contract', 'Traitement des données dans le cadre de la relation contractuelle'),
(1, 'email_marketing', TRUE, '2025-01-10 10:00:00', 'registration', 'consent', 'Envoi d''informations commerciales par email'),
(1, 'sms_marketing', FALSE, NULL, 'registration', 'consent', 'Envoi d''informations commerciales par SMS'),
(2, 'data_processing', TRUE, '2025-01-12 14:30:00', 'registration', 'contract', 'Traitement des données dans le cadre de la relation contractuelle'),
(2, 'email_marketing', TRUE, '2025-01-12 14:30:00', 'registration', 'consent', 'Envoi d''informations commerciales par email'),
(3, 'data_processing', TRUE, '2025-01-15 09:15:00', 'registration', 'contract', 'Traitement des données dans le cadre de la relation contractuelle');

-- Données de test pour customer_communications
INSERT IGNORE INTO customer_communications (customer_id, communication_type, direction, subject, content, status, sender_name, recipient_contact, delivered_at) VALUES
(1, 'email', 'outbound', 'Bienvenue chez ChronoTech', 'Merci d''avoir choisi ChronoTech pour vos besoins de maintenance...', 'delivered', 'ChronoTech System', 'jean.dupont@email.com', '2025-01-10 10:05:00'),
(1, 'sms', 'outbound', 'Rappel RDV', 'Rappel: RDV demain 14h pour maintenance véhicule', 'delivered', 'ChronoTech System', '+33123456789', '2025-01-22 18:00:00'),
(2, 'email', 'outbound', 'Devis personnalisé', 'Voici votre devis personnalisé pour l''installation...', 'opened', 'Commercial Team', 'contact@entreprise-abc.com', '2025-01-12 15:00:00'),
(2, 'phone', 'inbound', 'Question technique', 'Appel du client pour question sur le devis', 'completed', 'Support Team', '+33987654321', '2025-01-18 10:30:00');

-- Données de test pour customer_preferences
INSERT IGNORE INTO customer_preferences (customer_id, preference_category, preference_key, preference_value, preference_type) VALUES
(1, 'communication', 'preferred_contact_method', 'email', 'string'),
(1, 'communication', 'contact_frequency', '2', 'number'),
(1, 'service', 'preferred_time_slot', 'afternoon', 'string'),
(1, 'service', 'reminder_days_before', '1', 'number'),
(2, 'communication', 'preferred_contact_method', 'phone', 'string'),
(2, 'billing', 'invoice_format', 'pdf', 'string'),
(2, 'service', 'preferred_technician', 'senior', 'string');

-- Vérification des données insérées
SELECT 'customer_activities' as table_name, COUNT(*) as count FROM customer_activities
UNION ALL
SELECT 'customer_documents', COUNT(*) FROM customer_documents
UNION ALL
SELECT 'customer_analytics', COUNT(*) FROM customer_analytics
UNION ALL
SELECT 'customer_rfm_scores', COUNT(*) FROM customer_rfm_scores
UNION ALL
SELECT 'customer_consents', COUNT(*) FROM customer_consents
UNION ALL
SELECT 'customer_communications', COUNT(*) FROM customer_communications
UNION ALL
SELECT 'customer_preferences', COUNT(*) FROM customer_preferences;
