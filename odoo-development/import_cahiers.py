# -*- coding: utf-8 -*-
import os
import re
import json
import PyPDF2
import logging

_logger = logging.getLogger('odoo.import_cahiers')

def import_cahiers(env):
    print("--- IMPORT DES CAHIERS DE CHARGES ---")
    base_dir = "/mnt/extra-addons/cahiers_charges/Business analysis"
    if not os.path.exists(base_dir):
        print(f"❌ Le dossier {base_dir} n'existe pas.")
        return

    # 1. Parcourir les dossiers pour trouver les PDF
    pdf_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                filepath = os.path.join(root, file)
                # Dossier parent pour identifier le projet/application
                folder_name = os.path.basename(root)
                pdf_files.append((filepath, file, folder_name))

    print(f"Trouvé {len(pdf_files)} fichiers PDF à importer.")

    # 2. Importer chaque PDF
    imported_count = 0
    for filepath, filename, folder_name in pdf_files:
        title = f"CDC - {folder_name} - {filename[:-4]}"
        
        # Vérifier si l'article existe déjà
        article = env['agh.knowledge.article'].search([('name', '=', title)], limit=1)
        
        # Extraction du texte
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages[:10]: # Limiter à 10 pages
                    text += page.extract_text() or ""
                    if len(text) > 8000:
                        break
                text_content = text[:8000]
        except Exception as e:
            print(f"❌ Impossible de lire le PDF {filename}: {e}")
            continue

        if not text_content.strip():
            print(f"⚠️ Texte vide pour {filename}, ignoré.")
            continue

        # Formatage HTML simple
        html_content = f"<h2>Cahier des charges - {folder_name}</h2><h3>Fichier: {filename}</h3>"
        paragraphs = text_content.split('\n\n')
        for p in paragraphs:
            if p.strip():
                # Échapper les caractères HTML basiques
                clean_p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_content += f"<p>{clean_p}</p>"

        # Création ou mise à jour
        if not article:
            article = env['agh.knowledge.article'].create({
                'name': title,
                'content': html_content,
                'agile_doc_type': 'functional',
                'state': 'approved'
            })
            print(f"✅ Créé : {title}")
        else:
            article.write({
                'content': html_content,
                'state': 'approved'
            })
            print(f"🔄 Mis à jour : {title}")

        # Générer l'embedding
        try:
            success = article.action_update_embedding()
            if success:
                print(f"   -> Embedding généré pour {title}")
            else:
                print(f"   -> ⚠️ Échec de génération d'embedding pour {title}")
        except Exception as e:
            print(f"   -> ❌ Erreur embedding pour {title} : {e}")

        imported_count += 1

    print(f"--- Fin de l'import : {imported_count} articles importés/mis à jour ---")

# Appel de la fonction avec la variable globale env (fournie par odoo shell)
import_cahiers(env)
env.cr.commit()
