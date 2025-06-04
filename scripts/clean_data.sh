#!/bin/bash

echo "🧹 Cleaning data directories..."

# Remove all generated data files
rm -rf data/live/raw/*
rm -rf data/live/descriptions/*
rm -rf data/static/*

echo "✅ Data cleaned!"
echo "📁 Remaining structure:"
ls -la data/live/ 