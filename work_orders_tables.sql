-- Tables pour les travaux demandés (Work Orders)
CREATE TABLE IF NOT EXISTS `work_orders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `claim_number` varchar(50) NOT NULL UNIQUE,
  `customer_name` varchar(255) NOT NULL,
  `customer_address` text NOT NULL,
  `customer_phone` varchar(20) DEFAULT NULL,
  `customer_email` varchar(255) DEFAULT NULL,
  `description` text NOT NULL,
  `priority` enum('low', 'medium', 'high', 'urgent') NOT NULL DEFAULT 'medium',
  `status` enum('draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled') NOT NULL DEFAULT 'draft',
  `assigned_technician_id` int(11) DEFAULT NULL,
  `created_by_user_id` int(11) NOT NULL,
  `estimated_duration` int(11) DEFAULT NULL COMMENT 'Durée estimée en minutes',
  `estimated_cost` decimal(10,2) DEFAULT NULL,
  `actual_duration` int(11) DEFAULT NULL COMMENT 'Durée réelle en minutes',
  `actual_cost` decimal(10,2) DEFAULT NULL,
  `scheduled_date` datetime DEFAULT NULL,
  `completion_date` datetime DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `assigned_technician_id` (`assigned_technician_id`),
  KEY `created_by_user_id` (`created_by_user_id`),
  KEY `status` (`status`),
  KEY `priority` (`priority`),
  KEY `scheduled_date` (`scheduled_date`),
  CONSTRAINT `work_orders_ibfk_1` FOREIGN KEY (`assigned_technician_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `work_orders_ibfk_2` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table pour les produits/matériaux liés aux travaux
CREATE TABLE IF NOT EXISTS `work_order_products` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `work_order_id` int(11) NOT NULL,
  `product_name` varchar(255) NOT NULL,
  `product_reference` varchar(100) DEFAULT NULL,
  `quantity` decimal(10,2) NOT NULL DEFAULT 1.00,
  `unit_price` decimal(10,2) DEFAULT NULL,
  `total_price` decimal(10,2) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `work_order_id` (`work_order_id`),
  CONSTRAINT `work_order_products_ibfk_1` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table pour l'historique des changements de statut
CREATE TABLE IF NOT EXISTS `work_order_status_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `work_order_id` int(11) NOT NULL,
  `old_status` varchar(50) DEFAULT NULL,
  `new_status` varchar(50) NOT NULL,
  `changed_by_user_id` int(11) NOT NULL,
  `change_reason` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `work_order_id` (`work_order_id`),
  KEY `changed_by_user_id` (`changed_by_user_id`),
  CONSTRAINT `work_order_status_history_ibfk_1` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`) ON DELETE CASCADE,
  CONSTRAINT `work_order_status_history_ibfk_2` FOREIGN KEY (`changed_by_user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
