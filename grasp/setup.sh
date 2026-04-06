#!/usr/bin/env bash
# GRASP setup for Europeana QLever endpoint
# Requires: grasp CLI (uv tool), QLever running on :7001
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GRASP_INDEX_DIR="${GRASP_INDEX_DIR:-$HOME/data/europeana/grasp-index}"

echo "=== GRASP Index Dir: $GRASP_INDEX_DIR ==="

# 1. Download entity and property label data
echo "--- Step 1: Downloading entity and property data ---"
grasp data europeana \
  --endpoint http://localhost:7001 \
  --entity-sparql "$SCRIPT_DIR/europeana-entity.sparql" \
  --property-sparql "$SCRIPT_DIR/europeana-property.sparql"

# 2. Build fuzzy search indices
echo "--- Step 2: Building fuzzy indices ---"
grasp index europeana \
  --entities-type fuzzy \
  --properties-type fuzzy

# 3. Place prefixes.json
echo "--- Step 3: Installing prefixes.json ---"
cp "$SCRIPT_DIR/prefixes.json" "$GRASP_INDEX_DIR/europeana/prefixes.json"

# 4. Place info queries
echo "--- Step 4: Installing info queries ---"
mkdir -p "$GRASP_INDEX_DIR/europeana/entities" "$GRASP_INDEX_DIR/europeana/properties"
cp "$SCRIPT_DIR/entities-info.sparql" "$GRASP_INDEX_DIR/europeana/entities/info.sparql"
cp "$SCRIPT_DIR/properties-info.sparql" "$GRASP_INDEX_DIR/europeana/properties/info.sparql"

# 5. Pre-cache entity/property info
echo "--- Step 5: Pre-caching info queries ---"
grasp cache europeana

echo "=== Setup complete ==="
echo ""
echo "Test with:"
echo "  grasp run $SCRIPT_DIR/europeana-grasp.yaml --input \"How many items are in the dataset?\""
echo ""
echo "Start server with:"
echo "  grasp serve $SCRIPT_DIR/europeana-grasp.yaml"
