"""
Test data loading and formatting without requiring API keys.
"""

import json
from pathlib import Path

from forge.ingestion.engine import DataFormatter, IngestionEngine
from forge.ingestion.models import (
    ArchitectureDataset,
    IncidentDataset,
    PostmortemDataset,
)


def test_load_incidents():
    """Test loading and validating incidents data."""
    data_path = Path("data/incidents.json")
    
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    dataset = IncidentDataset.model_validate(raw_data)
    
    print(f"✓ Loaded {len(dataset.incidents)} incidents")
    
    # Test formatting
    formatter = DataFormatter()
    first_incident = dataset.incidents[0].model_dump()
    formatted = formatter.format_incident(first_incident)
    
    print(f"✓ Formatted first incident ({len(formatted)} chars)")
    print(f"\nFirst 500 chars:\n{formatted[:500]}...\n")
    
    return len(dataset.incidents)


def test_load_architecture():
    """Test loading and validating architecture data."""
    data_path = Path("data/architecture.json")
    
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    dataset = ArchitectureDataset.model_validate(raw_data)
    
    print(f"✓ Loaded {len(dataset.services)} services")
    print(f"✓ Loaded {len(dataset.teams)} teams")
    print(f"✓ Loaded {len(dataset.runbooks)} runbooks")
    
    # Test formatting
    formatter = DataFormatter()
    
    first_service = dataset.services[0].model_dump()
    formatted_service = formatter.format_service(first_service)
    print(f"✓ Formatted first service ({len(formatted_service)} chars)")
    
    first_team = dataset.teams[0].model_dump()
    formatted_team = formatter.format_team(first_team)
    print(f"✓ Formatted first team ({len(formatted_team)} chars)")
    
    return len(dataset.services) + len(dataset.teams) + len(dataset.runbooks)


def test_load_postmortems():
    """Test loading and validating postmortems data."""
    data_path = Path("data/postmortems.json")
    
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    dataset = PostmortemDataset.model_validate(raw_data)
    
    print(f"✓ Loaded {len(dataset.postmortems)} postmortems")
    
    # Test formatting
    formatter = DataFormatter()
    first_postmortem = dataset.postmortems[0].model_dump()
    formatted = formatter.format_postmortem(first_postmortem)
    
    print(f"✓ Formatted first postmortem ({len(formatted)} chars)")
    print(f"\nFirst 500 chars:\n{formatted[:500]}...\n")
    
    return len(dataset.postmortems)


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Forge Data Loading and Formatting")
    print("=" * 70)
    print()
    
    print("1. Testing Incidents Data")
    print("-" * 70)
    incidents_count = test_load_incidents()
    print()
    
    print("2. Testing Architecture Data")
    print("-" * 70)
    architecture_count = test_load_architecture()
    print()
    
    print("3. Testing Postmortems Data")
    print("-" * 70)
    postmortems_count = test_load_postmortems()
    print()
    
    print("=" * 70)
    print(f"✓ All tests passed!")
    print(f"  Total items: {incidents_count + architecture_count + postmortems_count}")
    print(f"    - Incidents: {incidents_count}")
    print(f"    - Architecture: {architecture_count}")
    print(f"    - Postmortems: {postmortems_count}")
    print("=" * 70)
