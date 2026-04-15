#!/bin/bash
# ============================================
# PostgreSQL Init Script - 03_seed_initial_data.sql
# ============================================
# Insere dados iniciais essenciais para o funcionamento do sistema

-- Inserir roles padrão (serão usados pelo Flask-Migrate depois)
-- Nota: Esta tabela será criada pelo SQLAlchemy, mas preparamos os dados aqui

-- Configurações padrão do sistema (tabela será criada pelo ORM)
-- Este script serve como referência para dados iniciais

SELECT 'Seed data script executed - tables will be created by Flask-Migrate' AS status;
SELECT 'Run: flask db upgrade && flask init_roles && flask create_admin' AS next_steps;
