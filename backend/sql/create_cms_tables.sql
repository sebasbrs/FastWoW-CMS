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
  `role` TINYINT NOT NULL DEFAULT 1, -- 0=guest(reservado),1=logged(player),2=admin
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
  `soap_uri` VARCHAR(5) DEFAULT NULL,
  `soap_user` VARCHAR(100) DEFAULT NULL,
  `soap_password` VARCHAR(255) DEFAULT NULL,
  `soap_timeout` INT UNSIGNED NOT NULL DEFAULT 30,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_realms_realm_id` (`realm_id`),
  KEY `idx_realms_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- News / articles table
CREATE TABLE IF NOT EXISTS `news` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(200) NOT NULL,
  `slug` VARCHAR(220) NOT NULL,
  `summary` VARCHAR(500) DEFAULT NULL,
  `content` MEDIUMTEXT NOT NULL,
  `realm_id` INT UNSIGNED DEFAULT NULL, -- null => global news
  `author_username` VARCHAR(32) NOT NULL,
  `is_published` TINYINT(1) NOT NULL DEFAULT 0,
  `published_at` DATETIME NULL DEFAULT NULL,
  `priority` INT NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_news_slug` (`slug`),
  KEY `idx_news_published_at` (`published_at`),
  KEY `idx_news_realm_id` (`realm_id`),
  CONSTRAINT `fk_news_realm_id` FOREIGN KEY (`realm_id`) REFERENCES `realms`(`realm_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comments for news
CREATE TABLE IF NOT EXISTS `news_comments` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `news_id` INT UNSIGNED NOT NULL,
  `author_username` VARCHAR(32) NOT NULL,
  `content` TEXT NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_news_comments_news_id` (`news_id`),
  KEY `idx_news_comments_author` (`author_username`),
  CONSTRAINT `fk_news_comments_news` FOREIGN KEY (`news_id`) REFERENCES `news`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comments for news
CREATE TABLE IF NOT EXISTS `news_comments` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `news_id` INT UNSIGNED NOT NULL,
  `author_username` VARCHAR(32) NOT NULL,
  `content` TEXT NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_news_comments_news_id` (`news_id`),
  KEY `idx_news_comments_created_at` (`created_at`),
  CONSTRAINT `fk_news_comments_news` FOREIGN KEY (`news_id`) REFERENCES `news`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Notes:
-- 1) `session` is BINARY(40) to store the 40-byte session_key used by web sessions.
-- 2) `role` gestiona permisos básicos: 0=guest (no se usa en DB), 1=logged (por defecto), 2=admin.
-- 3) Credentials stored in `char_db_password` should be protected; in production use a secrets manager
--    or encrypt the column and restrict DB user permissions.
