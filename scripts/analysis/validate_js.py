#!/usr/bin/env python3
"""
Extracteur et validateur JavaScript - ChronoTech
Trouve les erreurs de syntaxe dans le dashboard
"""

import re

def extract_and_validate_js():
    """Extract JavaScript from HTML and validate syntax"""
    
    print("🔍 EXTRACTION ET VALIDATION JAVASCRIPT")
    print("=" * 50)
    
    try:
        with open('/home/amenard/Chronotech/ChronoTech/templates/dashboard/main.html', 'r') as f:
            content = f.read()
        
        # Extraire tout le JavaScript entre <script> et </script>
        js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        
        print(f"📊 {len(js_blocks)} blocs JavaScript trouvés")
        
        total_js_lines = 0
        for i, js_block in enumerate(js_blocks):
            lines = js_block.strip().split('\n')
            total_js_lines += len(lines)
            print(f"   Bloc {i+1}: {len(lines)} lignes")
        
        print(f"📝 Total: {total_js_lines} lignes JavaScript")
        
        # Rechercher des patterns d'erreurs communes
        error_patterns = [
            (r'}\s*$', 'Accolade fermante isolée'),
            (r'{\s*$', 'Accolade ouvrante isolée'),
            (r',\s*}', 'Virgule avant accolade fermante'),
            (r'}\s*,', 'Virgule après accolade fermante'),
            (r'function\s+\w+\s*\([^)]*\)\s*{[^}]*$', 'Fonction non fermée'),
            (r'if\s*\([^)]*\)\s*{[^}]*$', 'If statement non fermé'),
            (r'for\s*\([^)]*\)\s*{[^}]*$', 'For loop non fermé'),
        ]
        
        print("\n🔍 Recherche d'erreurs de syntaxe...")
        errors_found = []
        
        for i, js_block in enumerate(js_blocks):
            lines = js_block.split('\n')
            for line_num, line in enumerate(lines, 1):
                for pattern, description in error_patterns:
                    if re.search(pattern, line.strip()):
                        errors_found.append(f"Bloc {i+1}, ligne {line_num}: {description} - '{line.strip()}'")
        
        if errors_found:
            print(f"❌ {len(errors_found)} erreurs potentielles trouvées:")
            for error in errors_found[:10]:  # Limiter à 10 erreurs
                print(f"   {error}")
        else:
            print("✅ Aucune erreur de syntaxe évidente trouvée")
        
        # Vérifier les accolades non fermées
        print("\n🔍 Vérification équilibre des accolades...")
        brace_count = 0
        paren_count = 0
        bracket_count = 0
        
        all_js = '\n'.join(js_blocks)
        for char in all_js:
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
        
        print(f"   Accolades {{}}: {'+' if brace_count > 0 else ''}{brace_count}")
        print(f"   Parenthèses (): {'+' if paren_count > 0 else ''}{paren_count}")
        print(f"   Crochets []: {'+' if bracket_count > 0 else ''}{bracket_count}")
        
        if brace_count == 0 and paren_count == 0 and bracket_count == 0:
            print("✅ Équilibre des symboles correct")
        else:
            print("❌ Déséquilibre détecté!")
        
        # Chercher les lignes autour de 8266 (peut-être une ligne calculée dynamiquement)
        print("\n🔍 Recherche de problèmes dans les template strings...")
        template_issues = []
        for i, js_block in enumerate(js_blocks):
            lines = js_block.split('\n')
            for line_num, line in enumerate(lines, 1):
                # Chercher des template strings mal formés
                if '${' in line and '`' in line:
                    # Vérifier que les ${ sont bien fermés par }
                    dollar_braces = re.findall(r'\$\{[^}]*\}?', line)
                    for db in dollar_braces:
                        if not db.endswith('}'):
                            template_issues.append(f"Bloc {i+1}, ligne {line_num}: Template string mal fermé - '{line.strip()}'")
        
        if template_issues:
            print(f"❌ {len(template_issues)} problèmes de template strings:")
            for issue in template_issues:
                print(f"   {issue}")
        else:
            print("✅ Template strings semblent corrects")
        
        return len(errors_found) == 0 and brace_count == 0 and len(template_issues) == 0
        
    except Exception as e:
        print(f"❌ Erreur lecture fichier: {e}")
        return False

if __name__ == "__main__":
    is_valid = extract_and_validate_js()
    
    if is_valid:
        print("\n🎉 VALIDATION RÉUSSIE!")
        print("Le JavaScript semble syntaxiquement correct")
    else:
        print("\n⚠️ PROBLÈMES DÉTECTÉS!")
        print("Des erreurs de syntaxe ont été trouvées")
    
    print("\n🎯 PROCHAINES ÉTAPES:")
    print("1. Corriger les erreurs détectées")
    print("2. Tester dans le navigateur (F12 Console)")
    print("3. Recharger le dashboard")
