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
  `email_verified` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_account_username` (`username`),
  KEY `idx_account_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vote sites (top sites)
CREATE TABLE IF NOT EXISTS `vote_sites` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `url` VARCHAR(500) NOT NULL,
  `cooldown_minutes` INT UNSIGNED NOT NULL DEFAULT 720, -- 12h por defecto
  `points_reward` INT UNSIGNED NOT NULL DEFAULT 1,
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `position` INT NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_vote_sites_enabled` (`is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vote logs (when a user triggers a vote claim)
CREATE TABLE IF NOT EXISTS `vote_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(32) NOT NULL,
  `site_id` INT UNSIGNED NOT NULL,
  `claimed_points` INT UNSIGNED NOT NULL DEFAULT 0,
  `next_available_at` DATETIME NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_vote_logs_user_site` (`username`, `site_id`),
  KEY `idx_vote_logs_next` (`next_available_at`),
  CONSTRAINT `fk_vote_logs_site` FOREIGN KEY (`site_id`) REFERENCES `vote_sites`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
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
  KEY `idx_news_comments_created_at` (`created_at`),
  KEY `idx_news_comments_author` (`author_username`),
  CONSTRAINT `fk_news_comments_news` FOREIGN KEY (`news_id`) REFERENCES `news`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Forum categories
CREATE TABLE IF NOT EXISTS `forum_categories` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `slug` VARCHAR(140) NOT NULL,
  `description` TEXT NULL,
  `position` INT NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_forum_categories_slug` (`slug`),
  KEY `idx_forum_categories_position` (`position`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Forum topics
CREATE TABLE IF NOT EXISTS `forum_topics` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `category_id` INT UNSIGNED NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `author_username` VARCHAR(32) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `last_post_at` TIMESTAMP NULL DEFAULT NULL,
  `posts_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `is_locked` TINYINT(1) NOT NULL DEFAULT 0,
  `is_pinned` TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_forum_topics_category` (`category_id`),
  KEY `idx_forum_topics_last_post_at` (`last_post_at`),
  KEY `idx_forum_topics_pinned` (`is_pinned`),
  CONSTRAINT `fk_forum_topics_category` FOREIGN KEY (`category_id`) REFERENCES `forum_categories`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Forum posts
CREATE TABLE IF NOT EXISTS `forum_posts` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `topic_id` INT UNSIGNED NOT NULL,
  `author_username` VARCHAR(32) NOT NULL,
  `content` MEDIUMTEXT NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_forum_posts_topic` (`topic_id`),
  KEY `idx_forum_posts_author` (`author_username`),
  CONSTRAINT `fk_forum_posts_topic` FOREIGN KEY (`topic_id`) REFERENCES `forum_topics`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Password reset tokens (OTP) for account recovery
CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(32) NOT NULL,
  `token` VARCHAR(64) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `consumed` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_prt_username` (`username`),
  KEY `idx_prt_token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Email verification tokens
CREATE TABLE IF NOT EXISTS `email_verification_tokens` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(32) NOT NULL,
  `token` VARCHAR(64) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `consumed` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_evt_username` (`username`),
  KEY `idx_evt_token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shop categories
CREATE TABLE IF NOT EXISTS `shop_categories` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `slug` VARCHAR(140) NOT NULL,
  `description` TEXT NULL,
  `position` INT NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_shop_categories_slug` (`slug`),
  KEY `idx_shop_categories_position` (`position`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shop items
CREATE TABLE IF NOT EXISTS `shop_items` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `category_id` INT UNSIGNED NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `description` TEXT NULL,
  `icon` VARCHAR(120) NULL,
  `world_item_entry` INT UNSIGNED NOT NULL,
  `realm_id` INT UNSIGNED NULL, -- null => usable en todos los realms
  `price_vote_points` INT UNSIGNED NOT NULL DEFAULT 0,
  `price_credits` INT UNSIGNED NOT NULL DEFAULT 0,
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `limit_per_account` INT UNSIGNED NULL, -- null => sin límite
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_shop_items_category` (`category_id`),
  KEY `idx_shop_items_realm` (`realm_id`),
  KEY `idx_shop_items_enabled` (`is_enabled`),
  CONSTRAINT `fk_shop_items_category` FOREIGN KEY (`category_id`) REFERENCES `shop_categories`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shop purchases log
CREATE TABLE IF NOT EXISTS `shop_purchases` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(32) NOT NULL,
  `item_id` INT UNSIGNED NULL, -- legado (para compras simples); ahora se usa tabla shop_purchase_items
  `realm_id` INT UNSIGNED NULL,
  `character_guid` BIGINT UNSIGNED NULL,
  `character_name` VARCHAR(24) NULL,
  `cost_vote_points` INT UNSIGNED NOT NULL DEFAULT 0,
  `cost_credits` INT UNSIGNED NOT NULL DEFAULT 0,
  `sent_via_soap` TINYINT(1) NOT NULL DEFAULT 0,
  `soap_response` TEXT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_shop_purchases_user` (`username`),
  KEY `idx_shop_purchases_item` (`item_id`),
  KEY `idx_shop_purchases_realm` (`realm_id`),
  KEY `idx_shop_purchases_char_guid` (`character_guid`),
  CONSTRAINT `fk_shop_purchases_item` FOREIGN KEY (`item_id`) REFERENCES `shop_items`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Items individuales dentro de una compra (soporte multi-item / multi-stack)
CREATE TABLE IF NOT EXISTS `shop_purchase_items` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `purchase_id` BIGINT UNSIGNED NOT NULL,
  `shop_item_id` INT UNSIGNED NOT NULL,
  `world_item_entry` INT UNSIGNED NOT NULL,
  `quantity` INT UNSIGNED NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_purchase_items_purchase` (`purchase_id`),
  KEY `idx_purchase_items_shop_item` (`shop_item_id`),
  CONSTRAINT `fk_purchase_items_purchase` FOREIGN KEY (`purchase_id`) REFERENCES `shop_purchases`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_purchase_items_shop_item` FOREIGN KEY (`shop_item_id`) REFERENCES `shop_items`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Notes:
-- 1) `session` is BINARY(40) to store the 40-byte session_key used by web sessions.
-- 2) `role` gestiona permisos básicos: 0=guest (no se usa en DB), 1=logged (por defecto), 2=admin.
-- 3) Credentials stored in `char_db_password` should be protected; in production use a secrets manager
--    or encrypt the column and restrict DB user permissions.
