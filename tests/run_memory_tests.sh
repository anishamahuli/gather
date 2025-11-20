#!/bin/bash
# Quick script to run memory tests

echo "🧪 Running Memory Tests..."
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run basic tests
echo "Running basic memory tests..."
python -m tests.test_memory_basic

echo ""
echo "✅ Test suite complete!"
echo ""
echo "To debug memory, run:"
echo "  python -m tests.debug_memory --all"
echo ""
echo "To view specific user's memory:"
echo "  python -m tests.debug_memory --user-id me --view-file"

