#!/usr/bin/env python3
"""Test all language plugins to verify they load correctly."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from falconeye.infrastructure.plugins.plugin_registry import PluginRegistry


def test_all_plugins():
    """Test that all language plugins load correctly."""
    print("=" * 80)
    print("Testing FalconEYE Language Plugin System")
    print("=" * 80)
    print()

    # Create registry and load all plugins
    registry = PluginRegistry()
    print("Loading all plugins...")
    registry.load_all_plugins()
    print(f"✓ Loaded {len(registry.get_all_plugins())} plugins\n")

    # Get all supported languages
    languages = registry.get_supported_languages()
    print(f"Supported languages: {', '.join(sorted(languages))}\n")

    # Get all supported extensions
    extensions = registry.get_supported_extensions()
    print(f"Supported extensions ({len(extensions)}): {', '.join(sorted(extensions))}\n")

    # Test each plugin
    print("=" * 80)
    print("Plugin Details")
    print("=" * 80)
    print()

    for plugin in registry.get_all_plugins():
        print(f"Language: {plugin.language_name}")
        print(f"Extensions: {', '.join(plugin.file_extensions)}")
        print(f"System Prompt: {len(plugin.get_system_prompt())} chars")
        print(f"Validation Prompt: {len(plugin.get_validation_prompt())} chars")
        print(f"Vulnerability Categories: {len(plugin.get_vulnerability_categories())}")
        print(f"Frameworks: {len(plugin.get_framework_context())}")

        chunking = plugin.get_chunking_strategy()
        print(f"Chunking: {chunking['chunk_size']} lines, {chunking['chunk_overlap']} overlap")
        print()

    # Test extension mapping
    print("=" * 80)
    print("Extension Mapping Tests")
    print("=" * 80)
    print()

    test_extensions = [
        ".py",
        ".js",
        ".ts",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".java",
        ".dart",
        ".php",
    ]

    for ext in test_extensions:
        plugin = registry.get_plugin_by_extension(ext)
        if plugin:
            print(f"✓ {ext:8} → {plugin.language_name}")
        else:
            print(f"✗ {ext:8} → NOT FOUND")

    print()

    # Verify all expected languages are present
    print("=" * 80)
    print("Expected Languages Verification")
    print("=" * 80)
    print()

    expected_languages = [
        "python",
        "javascript",
        "go",
        "rust",
        "c_cpp",
        "java",
        "dart",
        "php",
    ]

    all_present = True
    for lang in expected_languages:
        if registry.is_language_supported(lang):
            print(f"✓ {lang}")
        else:
            print(f"✗ {lang} NOT FOUND")
            all_present = False

    print()
    print("=" * 80)
    if all_present:
        print("✓ ALL TESTS PASSED")
        print("All 8 language plugins loaded successfully!")
    else:
        print("✗ SOME TESTS FAILED")
        print("Some language plugins are missing!")
        return False
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_all_plugins()
    sys.exit(0 if success else 1)