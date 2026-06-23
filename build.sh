#!/usr/bin/env bash
# ── Render build script ──
# Run automatically by Render on every deploy.
set -o errexit

echo "→ Installing Python dependencies…"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "→ Collecting static files…"
python manage.py collectstatic --no-input

echo "→ Running database migrations…"
python manage.py migrate --no-input

echo "→ Creating default categories (if needed)…"
python manage.py shell -c "
from apps.events.models import Category
defaults = [
  ('Music', '🎵'), ('Tech', '💻'), ('Food & Drinks', '🍜'),
  ('Arts', '🎨'), ('Sports', '⚽'), ('Business', '💼'),
  ('Fashion', '👗'), ('Comedy', '😂'), ('Film', '🎬'),
  ('Religious', '✝️'), ('Education', '📚'), ('Health', '🏥'),
]
for name, icon in defaults:
    Category.objects.get_or_create(name=name, defaults={'icon': icon})
print(f'Categories ready: {Category.objects.count()} total')
"

echo "✓ Build complete!"
