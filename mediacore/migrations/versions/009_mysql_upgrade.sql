-- Bring everything in sync with what websetup.py generates

ALTER TABLE `categories`
	MODIFY COLUMN `slug` VARCHAR(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	DROP INDEX `name`,
	ADD INDEX name USING BTREE(`name`);

ALTER TABLE `comments`
	MODIFY COLUMN `subject` VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL;

ALTER TABLE `media`
	MODIFY COLUMN `type` ENUM('video','audio') CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	MODIFY COLUMN `slug` VARCHAR(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	MODIFY COLUMN `title` VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;

ALTER TABLE `media_fulltext`
	MODIFY COLUMN `title` VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;

ALTER TABLE `media_files`
	MODIFY COLUMN `type` ENUM('video','audio','audio_desc','captions') CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	MODIFY COLUMN `container` VARCHAR(10) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	MODIFY COLUMN `url` VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL;

ALTER TABLE `podcasts`
	MODIFY COLUMN `slug` VARCHAR(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
	MODIFY COLUMN `itunes_url` VARCHAR(80) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
	MODIFY COLUMN `feedburner_url` VARCHAR(80) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL;

ALTER TABLE `tags`
	MODIFY COLUMN `slug` VARCHAR(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;
