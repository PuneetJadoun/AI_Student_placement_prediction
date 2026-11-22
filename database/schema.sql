CREATE DATABASE IF NOT EXISTS student_ai_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_ai_db;

CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'student',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS students (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_students_email (email),
  CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS academic_records (
  record_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  previous_score FLOAT NOT NULL,
  math_score FLOAT NULL,
  reading_score FLOAT NULL,
  writing_score FLOAT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_academic_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS class_status (
  class_record_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  attendance FLOAT NOT NULL,
  study_hours FLOAT NOT NULL,
  sleep_hours FLOAT NOT NULL,
  internet_usage FLOAT NOT NULL,
  assignments_completed INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_class_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS student_background (
  background_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  gender VARCHAR(30) NULL,
  group_name VARCHAR(30) NULL,
  parental_education VARCHAR(120) NULL,
  extracurricular_activities BOOLEAN NULL,
  learning_disabilities BOOLEAN NULL,
  CONSTRAINT fk_background_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS placement_predictions (
  prediction_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  predicted_status VARCHAR(30) NOT NULL,
  placement_probability FLOAT NULL,
  model_version VARCHAR(80) NOT NULL,
  actual_placement_status VARCHAR(30) NULL,
  recommendations TEXT NULL,
  prediction_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_prediction_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);
