#!/usr/bin/env python3
"""Debug: Inspeccionar cómo se selecciona tipo de documento en SURA."""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

SURA_URL = (
    "https://login.sura.com/sso/servicelogin.aspx"
    "?continueTo=https%3A%2F%2Fepsapps.suramericana.com%2FSemp%2F"
    "&service=epssura"
)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(SURA_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    
    print("\n" + "="*80)
    print("DEBUG: Elementos para seleccionar tipo de documento")
    print("="*80 + "\n")
    
    # Buscar el select
    print("1️⃣ Buscando #ctl00_ContentMain_suraType (select)...")
    select = page.locator("#ctl00_ContentMain_suraType")
    if select.is_visible():
        print("   ✅ Encontrado")
        html = page.evaluate("el => el.outerHTML", select.element_handle())
        print(f"   HTML: {html}\n")
    else:
        print("   ❌ No visible\n")
    
    # Buscar radio buttons
    print("2️⃣ Buscando radio buttons o inputs con 'C' o 'cedula'...")
    elementos = page.locator("input[type='radio'], input[type='hidden']").all()
    for i, elem in enumerate(elementos):
        try:
            elem_id = elem.get_attribute("id")
            elem_name = elem.get_attribute("name")
            elem_value = elem.get_attribute("value")
            elem_label = elem.get_attribute("placeholder")
            print(f"   [{i}] id={elem_id} | name={elem_name} | value={elem_value} | placeholder={elem_label}")
        except:
            pass
    print()
    
    # Buscar labels
    print("3️⃣ Buscando labels con 'Cédula' o 'C'...")
    labels = page.locator("label").all()
    for i, label in enumerate(labels):
        try:
            texto = label.text_content().strip()
            if len(texto) < 50:
                print(f"   [{i}] {texto}")
        except:
            pass
    print()
    
    # Mostrar el HTML completo del formulario de login
    print("4️⃣ HTML del área del formulario:")
    form_html = page.locator("form, .login-form, [role='main']").first.inner_html()
    print(form_html[:1500])
    print("\n... (truncado)")
    
    print("\n" + "="*80)
    print("Presiona Enter para cerrar...")
    input()
    browser.close()
