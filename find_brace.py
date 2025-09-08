#!/usr/bin/env python3
"""
Trouveur d'accolade manquante - ChronoTech
"""

import re

def find_missing_brace():
    """Trouve l'accolade manquante dans le JavaScript"""
    
    print("🔍 RECHERCHE ACCOLADE MANQUANTE")
    print("=" * 50)
    
    with open('/home/amenard/Chronotech/ChronoTech/templates/dashboard/main.html', 'r') as f:
        lines = f.readlines()
    
    # Chercher les blocs script
    in_script = False
    script_content = []
    script_start = 0
    
    for i, line in enumerate(lines):
        if '<script>' in line or '<script ' in line:
            in_script = True
            script_start = i + 1
            script_content = []
            print(f"📜 Script bloc trouvé ligne {i+1}")
            
        elif '</script>' in line and in_script:
            print(f"   Se termine ligne {i+1} ({len(script_content)} lignes JS)")
            
            # Analyser ce bloc
            brace_count = 0
            paren_count = 0 
            bracket_count = 0
            
            for j, js_line in enumerate(script_content):
                for char in js_line:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    elif char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1
                    elif char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                
                # Si déséquilibre détecté, montrer la ligne
                if brace_count < 0:
                    print(f"   ❌ Ligne {script_start + j}: Accolade fermante en trop")
                    print(f"      {js_line.strip()}")
            
            print(f"   Balance finale: {{}} {brace_count}, () {paren_count}, [] {bracket_count}")
            
            if brace_count != 0 or paren_count != 0 or bracket_count != 0:
                print(f"   ⚠️  DÉSÉQUILIBRE DÉTECTÉ dans ce bloc!")
                
                # Montrer les dernières lignes du bloc
                print("   📝 Dernières lignes du bloc:")
                for j in range(max(0, len(script_content)-5), len(script_content)):
                    line_num = script_start + j
                    print(f"      {line_num:4d}: {script_content[j].rstrip()}")
            
            in_script = False
            
        elif in_script:
            script_content.append(line)
    
    print("\n🎯 RECHERCHE FONCTIONS NON FERMÉES...")
    
    # Chercher spécifiquement des fonctions non fermées
    function_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*{'
    
    with open('/home/amenard/Chronotech/ChronoTech/templates/dashboard/main.html', 'r') as f:
        content = f.read()
    
    functions = re.finditer(function_pattern, content)
    for match in functions:
        func_name = match.group(1)
        start_pos = match.start()
        
        # Compter les lignes jusqu'à cette position
        lines_before = content[:start_pos].count('\n')
        print(f"📋 Fonction '{func_name}' trouvée ligne {lines_before + 1}")

if __name__ == "__main__":
    find_missing_brace()
