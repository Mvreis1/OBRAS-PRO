#!/bin/bash
# ============================================
# PostgreSQL Post-Init Script
# ============================================
# Executado após todos os scripts de init
# Útil para verificações finais e configurações

set -e

echo "🚀 PostgreSQL initialization complete!"
echo "📊 Database: $POSTGRES_DB"
echo "👤 User: $POSTGRES_USER"
echo ""
echo "Next steps:"
echo "  1. Run Flask migrations: flask db upgrade"
echo "  2. Initialize roles: flask init_roles"
echo "  3. Create admin user: flask create_admin"
echo ""
echo "✅ PostgreSQL is ready!"
