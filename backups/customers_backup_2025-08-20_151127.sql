/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.13-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: 192.168.50.101    Database: bdm
-- ------------------------------------------------------
-- Server version	8.0.23

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `customers`
--

DROP TABLE IF EXISTS `customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `customers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `company` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mobile` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address` text COLLATE utf8mb4_unicode_ci,
  `postal_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `country` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT 'France',
  `vehicle_info` text COLLATE utf8mb4_unicode_ci COMMENT 'Informations sur les véhicules du client',
  `maintenance_history` text COLLATE utf8mb4_unicode_ci COMMENT 'Historique de maintenance',
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `siret` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `billing_address` text COLLATE utf8mb4_unicode_ci,
  `payment_terms` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tax_number` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preferred_contact_method` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `zone` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_type` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `email` (`email`),
  KEY `phone` (`phone`),
  KEY `company` (`company`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `customers`
--

LOCK TABLES `customers` WRITE;
/*!40000 ALTER TABLE `customers` DISABLE KEYS */;
INSERT INTO `customers` VALUES
(1,'Martin Dubois','Entreprise ABC','martin.dubois@abc.fr','0123456789',NULL,'123 Rue de la Paix','75001','Paris','France','Véhicule utilitaire Renault Master 2020',NULL,NULL,'2025-08-13 13:45:11','2025-08-20 19:01:34',1,NULL,'actif',NULL,'30j',NULL,'email',NULL,NULL),
(2,'Sophie Laurent','Société XYZ','sophie.laurent@xyz.fr','0987654321',NULL,'456 Avenue des Champs','69002','Lyon','France','Camion Iveco Daily 2019',NULL,NULL,'2025-08-13 13:45:11','2025-08-20 18:23:02',1,NULL,'actif',NULL,NULL,NULL,NULL,NULL,NULL),
(3,'Pierre Moreau','SARL Tech Plus','pierre.moreau@techplus.fr','0555123456',NULL,'789 Boulevard Tech','13001','Marseille','France','Fourgon Peugeot Boxer 2021',NULL,NULL,'2025-08-13 13:45:11','2025-08-20 18:23:02',1,NULL,'actif',NULL,NULL,NULL,NULL,NULL,NULL),
(4,'Solution Entreprise Informatique','','info@groupesei.com','',NULL,'','','','France',NULL,NULL,'','2025-08-14 19:07:40','2025-08-14 19:07:40',1,'','actif','','30j','','email','',NULL),
(5,'Adam Menard','','seiadammenard@gmail.com','',NULL,'','','','France',NULL,NULL,'','2025-08-14 19:08:06','2025-08-20 18:24:25',0,'','actif','','30j','','email','',NULL);
/*!40000 ALTER TABLE `customers` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-08-20 15:11:28
