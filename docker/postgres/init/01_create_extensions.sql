#!/bin/bash
# ============================================
# PostgreSQL Init Script - 01_create_extensions.sql
# ============================================
# Este script é executado automaticamente na primeira inicialização do PostgreSQL
# Cria extensões úteis para o banco de dados

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

-- Criar extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Configurações de performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = all;

SELECT 'Extensions created successfully!' AS status;
