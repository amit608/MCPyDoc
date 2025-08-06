#!/usr/bin/env python3
"""
Demo showing the improved MCPyDoc functionality for AI agents.

This demo simulates how an AI agent would interact with MCPyDoc after the improvements
to address the issues found in the original demo flow.
"""

import asyncio
import json
import sys
import os

# Add the parent directory to the Python path to import mcpydoc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcpydoc.server import MCPyDoc

async def demo_improved_workflow():
    """Demonstrate the improved workflow for AI agents."""
    print("🚀 MCPyDoc Improved Demo - Enhanced AI Agent Experience")
    print("=" * 60)
    
    mcpydoc = MCPyDoc()
    
    # Scenario: AI agent needs to understand a package and find a specific method
    package_name = "json"
    target_method = "loads"
    
    print(f"\n📦 Scenario: Understanding package '{package_name}' and finding method '{target_method}'")
    print("-" * 60)
    
    # Step 1: Start with package structure analysis (recommended first step)
    print("\n1️⃣ STEP 1: Analyze package structure (recommended starting point)")
    try:
        structure = await mcpydoc.analyze_package_structure(package_name)
        print(f"✅ Package analyzed successfully!")
        print(f"   📊 Found: {len(structure.classes)} classes, {len(structure.functions)} functions")
        if structure.classes:
            print(f"   🎯 Main class: {structure.classes[0].symbol.name}")
        
        print("\n   🧭 Suggested next steps:")
        for step in structure.suggested_next_steps:
            print(f"      • {step}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 2: Search for the specific method with enhanced symbol search
    print(f"\n2️⃣ STEP 2: Search for method '{target_method}' with enhanced search")
    try:
        search_results = await mcpydoc.search_package_symbols(package_name, target_method)
        print(f"✅ Search completed!")
        print(f"   🔍 Found {len(search_results)} symbols matching '{target_method}'")
        
        if search_results:
            # Show enhanced results with parent class and confidence
            for result in search_results[:3]:  # Show top 3
                symbol = result.symbol
                print(f"   📋 Symbol: {symbol.name}")
                print(f"      Kind: {symbol.kind}")
                if result.parent_class:
                    print(f"      Parent class: {result.parent_class}")
                print(f"      Signature: {symbol.signature}")
                
                if result.documentation and result.documentation.description:
                    print(f"      Description: {result.documentation.description}")
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Step 3: Get detailed documentation with suggested next steps
    if search_results and search_results[0].parent_class:
        parent_class = search_results[0].parent_class
        module_path = f"{parent_class}.{target_method}"
        
        print(f"3️⃣ STEP 3: Get detailed documentation for '{module_path}'")
        try:
            doc_result = await mcpydoc.get_module_documentation(package_name, module_path)
            print(f"✅ Documentation retrieved!")
            
            if doc_result.symbol and doc_result.symbol.symbol.signature:
                print(f"   📝 Signature: {doc_result.symbol.symbol.signature}")
            
            if doc_result.documentation and doc_result.documentation.description:
                print(f"   📖 Description: {doc_result.documentation.description}")
            
            print("\n   🧭 Suggested next steps:")
            for step in doc_result.suggested_next_steps:
                print(f"      • {step}")
                
            if doc_result.alternative_paths:
                print("\n   🔄 Alternative paths to try:")
                for path in doc_result.alternative_paths:
                    print(f"      • {path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # Show enhanced error guidance
            print("   💡 Enhanced error guidance would suggest:")
            print(f"      • Try 'calculator.{target_method}' if in a submodule")
            print(f"      • Use analyze_structure to explore package layout")
            print(f"      • Search for the class name first, then its methods")
    
    # Step 4: Get source code to understand exact implementation
    if search_results and search_results[0].parent_class:
        parent_class = search_results[0].parent_class
        symbol_name = f"{parent_class}.{target_method}"
        
        print(f"\n4️⃣ STEP 4: Get source code for '{symbol_name}'")
        try:
            source_result = await mcpydoc.get_source_code(package_name, symbol_name)
            print(f"✅ Source code retrieved!")
            print(f"   📏 Source lines: {len(source_result.source.split(chr(10))) if source_result.source else 0}")
            
            # Show a snippet of the source code
            if source_result.source:
                lines = source_result.source.split('\n')
                print("   📄 Source code snippet:")
                for i, line in enumerate(lines[:10], 1):  # Show first 10 lines
                    print(f"      {i:2}: {line}")
                if len(lines) > 10:
                    print(f"      ... ({len(lines) - 10} more lines)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎉 Demo completed! The enhanced MCPyDoc provides:")
    print("   ✨ Better workflow guidance with suggested next steps")
    print("   🎯 Enhanced symbol search that finds methods within classes")
    print("   🔍 Parent class information for better context")
    print("   🧭 Alternative paths for common mistakes")
    print("   💡 Smarter error messages with actionable guidance")

async def demo_error_scenarios():
    """Demonstrate improved error handling and guidance."""
    print("\n🔧 Error Handling Improvements Demo")
    print("=" * 40)
    
    mcpydoc = MCPyDoc()
    
    # Test wrong module path
    print("\n📍 Testing wrong module path scenario:")
    try:
        result = await mcpydoc.get_module_documentation("magic_calculator", "WrongClass.method")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Enhanced guidance would suggest:")
        print("   • Use analyze_structure to see available classes")
        print("   • Try calculator.method or core.method patterns")
        print("   • Use search_symbols to find the correct class name")

if __name__ == "__main__":
    asyncio.run(demo_improved_workflow())
    asyncio.run(demo_error_scenarios())
