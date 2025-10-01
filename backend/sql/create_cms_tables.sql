-- SQL schema for CMS tables used by FastWoW-CMS
-- Creates cms.account and cms.realms

CREATE DATABASE IF NOT EXISTS `cms` DEFAULT CHARACTER SET = 'utf8mb4' COLLATE = 'utf8mb4_unicode_ci';
USE `cms`;

-- Table to store web-related account info (credits, votes, web session, etc.)
CREATE TABLE IF NOT EXISTS `account` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(32) NOT NULL,
  `credits` INT UNSIGNED NOT NULL DEFAULT 0,
  `vote_points` INT UNSIGNED NOT NULL DEFAULT 0,
  `last_login` TIMESTAMP NULL DEFAULT NULL,
  `session` BINARY(40) DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_account_username` (`username`),
  KEY `idx_account_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table to register realms and the connection information for their characters DB
-- This allows CMS to connect to each realm's characters database to fetch online counts, races, etc.
CREATE TABLE IF NOT EXISTS `realms` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `realm_id` INT UNSIGNED NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `char_db_host` VARCHAR(255) NOT NULL,
  `char_db_port` INT UNSIGNED NOT NULL DEFAULT 3306,
  `char_db_user` VARCHAR(100) NOT NULL,
  `char_db_password` VARCHAR(255) NOT NULL,
  `char_db_name` VARCHAR(100) NOT NULL,
  `description` TEXT,
  -- SOAP connection details (for future use)
  `soap_enabled` TINYINT(1) NOT NULL DEFAULT 0,
  `soap_endpoint` VARCHAR(255) DEFAULT NULL,
  `soap_user` VARCHAR(100) DEFAULT NULL,
  `soap_password` VARCHAR(255) DEFAULT NULL,
  `soap_timeout` INT UNSIGNED NOT NULL DEFAULT 30,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_realms_realm_id` (`realm_id`),
  KEY `idx_realms_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Notes:
-- 1) `session` is BINARY(40) to store the 40-byte session_key used by web sessions.
-- 2) Credentials stored in `char_db_password` should be protected; in production use a secrets manager
--    or encrypt the column and restrict DB user permissions.
