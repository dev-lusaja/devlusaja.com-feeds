-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS feeds_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE feeds_db;

-- Crear tabla de feeds
CREATE TABLE IF NOT EXISTS feeds (
    id VARCHAR(36) PRIMARY KEY,
    title TEXT,
    link VARCHAR(2048),
    pubDate VARCHAR(255),
    pubDate_parsed DATETIME GENERATED ALWAYS AS (
        STR_TO_DATE(SUBSTRING(pubDate, 1, 19), '%Y-%m-%dT%H:%i:%s')
    ) STORED,
    description TEXT,
    author LONGTEXT,
    sourceTitle VARCHAR(255),
    sourceUrl TEXT,
    sourceCategory VARCHAR(255),
    sourceType VARCHAR(50),
    sourceCountry VARCHAR(100),
    content LONGTEXT,
    image TEXT,
    isShortVideo TINYINT(1) DEFAULT 0,
    raw_data LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source_category (sourceCategory),
    INDEX idx_source_type (sourceType),
    INDEX idx_source_country (sourceCountry),
    INDEX idx_pub_date (pubDate),
    INDEX idx_pubDate_parsed (pubDate_parsed),
    INDEX idx_sourceType_pubDate (sourceType, pubDate_parsed),
    INDEX idx_created_at (created_at),
    UNIQUE INDEX idx_unique_link (link(767))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Crear tabla de ejecuciones
CREATE TABLE IF NOT EXISTS executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    execution_date DATE NOT NULL UNIQUE,
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feeds_processed INT DEFAULT 0,
    feeds_inserted INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed',
    INDEX idx_execution_date (execution_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;